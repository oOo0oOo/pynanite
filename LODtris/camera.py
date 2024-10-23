import numpy as np
from OpenGL.GL import glLoadIdentity, glFlush
from OpenGL.GLU import gluLookAt

class Camera:
    def __init__(self):
        self.position = np.array([0, 3, -4], dtype=np.float32)
        self.look_angle = [3.8, -0.3]
        self.cos_half_fov = np.cos(np.pi / 4)
        self.forward = self._get_forward_vector()

    def _get_forward_vector(self):
        return np.array([
            -np.sin(self.look_angle[0]) * np.cos(self.look_angle[1]),
            np.sin(self.look_angle[1]), 
            -np.cos(self.look_angle[0]) * np.cos(self.look_angle[1])])

    def update(self, delta_pos, delta_angle):
        self.position += delta_pos
        self.look_angle -= delta_angle
        glLoadIdentity()
        self.forward = self._get_forward_vector()
        gluLookAt(*self.position, *(self.position + self.forward), 0, 1, 0)
        glFlush()

    def check_in_front(self, world_positions):
        directions = world_positions - self.position
        directions /= np.linalg.norm(directions, axis=1, keepdims=True)
        dot_products = np.dot(directions, self.forward)
        return dot_products > self.cos_half_fov