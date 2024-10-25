from itertools import combinations
from collections import defaultdict

import numpy as np
import pymetis
from PIL import Image
from pyfqmr import Simplify
from scipy.spatial import KDTree

from OpenGL.GL import (
    glGenTextures, glBindTexture, glTexParameterf, glTexImage2D, 
    GL_TEXTURE_2D, GL_LINEAR, GL_RGB, GL_UNSIGNED_BYTE,
    GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER
)


def load_obj(path):
    vertices = []
    tris = []
    texture_coords = []
    normals = []
    vertex_vt_map = {}
    vertex_vn_map = {}

    with open(path, "r") as f:
        lines = f.readlines()

    for line in lines:
        if line.startswith("v "):
            vertices.append([float(v) for v in line.split()[1:]])
        elif line.startswith("vt "):
            texture_coords.append([float(v) for v in line.split()[1:]])
        elif line.startswith("vn "):
            normals.append([float(v) for v in line.split()[1:]])
        elif line.startswith("f "):
            elements = line.split()[1:]
            tri = []
            for element in elements:
                els = element.split("/")

                v = int(els[0]) - 1  # NOTE: -1 because obj indices start at 1
                t = int(els[1]) - 1 if len(els) > 1 and els[1] else 0
                n = int(els[2]) - 1 if len(els) > 2 and els[2] else 0

                vertex_vt_map[v] = t
                vertex_vn_map[v] = n

                tri.append(v)

            # Convert quads to tris
            if len(tri) == 4:
                tris.append([tri[0], tri[1], tri[2]])
                tris.append([tri[0], tri[2], tri[3]])
            else:
                tris.append(tri)

    try:
        texture_coords = [
            texture_coords[vertex_vt_map[i]] for i in range(len(vertices))
        ]
    except IndexError:
        print("Invalid textures")
        texture_coords = [[0, 0] for _ in range(len(vertices))]
    texture_coords = np.array(texture_coords, dtype=np.float32)

    try:
        normals = [normals[vertex_vn_map[i]] for i in range(len(vertices))]
    except IndexError:
        print("Invalid normals")
        normals = [[0, 1, 0] for _ in range(len(vertices))]

    normals = np.array(normals, dtype=np.float32)

    # Scaling the vertices 0 - 1
    vertices = np.array(vertices)

    min_axis = np.min(vertices)
    vertices -= min_axis

    max_axis = np.max(vertices)
    vertices /= max_axis

    tris = np.array(tris)

    print("Loaded %d vertices and %d tris" % (len(vertices), len(tris)))
    return vertices.astype(np.float32), tris, texture_coords, normals


def load_texture(path):
    # Load texture
    img = Image.open(path)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img_data = np.array(img, dtype=np.uint8)

    # Generate a texture id
    texture_id = glGenTextures(1)

    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
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

    # print(f"Loaded texture {path} ({img.width} x {img.height}) with id {texture_id}")
    return texture_id


def create_dual_graph(tris):
    # Create an unweighted dual graph of the mesh tris
    edge_to_tri = defaultdict(list)
    for i, tri in enumerate(tris):
        tri = sorted(tri)
        for edge in combinations(tri, 2):
            edge_to_tri[edge].append(i)

    adjacency = defaultdict(list)
    for triss in edge_to_tri.values():
        for tri1, tri2 in combinations(triss, 2):
            adjacency[tri1].append(tri2)
            adjacency[tri2].append(tri1)

    return [adjacency[i] for i in range(len(tris))]


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
                dual_graph_clusters[adj_cluster][curr_cluster] += 1

    dual_graph_clusters = [
        tuple([(key, value) for key, value in dual_graph_clusters[i].items()])
        for i in range(num_clusters)
    ]

    return dual_graph_clusters


def partition_graph(n_clusters, adjacencies):
    n_cuts, membership = pymetis.part_graph(n_clusters, adjacencies)
    return np.array(membership)

def partition_graph_weighted(n_clusters, adjacencies):
    # Convert the adjacency list to xadj, adjncy, and eweights
    xadj = [0]
    adjncy = []
    eweights = []
    for neighbors in adjacencies:
        for neighbor, weight in neighbors:
            adjncy.append(neighbor)
            eweights.append(weight)
        xadj.append(len(adjncy))

    n_cuts, membership = pymetis.part_graph(
        nparts=n_clusters,
        xadj=xadj,
        adjncy=adjncy,
        eweights=eweights
    )
    return np.array(membership)


def group_clusters(clusters, member_adjacencies, num_clusters):
    # Group clusters based on graph partitioning (keep as many shared boundary edges as possible)
    weighted_adjacencies = create_dual_graph_clusters(member_adjacencies, clusters)
    group_membership = partition_graph_weighted(num_clusters, weighted_adjacencies)
    return group_membership


