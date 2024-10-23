import numpy as np

from LODtris import ClusterMesh

THRESHOLD = 0.00006
MARGIN = 0.00003 # Unfortunately we need this hysteresis? The error and radii should be monotonic!

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
        current_clusters = self.cluster_mesh.clusters.copy()
        errors = {}

        cur_clust = list(current_clusters)
        errors.update(zip(cur_clust, self.calc_screen_space_error(cur_clust)))
        prev_error_keys = set(cur_clust)

        for __ in range(num_steps):
            to_remove = set()
            to_add = set()

            for cluster in list(current_clusters):
                if cluster in to_remove or cluster in to_add:
                    continue
                
                cluster_error = errors[cluster]

                # Coarsening (decrease lod)
                if cluster_error < THRESHOLD - MARGIN:
                    if cluster != self.last_cluster:
                        parents = self.lod_dag.cluster_dag[cluster]
                        for p in parents:
                            to_remove.update(self.lod_dag.cluster_dag_rev[p])
                        to_add.update(parents)
                
                # Refinement (increase lod)
                elif cluster_error > THRESHOLD + MARGIN:
                    all_kids = self.lod_dag.cluster_dag_rev[cluster]
                    if all_kids[0] != 0:
                        to_add.update(all_kids)
                        for k in all_kids:
                            to_remove.update(self.lod_dag.cluster_dag[k])

            if to_remove or to_add:
                current_clusters.update(to_add)
                current_clusters.difference_update(to_remove)

                to_update = list(to_add.difference(prev_error_keys))
                errors.update(zip(to_update, self.calc_screen_space_error(to_update)))
                prev_error_keys.update(to_update)

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

        # We are inside the bounding sphere
        result[dists <= 0] = np.inf

        return result

    def update(self):
        self.cluster_mesh.draw()

    def shutdown(self):
        self.cluster_mesh.shutdown()
