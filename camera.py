import numpy as np
from OpenGL.GL import glGetFloatv, GL_MODELVIEW_MATRIX


class Camera:
    def __init__(self):
        self.position = np.array([0, 0.85, -4], dtype=np.float32)
        self.look_angle = np.array([180.0, 0.0], dtype=np.float32)  # Horizontal and vertical angles

    def update(self):
        # Update the camera position and frustum
        # Returns True if anything changed
        matrix = glGetFloatv(GL_MODELVIEW_MATRIX)

        # Clipping planes
        self.planes = np.array(
            [
                self.normalize_plane(matrix[3] + matrix[0]),  # Left
                self.normalize_plane(matrix[3] - matrix[0]),  # Right
                self.normalize_plane(matrix[3] + matrix[1]),  # Bottom
                self.normalize_plane(matrix[3] - matrix[1]),  # Top
                self.normalize_plane(matrix[3] + matrix[2]),  # Near
                self.normalize_plane(matrix[3] - matrix[2]),  # Far
            ]
        )

    def normalize_plane(self, plane):
        length = np.linalg.norm(plane[:3])
        return plane / length

    def is_sphere_in_frustum(self, pos, radius):
        pos = np.array(pos) - self.position
        for i in range(6):
            if np.dot(self.planes[i][:3], pos) + self.planes[i][3] <= -radius:
                return False
        return True
    