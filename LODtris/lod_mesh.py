import numpy as np

from LODtris import ClusterMesh

THRESHOLD = 0.00006
MARGIN = 0.00002 # Unfortunately we need this hysteresis? The error and radii should be monotonic!

class LODMesh:
    def __init__(self, lod_dag, camera, position):
        self.lod_dag = lod_dag
        self.camera = camera
        self.position = position
        self.cluster_mesh = ClusterMesh(
            position,
            lod_dag.cluster_verts,
            lod_dag.cluster_textures,
            lod_dag.texture_id,
            lod_dag.cluster_normals,
        )

        self.spheres = self.lod_dag.cluster_bounding_centers + position
        self.last_cluster = len(self.lod_dag.cluster_verts) - 1

    def debug_set_min_lod(self):
        self.cluster_mesh.set_clusters({len(self.lod_dag.cluster_verts) - 1})

    def debug_set_max_lod(self):
        self.cluster_mesh.set_clusters(self.lod_dag.cluster_dag[0])

    def step_graph_cut(self, num_steps=3):
        any_change = False
        for __ in range(num_steps):
            to_remove = set()
            to_add = set()

            current_clusters = self.cluster_mesh.clusters
            errors = self.calc_screen_space_error(list(current_clusters))

            for cluster, cluster_error in zip(current_clusters, errors):
                if cluster in to_remove:
                    continue
                if cluster in to_add:
                    continue

                # Coarsening (decrease lod)
                if cluster_error < THRESHOLD - MARGIN:
                    if cluster != self.last_cluster:
                        parents = self.lod_dag.cluster_dag[cluster]
                        to_remove.update(self.lod_dag.cluster_dag_rev[parents[0]])
                        to_add.update(parents)
                
                # Refinement (increase lod)
                elif cluster_error > THRESHOLD + MARGIN:
                    all_kids = self.lod_dag.cluster_dag_rev[cluster]
                    if all_kids[0] != 0:
                        to_add.update(all_kids)
                        to_remove.update(self.lod_dag.cluster_dag[all_kids[0]])

            if to_remove or to_add:
                current_clusters.update(to_add)
                current_clusters -= to_remove
                any_change = True

            else:
                break

        if any_change:
            self.cluster_mesh.set_clusters(current_clusters)

        return any_change

    def calc_screen_space_error(self, clusters):
        dists = np.linalg.norm(self.camera.position - self.spheres[clusters], axis=1)
        dists -= self.lod_dag.cluster_bounding_radii[clusters]
        result = self.lod_dag.cluster_errors[clusters] / dists

        # Culling
        in_front = self.camera.check_in_front(self.spheres[clusters])
        result[~in_front] = 0
        result[dists <= 0] = np.inf  # We are inside bounding sphere

        return result

    def update(self):
        self.cluster_mesh.draw()

    def shutdown(self):
        self.cluster_mesh.shutdown()
