import numpy as np
from OpenGL.GL import (
    glGetFloatv,
    GL_MODELVIEW_MATRIX,
    GL_PROJECTION_MATRIX,
    glLoadIdentity,
    glFlush
)
from OpenGL.GLU import gluLookAt

FOV_EXTENSION_FACTOR = 1.0

class Camera:
    
    def __init__(self):
        self.position = np.array([0, 0.85, -4], dtype=np.float32)
        self.look_angle = np.array([np.pi, 0], dtype=np.float32)  # Horizontal and vertical angles
    
    def update(self, delta_pos, delta_angle):
        self.position += delta_pos
        self.look_angle -= delta_angle
        self.look_angle[1] = np.maximum(np.minimum(self.look_angle[1], np.pi/2), -np.pi/2)

        # Update the camera's position and orientation
        glLoadIdentity()
        gluLookAt(
            self.position[0],
            self.position[1],
            self.position[2],
            self.position[0] - np.sin(self.look_angle[0]) * np.cos(self.look_angle[1]),
            self.position[1] + np.sin(self.look_angle[1]),
            self.position[2] - np.cos(self.look_angle[0]) * np.cos(self.look_angle[1]),
            0,
            1,
            0,
        )
        glFlush()
        
        # Get the inverse of the modelview matrix to bring points to the camera space
        modelview_matrix = glGetFloatv(GL_MODELVIEW_MATRIX)
        # modelview_matrix[0, :3] = self.position
        self.inv_modelview_matrix = np.linalg.inv(modelview_matrix)
        self.modelview_projection_matrix = glGetFloatv(GL_PROJECTION_MATRIX)

        # Calculate frustum planes
        clip_matrix = self.modelview_projection_matrix.T
        self.planes = np.array([
            self.normalize_clip_plane(clip_matrix[3] + clip_matrix[0]),  # left
            self.normalize_clip_plane(clip_matrix[3] - clip_matrix[0]),  # right
            self.normalize_clip_plane(clip_matrix[3] + clip_matrix[1]),  # bottom
            self.normalize_clip_plane(clip_matrix[3] - clip_matrix[1]),  # top
            self.normalize_clip_plane(clip_matrix[3] + clip_matrix[2]),  # near
            self.normalize_clip_plane(clip_matrix[3] - clip_matrix[2]),  # far
        ])
        
    def check_spheres_in_frustum(self, world_positions, radii):
        # Convert world space positions to camera space
        world_positions_homog = np.hstack([world_positions, np.ones((len(world_positions), 1))])
        cam_positions_homog = (self.inv_modelview_matrix @ world_positions_homog.T).T
        cam_positions = cam_positions_homog[:, :3]
        
        # Then perform frustum culling in camera space
        in_frustum = np.ones(len(cam_positions), dtype=bool)
        for i in range(6):
            in_frustum &= np.dot(self.planes[i][:3], cam_positions.T) + self.planes[i][3] > -radii
        
        return in_frustum
    
    def normalize_clip_plane(self, plane):
        length = np.linalg.norm(plane[:3])
        normed = plane / length

        # Extend the frustum planes to account for the field of view
        normed[3] *= FOV_EXTENSION_FACTOR
        return normed