def partition_graph_metis(n_clusters, adjacencies):
    # DEPRECATED: Use pymetis instead, its maintained and provides better results
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


def simplify_mesh_inside(vertices, faces, removal_ratio=0.5):
    target_faces = int(faces.shape[0] * (1 - removal_ratio))
    mesh_simplifier = Simplify()
    mesh_simplifier.setMesh(vertices, faces)
    mesh_simplifier.simplify_mesh(target_faces, preserve_border=True, verbose=0)
    (
        simplified_vertices,
        simplified_faces,
        simplified_normals,
    ) = mesh_simplifier.getMesh()

    # HANDLE NORMALS
    # Since OpenGL handles normals per vertex, and this simplification method returns normals per face,
    # we use the average of the normals of the faces that share a vertex as the vertex normal
    simplified_vertices_len = len(simplified_vertices)
    avg_normal = np.zeros((simplified_vertices_len, 3))
    avg_count = np.zeros(simplified_vertices_len)

    # Flatten the faces array and repeat the normals for each vertex in the face
    flattened_faces = simplified_faces.flatten()
    repeated_normals = np.repeat(simplified_normals, 3, axis=0)

    # Accumulate normals and counts using advanced indexing
    np.add.at(avg_normal, flattened_faces, repeated_normals)
    np.add.at(avg_count, flattened_faces, 1)

    # Avoid division by zero
    avg_count[avg_count == 0] = 1

    # Calculate the average normals
    simplified_normals = avg_normal / avg_count[:, np.newaxis]

    # Calculate the average normals and normalize them
    simplified_normals = avg_normal / avg_count[:, np.newaxis]
    norms = np.linalg.norm(simplified_normals, axis=1)

    # Prevent division by zero
    norms[norms == 0] = 1
    simplified_normals /= norms[:, np.newaxis]

    assert len(simplified_vertices) == len(simplified_normals)

    return simplified_vertices, simplified_faces, simplified_normals


def calc_RMS_error(verts1, verts2):
    tree = KDTree(verts2)
    dists, _ = tree.query(verts1)
    error = np.sum(np.square(dists))
    return np.sqrt(error / len(verts1))


def calc_bounding_sphere(vertices):
    center = np.mean(vertices, axis=0)
    radius = np.max(np.linalg.norm(vertices - center, axis=1))
    return center, radius


def minimum_bounding_sphere(spheres):
    if len(spheres) > 1:
        # Sort by radius to improve performance
        spheres = sorted(spheres, key=lambda x: x[1], reverse=True)

    # Initialize the bounding sphere to the first sphere
    center, radius = spheres[0]

    for (c, r) in spheres[1:]:
        dist = np.linalg.norm(c - center)

        # If the current sphere is already contained
        if dist + r <= radius:
            continue

        # If the bounding sphere is contained within current
        if dist + radius <= r:
            center, radius = c, r
            continue

        # Otherwise, calculate the new bounding sphere
        new_radius = (dist + radius + r) / 2
        new_center = center + ((new_radius - radius) / dist) * (c - center)
        center, radius = new_center, new_radius

    return (center, radius)


def calculate_normals(vertices, faces):
    # DEPRECATED: Not used in the current implementation
    # Calculate the vectors representing two sides of each triangle
    v1 = vertices[faces[:, 1] - 1] - vertices[faces[:, 0] - 1]
    v2 = vertices[faces[:, 2] - 1] - vertices[faces[:, 0] - 1]

    # Calculate the cross product of the vectors to get the face normals
    face_normals = np.cross(v1, v2)

    # Normalize the face normals
    face_normals /= np.linalg.norm(face_normals, axis=1)[:, np.newaxis]

    # Initialize an array for the vertex normals
    vertex_normals = np.zeros(vertices.shape, dtype=vertices.dtype)

    # Add each face's normal to its vertices' normals
    np.add.at(vertex_normals, faces - 1, face_normals[:, np.newaxis])

    # Normalize the vertex normals
    vertex_normals /= np.linalg.norm(vertex_normals, axis=1)[:, np.newaxis]

    return vertex_normals


def visualize_adjacencies(adjacencies):
    import networkx as nx
    import matplotlib.pyplot as plt
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
    import networkx as nx
    import matplotlib.pyplot as plt
    G = nx.Graph()
    for i, adj in adjacencies.items():
        for j in adj:
            G.add_edge(i, j)

    print(f"Drawing graph with {len(G.nodes)} nodes and {len(G.edges)} edges.")
    nx.draw(G, with_labels=label)
    plt.show()
    plt.pause(0.01)
