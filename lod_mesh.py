from functools import lru_cache

import numpy as np

from cluster_mesh import ClusterMesh

THRESHOLD = 0.00003


class LODMesh:
    def __init__(self, lod_dag, camera, position=(0, 0, 0)):
        self.lod_dag = lod_dag
        self.position = np.array(position)
        self.cluster_mesh = ClusterMesh(position, lod_dag.cluster_verts)

        # We start with the least detailed LOD
        self.current_clusters = set([len(self.lod_dag.cluster_dag_rev) - 1])
        self.cluster_mesh.add_clusters(self.current_clusters)

        self.cached_error = {}
        self.camera = camera

    def step_graph_cut(self, num_steps=1):
        self.cached_error = {}

        any_change = False
        for step_i in range(num_steps):
            # For each of the current clusters, check if we want to change the graph cut
            to_remove = set()
            to_add = set()

            for cluster in sorted(self.current_clusters):
                if cluster in to_remove:
                    continue
                if cluster in to_add:
                    continue

                # Refinement (increase lod): Check max error of all children
                cluster_error = self.calc_screen_space_error(cluster)
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
                        continue

                # Coarsening
                if cluster_error <= THRESHOLD:
                    parents = self.lod_dag.cluster_dag[cluster]
                    if len(parents) > 0:
                        all_kids = self.lod_dag.cluster_dag_rev[parents[0]]
                        to_remove.update(all_kids)
                        to_add.update(parents)

            if to_remove or to_add:
                self.current_clusters.update(to_add)
                self.current_clusters -= to_remove
                any_change = True

        if any_change:
            self.cluster_mesh.set_clusters(self.current_clusters)

    def calc_screen_space_error(self, cluster_i):
        if cluster_i in self.cached_error:
            return self.cached_error[cluster_i]
        else:
            error = self.calc_screen_space_error_raw(cluster_i)
            self.cached_error[cluster_i] = error
            return error

    def calc_screen_space_error_raw(self, cluster_i):
        # Calculate the view dependent screen space error for a cluster
        sphere_pos, sphere_radius = self.lod_dag.cluster_bounding_spheres[cluster_i]
        sphere_pos = sphere_pos + self.position
        geometric_error = self.lod_dag.cluster_errors[cluster_i]

        # Check if bounding sphere is outside frustum
        # if not self.camera.is_sphere_in_frustum(sphere_pos, sphere_radius):
        #     return 0

        # Check if the camera is inside the bounding sphere
        dist = np.linalg.norm(self.camera.position - sphere_pos)
        if dist <= sphere_radius:
            return float("inf")

        return geometric_error / (dist - sphere_radius)

    def update(self):
        self.cluster_mesh.draw()
