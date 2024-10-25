from collections import defaultdict
from functools import partial
import multiprocessing as mp
import pickle

from scipy.spatial import KDTree
import numpy as np

from .utils import (
    calc_bounding_sphere,
    calc_RMS_error,
    create_dual_graph,
    group_tris,
    group_clusters,
    load_obj,
    load_texture,
    minimum_bounding_sphere,
    simplify_mesh_inside,
)


class LODGraph:
    def __init__(self, paths, force_build=False, cluster_size_initial=160, cluster_size=128, group_size=8):
        obj_path, texture_path, build_path = paths

        self.config = {
            "cluster_size_initial": cluster_size_initial,
            "cluster_size": cluster_size,
            "group_size": group_size
        }

        if not force_build:
            if self.load_from_pickle(build_path):
                return
            
        print(f"Baking new LOD graph ({obj_path}). This will take a while...")

        # Create LOD 0
        vertices, tris, texture_coords, orig_normals = load_obj(obj_path)
        adjacencies, clusters = group_tris(tris, self.config["cluster_size_initial"])
        assert len(clusters) == len(tris)

        graph_adjacencies = [np.array(range(max(clusters) + 1))]
        geometric_errors = [0]
        self.lods = [
            [
                vertices,
                tris,
                adjacencies,
                clusters,
                graph_adjacencies,
                geometric_errors,
                orig_normals.copy(),
            ]
        ]

        clusters_remaining = max(clusters) + 1
        print(
            f"LOD 0 has {len(self.lods[-1][1])} tris and {clusters_remaining} clusters."
        )

        # Simplify the graph until we have a single cluster remaining
        while clusters_remaining > 1:
            self.lods.append(next_lod(self.lods[-1], self.config))
            clusters_remaining = max(self.lods[-1][3]) + 1
            print(
                f"LOD {len(self.lods) - 1} has {len(self.lods[-1][1])} tris and {clusters_remaining} clusters."
            )

        # Create the cluster DAG
        cluster_dag = []
        cluster_errors = []
        cluster_verts = [[]]
        cluster_normals = [[]]
        cluster_tris = [[]]
        num_clusters = 1  # ! Attention, this is dependent on having a single sink node
        for lod in self.lods:
            vertices, tris, __, clusters, graph_adjacencies, geometric, normals = lod

            for adjs in graph_adjacencies:
                cluster_dag.append(adjs + num_clusters)

            cluster_errors += geometric
            cluster_tris.append(tris)

            # Collect all vertices for tris
            cluster_map = defaultdict(list)
            for i, cluster in enumerate(clusters):
                cluster_map[cluster].append(tris[i])

            for i in range(max(clusters) + 1):
                verts = vertices[cluster_map[i]].reshape(-1, 3)
                cluster_verts.append(verts)
                norms = normals[cluster_map[i]].reshape(-1, 3)
                cluster_normals.append(norms)

            num_current_clusters = max(clusters) + 1
            num_clusters += num_current_clusters

        cluster_dag.append([])  # Root node (least detailed)
        cluster_errors.append(1.5 * cluster_errors[-1])

        cluster_dag = [[int(i) for i in j] for j in cluster_dag]

        # Create the reverse DAG (lookup from child to parent)
        cluster_dag_rev = defaultdict(list)
        for i, adjs in enumerate(cluster_dag):
            for adj in adjs:
                cluster_dag_rev[adj].append(i)
        
        cluster_dag_rev = [cluster_dag_rev[i] for i in range(num_clusters)]

        # Enforce monotonic cluster error and monotonic increasing bounding spheres (parent fully contains children)
        cluster_bounding_spheres = [((0, 0, 0), 0)]
        monotonic_error = [0]
        for i in range(1, num_clusters):
            sphere = calc_bounding_sphere(cluster_verts[i])
            error = cluster_errors[i]
            children = cluster_dag_rev[i]
            if children:
                if min(children) != 0:
                    all_spheres = [sphere] + [cluster_bounding_spheres[j] for j in children]
                    sphere = minimum_bounding_sphere(all_spheres)

                    kid_error = max([monotonic_error[j] for j in children])
                    if error <= kid_error:
                        error = kid_error * 1.001 # Cheat using an epsilon

            cluster_bounding_spheres.append(sphere)
            monotonic_error.append(error)
        
        # Check whether error is strictly monotonous and bounding spheres are strictly increasing in radius
        # for i in range(1, num_clusters):
        #     for j in cluster_dag_rev[i]:
        #         assert monotonic_error[i] > monotonic_error[j]
        #         assert cluster_bounding_spheres[i][1] >= cluster_bounding_spheres[j][1]

        self.texture_id = load_texture(texture_path)
        cluster_textures = [[]]
        tree = KDTree(self.lods[0][0])

        # Texturing: Interpolate btw n closest vertices
        num_neighbors = 2
        for i in range(1, num_clusters):
            verts = cluster_verts[i]
            dists, indices = tree.query(verts, num_neighbors)
            tex_coords = texture_coords[indices]

            weights = 1 / (dists + 1e-8)  # Add a small epsilon to avoid division by zero
            weights /= np.sum(weights, axis=1, keepdims=True)
            cluster_textures.append(np.einsum('ij,ijk->ik', weights, tex_coords)) # Magic einsum

        self.cluster_dag = cluster_dag
        self.cluster_dag_rev = cluster_dag_rev
        self.cluster_verts = cluster_verts
        self.cluster_errors = np.array(monotonic_error)
        self.cluster_bounding_centers = np.array(
            [i[0] for i in cluster_bounding_spheres]
        )
        self.cluster_bounding_radii = np.array([i[1] for i in cluster_bounding_spheres])
        self.cluster_normals = cluster_normals
        self.cluster_textures = cluster_textures

        assert (
            len(self.cluster_dag)
            == len(self.cluster_dag_rev)
            == num_clusters
            == len(self.cluster_verts)
            == len(self.cluster_errors)
            == len(self.cluster_bounding_centers)
            == len(self.cluster_bounding_radii)
            == len(self.cluster_normals)
            == len(self.cluster_textures)
        )
        self._post_process()
        self.save_to_pickle(paths)
        print(f"Baked cluster mesh with {len(cluster_dag)} clusters.")

    def _post_process(self):
        # A bit hacky...
        self.cluster_verts = [np.array(i, dtype=np.float32) for i in self.cluster_verts]
        self.cluster_normals = [np.array(i, dtype=np.float32).ravel() for i in self.cluster_normals]
        self.cluster_textures = [np.array(i, dtype=np.float32).ravel() for i in self.cluster_textures]

    def save_to_pickle(self, paths):
        data = [
            self.cluster_dag,
            self.cluster_dag_rev,
            self.cluster_verts,
            self.cluster_errors,
            self.cluster_bounding_centers,
            self.cluster_bounding_radii,
            self.cluster_normals,
            self.cluster_textures,
            paths,
        ]
        with open(paths[2], "wb") as f:
            pickle.dump(data, f)

    def load_from_pickle(self, path):
        try:
            with open(path, "rb") as f:
                print("Loading baked model from file.")
                data = pickle.load(f)
        except FileNotFoundError:
            return False

        (
            self.cluster_dag,
            self.cluster_dag_rev,
            self.cluster_verts,
            self.cluster_errors,
            self.cluster_bounding_centers,
            self.cluster_bounding_radii,
            self.cluster_normals,
            self.cluster_textures,
            paths,
        ) = data

        self.texture_id = load_texture(paths[1])

        self._post_process()

        print(f"Loaded cluster mesh with {len(self.cluster_dag)} clusters.")

        return True


