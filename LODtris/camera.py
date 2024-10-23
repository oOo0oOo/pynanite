import numpy as np
from OpenGL.GL import glLoadIdentity, glFlush
from OpenGL.GLU import gluLookAt

class Camera:
    def __init__(self):
        self.position = np.array([0, 0.85, -4], dtype=np.float32)
        self.look_angle = np.pi
        self.cos_half_fov = np.cos(np.pi / 4)

    def get_forward_vector(self):
        return np.array([-np.sin(self.look_angle), 0, -np.cos(self.look_angle)])

    def update(self, delta_pos, delta_angle):
        self.position += delta_pos
        self.look_angle -= delta_angle[0]
        glLoadIdentity()
        forward = self.get_forward_vector()
        center = self.position + forward
        gluLookAt(*self.position, *center, 0, 1, 0)
        glFlush()

    def check_in_front(self, world_positions):
        forward = self.get_forward_vector()
        directions = world_positions - self.position
        directions /= np.linalg.norm(directions, axis=1, keepdims=True)
        dot_products = directions @ forward
        return dot_products > self.cos_half_fov