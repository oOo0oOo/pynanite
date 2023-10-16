from collections import defaultdict
from functools import partial
from pprint import pprint
import subprocess
import sys
import time
import multiprocessing as mp

import numpy as np

from utils import (
    calc_bounding_sphere,
    calc_geometric_error,
    create_dual_graph,
    group_tris,
    group_clusters,
    load_obj,
    minimum_bounding_sphere,
    simplify_mesh_inside,
    visualize_adjacencies,
    visualize_adjacency_dict,
)


CLUSTER_SIZE_INITIAL = 160
CLUSTER_SIZE = 128
GROUP_SIZE = 8


class LODGraph:
    def __init__(self, path):
        # Create LOD 0
        vertices, tris = load_obj(path)
        adjacencies, clusters = group_tris(tris, CLUSTER_SIZE_INITIAL)
        graph_adjacencies = [np.array(range(max(clusters) + 1))]
        geometric_errors = [0]
        self.lods = [
            [vertices, tris, adjacencies, clusters, graph_adjacencies, geometric_errors]
        ]

        clusters_remaining = max(clusters) + 1
        print(
            f"LOD 0 has {len(self.lods[-1][1])} tris and {clusters_remaining} clusters."
        )

        # Simplify the graph until we cannot create more than 2 groups of 8 clusters
        while clusters_remaining > 16:
            self.lods.append(next_lod(self.lods[-1], parallel=False))
            clusters_remaining = max(self.lods[-1][3]) + 1
            print(
                f"LOD {len(self.lods) - 1} has {len(self.lods[-1][1])} tris and {clusters_remaining} clusters."
            )

        # One last mesh simplification for the last node
        last_vertices, last_tris, __, last_clusters, __, __ = self.lods[-1]
        simplified_vertices, simplified_faces = simplify_mesh_inside(
            last_vertices, last_tris
        )
        geometric_error = calc_geometric_error(simplified_vertices, last_vertices)

        self.lods.append(
            [
                simplified_vertices,
                simplified_faces,
                None,
                np.zeros(len(simplified_faces), dtype=int),
                [
                    np.array([0]) for i in range(max(last_clusters) + 1)
                ],  # All last clusters are connected to the last node
                [geometric_error for i in range(max(last_clusters) + 1)],
            ]
        )

        # Create the cluster DAG
        cluster_dag = []
        cluster_verts = [[]]
        cluster_errors = [0]
        # cluster_bounding_spheres = [((0, 0), 0)]

        num_clusters = 1  # ! Attention, this is dependent on having a single sink node
        for lod in self.lods:
            vertices, tris, __, clusters, graph_adjacencies, geometric = lod

            for adjs in graph_adjacencies:
                cluster_dag.append(adjs + num_clusters)

            cluster_errors += geometric

            # Collect all vertices for tris
            cluster_map = defaultdict(list)
            for i, cluster in enumerate(clusters):
                cluster_map[cluster].append(tris[i])

            for i in range(max(clusters) + 1):
                verts = vertices[cluster_map[i]].reshape(-1, 3)
                cluster_verts.append(verts)
                # cluster_bounding_spheres.append(calc_bounding_sphere(verts))

            num_current_clusters = max(clusters) + 1
            num_clusters += num_current_clusters

        cluster_dag.append([])

        # Create the reverse DAG
        cluster_dag_rev = defaultdict(list)
        for i, adjs in enumerate(cluster_dag):
            for adj in adjs:
                cluster_dag_rev[adj].append(i)

        self.cluster_dag_rev = [cluster_dag_rev[i] for i in range(num_clusters)]

        # Make sure parent bounding spheres contain children (monotonic)
        cluster_bounding_spheres = [((0, 0), 0)]
        for i in range(1, num_clusters):
            sphere = calc_bounding_sphere(cluster_verts[i])
            children = cluster_dag_rev[i]
            if children[0] != 0:
                all_spheres = [sphere]
                all_spheres += [cluster_bounding_spheres[j] for j in children]
                new_sphere = minimum_bounding_sphere(all_spheres)
                sphere = new_sphere
            cluster_bounding_spheres.append(sphere)

        # Enforce monotonic cluster error
        monotonic_error = [0]
        for i in range(1, num_clusters):
            error = cluster_errors[i]
            children = cluster_dag_rev[i]
            if children[0] != 0:
                kid_errors = [monotonic_error[j] for j in children]
                error = max(error, max(kid_errors))
            monotonic_error.append(error)
        cluster_errors = monotonic_error

        # print(f"Cluster DAG has {len(cluster_dag)} clusters. {len(cluster_verts)} verts. {len(cluster_errors)} errors. {len(cluster_bounding_spheres)} spheres. {len(self.cluster_dag_rev)} rev nodes.")

        assert (
            len(cluster_dag)
            == num_clusters
            == len(cluster_verts)
            == len(cluster_errors)
            == len(cluster_bounding_spheres)
            == len(self.cluster_dag_rev)
        )

        self.cluster_dag = cluster_dag
        self.cluster_verts = cluster_verts
        self.cluster_errors = cluster_errors
        self.cluster_bounding_spheres = cluster_bounding_spheres

        print(f"Cluster DAG has {len(cluster_dag)} clusters.")