def next_lod(lod, config, parallel=False):
    vertices, tris, adjacencies, clusters, __, __, __ = lod

    assert len(tris) == len(clusters)

    # Create a lookup table of cluster to tris_ids
    cluster_to_tris = defaultdict(list)
    for i, cluster in enumerate(clusters):
        cluster_to_tris[cluster].append(i)

    # Create cluster super-groups
    num_orig_clusters = len(cluster_to_tris)
    if num_orig_clusters > config["group_size"] * 2:
        grouped = group_clusters(clusters, adjacencies, num_orig_clusters // config["group_size"])
    elif num_orig_clusters > 4:
        grouped = group_clusters(clusters, adjacencies, 2)
    else:
        grouped = [0 for i in range(num_orig_clusters)]

    clusters_dict = defaultdict(list)
    for i, group in enumerate(grouped):
        clusters_dict[group].append(i)

    clusters_in_group = []
    for i in range(max(grouped) + 1):
        clusters_in_group.append(clusters_dict[i])

    if parallel:
        simplified_lod = simplify_groups_parallel(
            lod, cluster_to_tris, clusters_in_group, config
        )
    else:
        simplified_lod = simplify_groups(lod, cluster_to_tris, clusters_in_group, config)

    return simplified_lod


def simplify_group(lod, cluster_to_tris, config, group):
    vertices, tris, __, __, __, __, __ = lod

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

    simplified_vertices, simplified_faces, simplified_normals = simplify_mesh_inside(
        new_vertices, new_tris
    )

    if len(simplified_faces) > config["cluster_size"] * 2:
        new_adjacencies, new_clusters = group_tris(
            simplified_faces, cluster_size=config["cluster_size"]
        )
    else:
        new_adjacencies = None
        new_clusters = np.zeros(len(simplified_faces), dtype=int)

    geometric_error = calc_RMS_error(simplified_vertices, new_vertices)

    return (
        simplified_vertices,
        simplified_faces,
        new_adjacencies,
        new_clusters,
        # No graph adjacencies
        geometric_error,
        simplified_normals,
    )


def simplify_groups_parallel(lod, cluster_to_tris, clusters_in_group, config):
    with mp.Pool(int(mp.cpu_count())) as pool:
        partial_func = partial(simplify_group, lod, cluster_to_tris, config)
        results = pool.map(partial_func, clusters_in_group, chunksize=1)

    return combine_group_lods(results, clusters_in_group)


def simplify_groups(lod, cluster_to_tris, clusters_in_group, config):
    simplified_lods = []
    for group in clusters_in_group:
        simplified_lods.append(simplify_group(lod, cluster_to_tris, config, group))

    return combine_group_lods(simplified_lods, clusters_in_group)


def combine_group_lods(group_lods, clusters_in_group):
    # Combine lods into a single mesh, returns a new lod
    # Indices for vertices and clusters are updated for the new lod
    new_vertices = []
    new_tris = []
    new_clusters = []
    new_normals = []

    num_clusters = 0
    start_clusters = sum([len(i) for i in clusters_in_group])
    vertex_mapping = {}

    graph_adjacencies = {}
    geometric_errors = {}

    for i, lod in enumerate(group_lods):
        vertices, tris, adjacencies, clusters, geometric_error, normals = lod

        vertices = [tuple(vertex) for vertex in vertices]

        for vert_i, vertex in enumerate(vertices):
            if vertex not in vertex_mapping:
                vertex_mapping[vertex] = len(new_vertices)
                new_vertices.append(vertex)
                new_normals.append(normals[vert_i])

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
    new_normals = np.array(new_normals)
    new_tris = np.array(new_tris)
    new_adjacencies = create_dual_graph(new_tris)

    return (
        new_vertices,
        new_tris,
        new_adjacencies,
        new_clusters,
        graph_adjacencies,
        geometric_errors,
        new_normals,
    )
