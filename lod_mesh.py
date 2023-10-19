import numpy as np

from cluster_mesh import ClusterMesh

THRESHOLD = 0.00006


class LODMesh:
    def __init__(self, lod_dag, camera, position):
        self.lod_dag = lod_dag
        self.camera = camera
        self.position = position
        self.cluster_mesh = ClusterMesh(position, lod_dag.cluster_verts)

        # Precalc the bounding sphere translation
        self.spheres = self.lod_dag.cluster_bounding_centers.copy() + position

    def step_graph_cut(self, num_steps=1):
        any_change = False
        for __ in range(num_steps):
            # For each of the current clusters, check if we want to change the graph cut
            to_remove = set()
            to_add = set()

            current_clusters = self.cluster_mesh.clusters
            errors = self.calc_screen_space_error(list(current_clusters))

            for cluster, cluster_error in zip(current_clusters, errors):
                if cluster in to_remove:
                    continue
                if cluster in to_add:
                    continue

                # Refinement (increase lod): Check max error of all children
                if cluster_error > THRESHOLD:
                    all_kids = self.lod_dag.cluster_dag_rev[cluster]

                    refine = True
                    if len(all_kids) == 1:
                        if all_kids[0] == 0:
                            refine = False

                    if refine:
                        co_parents = self.lod_dag.cluster_dag[all_kids[0]]
                        to_add.update(all_kids)
                        to_remove.update(co_parents)

                # Coarsening
                elif cluster_error < THRESHOLD * 0.5:
                    parents = self.lod_dag.cluster_dag[cluster]
                    if len(parents) > 0:
                        all_kids = self.lod_dag.cluster_dag_rev[parents[0]]
                        to_remove.update(all_kids)
                        to_add.update(parents)

            if to_remove or to_add:
                current_clusters.update(to_add)
                current_clusters -= to_remove
                any_change = True

        if any_change:
            self.cluster_mesh.set_clusters(current_clusters)

        return any_change

    def calc_screen_space_error(self, clusters):
        dists = np.linalg.norm(self.camera.position - self.spheres[clusters], axis=1)
        dists -= self.lod_dag.cluster_bounding_radii[clusters]
        result = self.lod_dag.cluster_errors[clusters] / dists
        result[dists <= 0] = np.inf  # We are inside bounding sphere
        # TODO: Check if bounding sphere is outside frustum
        return result
    
    def update(self):
        self.cluster_mesh.draw()
