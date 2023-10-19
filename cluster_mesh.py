from OpenGL.GL import *

from OpenGL.arrays import vbo
import numpy as np


class ClusterMesh:
    """Drawing a mesh with multiple clusters made up of tris."""

    def __init__(self, position, cluster_verts):
        self.position = position
        self.cluster_verts = [np.float32((verts + position).ravel()) for verts in cluster_verts[1:]]
        self.cluster_verts.insert(0, [])
        
        self.master_vbo = None
        self.clusters = set([len(self.cluster_verts) - 1])

    def add_clusters(self, cluster_ids):
        self.clusters.update(cluster_ids)
        self.update_vbo()

    def remove_clusters(self, cluster_ids):
        self.clusters -= cluster_ids
        self.update_vbo()

    def set_clusters(self, cluster_ids):
        self.clusters = cluster_ids
        self.update_vbo()

    def reset_clusters(self):
        self.clusters = set()
        self.num_vertices = 0
        self.master_vbo = None

    def draw(self):
        if self.master_vbo is None:
            self.update_vbo()

        self.master_vbo.bind()
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, self.master_vbo)
        glColor3f(0.6, 0.4, 0.2)
        glDrawArrays(GL_TRIANGLES, 0, self.num_vertices)
        glDisableClientState(GL_VERTEX_ARRAY)
        self.master_vbo.unbind()

    def update_vbo(self):
        # Call this function every time the clusters change
        vertices = np.concatenate([self.cluster_verts[id] for id in self.clusters])
        self.num_vertices = vertices.size

        if self.master_vbo is None:
            self.master_vbo = vbo.VBO(vertices)
        else:
            self.master_vbo.set_array(vertices)
            self.master_vbo.bind()
            self.master_vbo.copy_data()
            self.master_vbo.unbind()


# class ClusterRenderer:
#     def __init__(self):
#         self.meshes = []
#         self.master_vbo = None

#     def add_mesh(self, mesh):
#         # Add a ClusterMesh
#         self.meshes.append(mesh)
#         self.update_vbo()

#     def remove_mesh(self, mesh):
#         if mesh in self.meshes:
#             self.meshes.remove(mesh)
#             self.update_vbo()

#     # def set_mesh_clusters(self, mesh_id, cluster_ids):
#     #     self.meshes[mesh_id].set_clusters(cluster_ids)
    
#     def draw(self):
#         if self.master_vbo is None:
#             self.update_vbo()

#         self.master_vbo.bind()
#         glEnableClientState(GL_VERTEX_ARRAY)
#         glVertexPointer(3, GL_FLOAT, 0, self.master_vbo)
#         glColor3f(0.6, 0.4, 0.2)
#         glDrawArrays(GL_TRIANGLES, 0, self.total_vertices)
#         glDisableClientState(GL_VERTEX_ARRAY)
#         self.master_vbo.unbind()

#     def update_vbo(self):
#         vertices = np.concatenate([mesh.cluster_verts[i] for mesh in self.meshes for i in mesh.clusters])
#         self.total_vertices = vertices.size

#         if self.master_vbo is None:
#             self.master_vbo = vbo.VBO(vertices)
#         else:
#             self.master_vbo.set_array(vertices)
#             self.master_vbo.bind()
#             self.master_vbo.copy_data()
#             self.master_vbo.unbind()


# class ClusterMesh:
#     """Drawing a mesh with multiple clusters made up of tris."""

#     def __init__(self, position, cluster_verts):
#         self.position = position
#         self.cluster_verts = [np.float32((verts + position).ravel()) for verts in cluster_verts[1:]]
#         self.cluster_verts.insert(0, [])

#         # We start with the least detailed LOD
#         self.clusters = set([len(self.cluster_verts) - 1])

#     def set_clusters(self, cluster_ids):
#         self.clusters = cluster_ids