def next_lod(lod, parallel=True):
    vertices, tris, adjacencies, clusters, __, __ = lod

    assert len(tris) == len(clusters)

    # Create a lookup table of cluster to tris_ids
    cluster_to_tris = defaultdict(list)
    for i, cluster in enumerate(clusters):
        cluster_to_tris[cluster].append(i)

    # Create cluster super-groups
    grouped = group_clusters(clusters, adjacencies, GROUP_SIZE)

    clusters_dict = defaultdict(list)
    for i, group in enumerate(grouped):
        clusters_dict[group].append(i)

    clusters_in_group = []
    for i in range(max(grouped) + 1):
        clusters_in_group.append(clusters_dict[i])

    if parallel:
        simplified_lod = simplify_groups_parallel(
            lod, cluster_to_tris, clusters_in_group
        )
    else:
        simplified_lod = simplify_groups(lod, cluster_to_tris, clusters_in_group)

    return simplified_lod


def simplify_group(lod, cluster_to_tris, group):
    vertices, tris, __, __, __, __ = lod

    new_vertices = []
    new_tris = []
    vertex_mapping = {}

    for cluster_i in group:
        for tri_i in cluster_to_tris[cluster_i]:
            verts = []
            for vertex_i in tris[tri_i]:
                if vertex_i not in vertex_mapping:
                    vertex_mapping[vertex_i] = len(new_vertices)
                    new_vertices.append(vertices[vertex_i])
                verts.append(vertex_mapping[vertex_i])
            new_tris.append(verts)

    new_vertices = np.array(new_vertices)
    new_tris = np.array(new_tris)
    new_tris = np.sort(new_tris, axis=1)

    simplified_vertices, simplified_faces = simplify_mesh_inside(new_vertices, new_tris)
    new_adjacencies, new_clusters = group_tris(
        simplified_faces, cluster_size=CLUSTER_SIZE
    )
    geometric_error = calc_geometric_error(simplified_vertices, new_vertices)

    return (
        simplified_vertices,
        simplified_faces,
        new_adjacencies,
        new_clusters,
        geometric_error,
    )


def simplify_groups_parallel(lod, cluster_to_tris, clusters_in_group):
    with mp.Pool(int(mp.cpu_count())) as pool:
        partial_func = partial(simplify_group, lod, cluster_to_tris)
        results = pool.map(partial_func, clusters_in_group, chunksize=16)

    return combine_group_lods(results, clusters_in_group)


def simplify_groups(lod, cluster_to_tris, clusters_in_group):
    simplified_lods = []
    for group in clusters_in_group:
        simplified_lods.append(simplify_group(lod, cluster_to_tris, group))

    return combine_group_lods(simplified_lods, clusters_in_group)


def combine_group_lods(group_lods, clusters_in_group):
    # Combine lods into a single mesh, returns a new lod
    # Indices for vertices and clusters are updated for the new lod
    new_vertices = []
    new_tris = []
    new_clusters = []

    num_clusters = 0
    start_clusters = sum([len(i) for i in clusters_in_group])
    vertex_mapping = {}

    graph_adjacencies = {}
    geometric_errors = {}

    for i, lod in enumerate(group_lods):
        vertices, tris, adjacencies, clusters, geometric_error = lod

        vertices = [tuple(vertex) for vertex in vertices]

        for vertex in vertices:
            if vertex not in vertex_mapping:
                vertex_mapping[vertex] = len(new_vertices)
                new_vertices.append(vertex)

        for tri in tris:
            new_tris.append([vertex_mapping[vertices[vertex]] for vertex in tri])

        n_clust = max(clusters) + 1

        adj_clusters = np.array(range(num_clusters, num_clusters + n_clust))
        for cluster_i in clusters_in_group[i]:
            graph_adjacencies[cluster_i] = adj_clusters.copy()
            geometric_errors[cluster_i] = geometric_error

        new_clusters.append(clusters + num_clusters)
        num_clusters += n_clust

    assert len(graph_adjacencies) == start_clusters
    graph_adjacencies = [graph_adjacencies[i] for i in range(start_clusters)]
    geometric_errors = [geometric_errors[i] for i in range(len(geometric_errors))]

    new_clusters = np.concatenate(new_clusters)
    new_vertices = np.array(new_vertices)
    new_tris = np.array(new_tris)

    new_tris = np.sort(new_tris, axis=1)

    new_adjacencies = create_dual_graph(new_tris)

    return (
        new_vertices,
        new_tris,
        new_adjacencies,
        new_clusters,
        graph_adjacencies,
        geometric_errors,
    )
