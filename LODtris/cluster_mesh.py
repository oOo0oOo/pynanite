from OpenGL.GL import *

from OpenGL.arrays import vbo
import numpy as np


class ClusterMesh:
    """Drawing a mesh with multiple clusters made up of tris."""

    def __init__(
        self, position, cluster_verts, cluster_textures_ravelled, texture_id, cluster_normals_ravelled
    ):
        self.position = position
        self.texture_id = texture_id
        self.cluster_textures = cluster_textures_ravelled
        self.cluster_normals = cluster_normals_ravelled

        self.cluster_verts = [None]
        position = np.array(position, dtype=np.float32)
        for i in range(1, len(cluster_verts)):
            self.cluster_verts.append((cluster_verts[i] + position).ravel())
        
        self.vertex_vbo = None
        self.tex_vbo = None
        self.norm_vbo = None
        self.clusters = set([len(self.cluster_verts) - 1])

    def set_clusters(self, cluster_ids):
        self.clusters = cluster_ids
        self.update_vbo()

    def bind_buffers(self):
        if self.vertex_vbo is None:
            self.update_vbo()

        self.vertex_vbo.bind()
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, self.vertex_vbo)

        self.tex_vbo.bind()
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glTexCoordPointer(2, GL_FLOAT, 0, self.tex_vbo)

        self.norm_vbo.bind()
        glEnableClientState(GL_NORMAL_ARRAY)
        glNormalPointer(GL_FLOAT, 0, self.norm_vbo)

    def unbind_buffers(self):
        glDisableClientState(GL_NORMAL_ARRAY)
        self.norm_vbo.unbind()

        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        self.tex_vbo.unbind()

        glDisableClientState(GL_VERTEX_ARRAY)
        self.vertex_vbo.unbind()

    def draw(self):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        self.bind_buffers()

        glDrawArrays(GL_TRIANGLES, 0, self.num_vertices)

        self.unbind_buffers()
        glDisable(GL_TEXTURE_2D)

    def update_vbo(self):
        # Call this function every time the clusters change
        vertices = np.concatenate([self.cluster_verts[id] for id in self.clusters])
        texcoords = np.concatenate([self.cluster_textures[id] for id in self.clusters])
        normals = np.concatenate([self.cluster_normals[id] for id in self.clusters])
        self.num_vertices = vertices.size

        if self.vertex_vbo is None:
            self.vertex_vbo = vbo.VBO(vertices)
            self.tex_vbo = vbo.VBO(texcoords)
            self.norm_vbo = vbo.VBO(normals)

        else:
            self.vertex_vbo.set_array(vertices)
            self.vertex_vbo.bind()
            self.vertex_vbo.copy_data()
            self.vertex_vbo.unbind()

            self.tex_vbo.set_array(texcoords)
            self.tex_vbo.bind()
            self.tex_vbo.copy_data()
            self.tex_vbo.unbind()

            self.norm_vbo.set_array(normals)
            self.norm_vbo.bind()
            self.norm_vbo.copy_data()
            self.norm_vbo.unbind()

    def shutdown(self):
        self.vertex_vbo.delete()
        self.tex_vbo.delete()
        self.norm_vbo.delete()