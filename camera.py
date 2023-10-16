import numpy as np
from OpenGL.GL import glGetFloatv, GL_MODELVIEW_MATRIX

class Camera:
    def __init__(self):
        self.last_matrix = np.array([])
        self.update()

    def update(self):
        # Update the camera position and frustum
        # Returns True if anything changed
        matrix = glGetFloatv(GL_MODELVIEW_MATRIX)

        if np.array_equal(matrix, self.last_matrix):
            return False

        # Camera position
        self.position = matrix[3][:3]
        matrix = matrix.T

        # Clipping planes
        self.planes = np.array([
            self.normalize_plane(matrix[3] + matrix[0]), # Left
            self.normalize_plane(matrix[3] - matrix[0]), # Right
            self.normalize_plane(matrix[3] + matrix[1]), # Bottom
            self.normalize_plane(matrix[3] - matrix[1]), # Top
            self.normalize_plane(matrix[3] + matrix[2]), # Near
            self.normalize_plane(matrix[3] - matrix[2])  # Far
        ])

        self.last_matrix = matrix
        return True

    def normalize_plane(self, plane):
        length = np.linalg.norm(plane[:3])  
        return plane / length
    
    # def is_sphere_in_frustum(self, pos, radius):
    #     for i in range(6):
    #         if np.dot(self.planes[i][:3], pos) + self.planes[i][3] <= -radius:
    #             return False
    #     return True
    def is_sphere_in_frustum(self, pos, radius):
        pos = np.array(pos) - self.position
        for i in range(6):
            if np.dot(self.planes[i][:3], pos) + self.planes[i][3] <= -radius:
                return False
        return True