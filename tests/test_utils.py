##
#
# python -m unittest discover -s tests
# These tests are not working. Only useful as a starting point...
#
##


import unittest
import os

import numpy as np

# Set the METIS_DLL environment variable to the current path
current_path = os.path.abspath(os.path.dirname(__file__))
parent_path = os.path.abspath(os.path.join(current_path, os.pardir))
os.environ["METIS_DLL"] = os.path.join(parent_path, "libmetis.so")

from LODtris.utils import group_tris, simplify_mesh_inside, create_dual_graph

from LODtris.lod_graph import next_lod, combine_group_lods

def create_grid_mesh_tris(size=(256, 256)):
    vertices = []
    tris = []
    for x in range(size[0]):
        for y in range(size[1]):
            vertices.append([x, y, 0])
            if x < size[0] - 1 and y < size[1] - 1:
                tris.append(
                    [x + y * size[0], x + 1 + y * size[0], x + (y + 1) * size[0]]
                )
                tris.append(
                    [
                        x + 1 + y * size[0],
                        x + (y + 1) * size[0],
                        x + 1 + (y + 1) * size[0],
                    ]
                )
    vertices = np.array(vertices, dtype=np.float32)
    tris = np.array(tris, dtype=np.uint32)

    adjacencies = create_dual_graph(tris)

    return vertices, tris, adjacencies


class TestSimplifyMesh(unittest.TestCase):
    def test_preserved_borders(self):
        vertices, tris, __ = create_grid_mesh_tris()
        v_simple, t_simple = simplify_mesh_inside(vertices, tris, removal_ratio=0.5)
        self.assertTrue(len(t_simple) < len(tris) * 0.55)

        border_vertices = []
        for x in range(256):
            border_vertices.append([x, 0, 0])
            border_vertices.append([x, 255, 0])
        for y in range(256):
            border_vertices.append([0, y, 0])
            border_vertices.append([255, y, 0])
        border_vertices = np.array(border_vertices, dtype=np.float32)

        # Check that the borders are preserved
        for vertex in border_vertices:
            self.assertTrue(np.any(np.all(vertex == v_simple, axis=1)))


class TestCombineLods(unittest.TestCase):
    def test_combine_lods(self):
        vertices, tris, adj = create_grid_mesh_tris()

        clusters = np.zeros(len(tris), dtype=np.uint32)
        clusters[0:1000] = 1
        lod0 = (vertices, tris, adj, clusters)

        lod_comb = combine_group_lods([lod0], clusters)
        assert np.array_equal(lod_comb[0], vertices)
        assert np.array_equal(lod_comb[1], tris)
        assert np.array_equal(lod_comb[3], clusters)

        vertices_shifted = vertices.copy()
        vertices_shifted[:, 2] += 10
        lod1 = (vertices_shifted, tris, adj, clusters)

        lod_comb = combine_group_lods([lod0, lod1], clusters)

        self.assertIsInstance(lod_comb, tuple)
        self.assertEqual(len(lod_comb), 4)
        self.assertIsInstance(lod_comb[0], np.ndarray)
        self.assertIsInstance(lod_comb[1], np.ndarray)
        self.assertIsInstance(lod_comb[2], list)
        self.assertIsInstance(lod_comb[2][0], list)
        self.assertIsInstance(lod_comb[3], np.ndarray)

        assert np.array_equal(lod_comb[0], np.concatenate([vertices, vertices_shifted]))
        self.assertEqual(len(lod_comb[1]), len(tris) * 2)
        self.assertEqual(len(lod_comb[3]), len(clusters) * 2)

        n_vert = len(adj)

        exp_adj = [[v + n_vert for v in tri] for tri in adj]
        adj += exp_adj

        for i, v in enumerate(lod_comb[2]):
            if not np.array_equal(v, adj[i]):
                raise Exception("Adjacency mismatch:", i, v, adj[i])


class TestLOD(unittest.TestCase):
    def test_lod_pipeline(self):
        config = {
            "cluster_size_initial": 160,
            "cluster_size": 128,
            "group_size": 8
        }

        vertices, tris, adj = create_grid_mesh_tris()
        adjacencies, clusters = group_tris(tris, cluster_size=94)

        lods = [[vertices, tris, adjacencies, clusters, [], [], []]]
        num_clusters = max(clusters) + 1
        while num_clusters > 20:
            lods.append(next_lod(lods[-1], config, parallel=False))
            num_clusters = max(lods[-1][3]) + 1
        print(
            f"Finished simplification, created {len(lods)} LODs. {num_clusters} clusters remaining."
        )


if __name__ == "__main__":
    unittest.main()
