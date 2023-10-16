from OpenGL.GL import *

from OpenGL.arrays import vbo
import numpy as np
import matplotlib.cm as cm
from matplotlib import colors


class ClusterMesh:
    """Drawing a mesh with multiple clusters made up of tris."""

    def __init__(self, position, cluster_verts):
        self.clusters = set()
        self.position = position
        self.cluster_verts = cluster_verts
        self.master_vbo = None

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
        if self.master_vbo is not None:
            self.master_vbo.delete()

        vertices = [self.cluster_verts[id] for id in self.clusters]
        vertices = np.concatenate(vertices) + self.position
        self.num_vertices = vertices.size
        self.master_vbo = vbo.VBO(np.float32(vertices.ravel()))
