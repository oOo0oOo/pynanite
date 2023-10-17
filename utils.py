from itertools import combinations
from collections import defaultdict

import numpy as np
import networkx as nx
import metis
import matplotlib.pyplot as plt
from PIL import Image
from pyfqmr import Simplify
from OpenGL.GL import *
from scipy.spatial import KDTree


def load_obj(path):
    with open(path, "r") as f:
        lines = f.readlines()

    vertices = []
    tris = []
    for line in lines:
        if line.startswith("v "):
            vertices.append([float(v) for v in line.split()[1:]])
        elif line.startswith("f "):
            tris.append(
                [int(v.split("/")[0]) - 1 for v in line.split()[1:]]
            )  # NOTE: -1 because obj indices start at 1

    # Now scale the 3D points to be between 0 and 1
    vertices = np.array(vertices)

    min_axis = np.min(vertices)
    vertices -= min_axis

    max_axis = np.max(vertices)
    vertices /= max_axis

    tris = np.array(tris)
    tris = np.sort(tris, axis=1)

    print("Loaded %d vertices and %d faces" % (len(vertices), len(tris)))
    return vertices, tris


def load_texture(path):
    # Load texture
    img = Image.open(path)
    img_data = np.array(list(img.getdata()), np.uint8)

    # Generate a texture id
    texture_id = glGenTextures(1)

    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

    # Upload the image data to GPU as a texture
    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGB,
        img.width,
        img.height,
        0,
        GL_RGB,
        GL_UNSIGNED_BYTE,
        img_data,
    )
    return texture_id


def create_dual_graph(tris):
    # Create an unweighted dual graph of the mesh tris
    # NOTE: Expects tris to be sorted
    edge_to_tri = defaultdict(list)
    for i, tri in enumerate(tris):
        for edge in combinations(tri, 2):
            edge_to_tri[edge].append(i)

    adjacency = defaultdict(list)

    for triss in edge_to_tri.values():
        for tri1, tri2 in combinations(triss, 2):  # iterate over unique pairs
            adjacency[tri1].append(tri2)
            adjacency[tri2].append(tri1)

    adjacency = [sorted(adjacency[i]) for i in range(len(tris))]

    return adjacency


def create_dual_graph_clusters(member_adjacencies, clusters_membership):
    # Returns a weighted adjacency list of the dual graph of the clusters
    dual_graph_clusters = defaultdict(lambda: defaultdict(int))

    num_clusters = max(clusters_membership) + 1

    # Iterate over member_adjacencies to create dual graph clusters
    for i, adjacent_indices in enumerate(member_adjacencies):
        curr_cluster = clusters_membership[i]
        for j in adjacent_indices:
            adj_cluster = clusters_membership[j]
            # Only add an edge if it is a border edge (clusters are different)
            if curr_cluster != adj_cluster:
                dual_graph_clusters[curr_cluster][adj_cluster] += 1

    dual_graph_clusters = [
        tuple([(key, value) for key, value in sorted(dual_graph_clusters[i].items())])
        for i in range(num_clusters)
    ]
    return dual_graph_clusters


def partition_graph(n_clusters, adjacencies):
    # Can use weighted or unweighted adjacency list (see metis docs)
    # NOTE: metis.part_graph can possibly hang (never complete)
    adj = metis.adjlist_to_metis(adjacencies)
    n_cuts, membership = metis.part_graph(adj, n_clusters)
    return np.array(membership)


def group_tris(tris, cluster_size):
    # Group tris based on graph partitioning (keep as many shared boundary edges as possible)
    dual_adj = create_dual_graph(tris)
    n_clusters = tris.shape[0] // cluster_size
    clusters = partition_graph(n_clusters, dual_adj)
    return dual_adj, clusters


def group_clusters(clusters, member_adjacencies, num_clusters):
    # Group clusters based on graph partitioning (keep as many shared boundary edges as possible)
    weighted_adjacencies = create_dual_graph_clusters(member_adjacencies, clusters)
    group_membership = partition_graph(num_clusters, weighted_adjacencies)
    return group_membership


def simplify_mesh_inside(vertices, faces, removal_ratio=0.5):
    target_faces = int(faces.shape[0] * (1 - removal_ratio))
    mesh_simplifier = Simplify()
    mesh_simplifier.setMesh(vertices, faces)
    mesh_simplifier.simplify_mesh(target_faces, preserve_border=True, verbose=0)
    simplified_vertices, simplified_faces, __ = mesh_simplifier.getMesh()
    simplified_faces = np.sort(simplified_faces, axis=1)
    return simplified_vertices, simplified_faces


def calc_geometric_error(verts1, verts2):
    tree = KDTree(verts2)
    error = 0
    for v in verts1:
        dist, _ = tree.query(v)
        error += dist**2
    return np.sqrt(error / len(verts1))


def calc_bounding_sphere(vertices):
    center = np.mean(vertices, axis=0)
    radius = np.max(np.linalg.norm(vertices - center, axis=1))
    return center, radius


def minimum_bounding_sphere(spheres):
    S = np.array([np.array(center) for center, _ in spheres])
    radii = np.array([radius for _, radius in spheres])
    return welzl(S, radii)


def welzl(S, radii, B=None):
    # Implementation of Welzl's algorithm for minimum bounding sphere
    if B is None:
        B = (np.array([0, 0, 0]), 0)

    if len(S) == 0:
        return B

    idx = S.shape[0] - 1
    p = S[idx, :]
    rad = radii[idx]
    S = np.delete(S, idx, 0)
    radii = np.delete(radii, idx, 0)
    Bp = welzl(S, radii, B)

    if np.linalg.norm(p - Bp[0]) <= max(Bp[1], rad):
        return Bp

    # Otherwise, compute the bounding sphere for Bp union p
    d = np.linalg.norm(p - Bp[0])
    center = (Bp[0] + p) / 2 + (rad - Bp[1]) * (p - Bp[0]) / (2 * d)
    radius = (d + Bp[1] + rad) / 2
    Bpp = (center, radius)
    return Bpp


def visualize_adjacencies(adjacencies):
    G = nx.Graph()
    for i, adj in enumerate(adjacencies):
        for j in adj:
            if type(j) == tuple:
                j = j[0]
            G.add_edge(i, j)

    print(f"Drawing graph with {len(G.nodes)} nodes and {len(G.edges)} edges.")
    nx.draw(G)
    plt.show()
    plt.pause(0.01)


def visualize_adjacency_dict(adjacencies, label=True):
    G = nx.Graph()
    for i, adj in adjacencies.items():
        for j in adj:
            G.add_edge(i, j)

    print(f"Drawing graph with {len(G.nodes)} nodes and {len(G.edges)} edges.")
    nx.draw(G, with_labels=label)
    plt.show()
    plt.pause(0.01)
