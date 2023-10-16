import sys
import subprocess
from cProfile import Profile

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from lod_mesh import LODMesh
from lod_graph import LODGraph
from camera import Camera


MODELS = {
    "flower": [
        "data/Flower.obj/Flower.obj",
        "data/Flower.obj/Flower_0.jpg",
    ]
}


class LODTrisViewer:
    def __init__(self, display_dim=(1920, 1080)):
        self.meshes = []

        # profiler = Profile()
        # profiler.enable()
        self.models = {k: LODGraph(v[0]) for k, v in MODELS.items()}
        # profiler.disable()
        # profiler.dump_stats("profile.prof")
        # subprocess.run(
        #     ["gprof2dot", "-f", "pstats", "profile.prof", "-o", "call_graph.dot"]
        # )
        # subprocess.run(["dot", "-Tpng", "call_graph.dot", "-o", "call_graph.png"])
        # sys.exit(0)

        pygame.init()
        self.display_dim = display_dim
        self.display = pygame.display.set_mode(display_dim, DOUBLEBUF | OPENGL)
        pygame.display.set_caption("LODtris 0.1")
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        
        self.cameraStartPos = [0, 0.5, -4]
        self.prevKeyState = None
        self.dynamicLOD = True
        self.__init_opengl()

    def __init_opengl(self):
        # ATTENTION: Disables backface culling
        # This is required for simplicity; not keeping track of normals
        # glDisable(GL_CULL_FACE)
        # glDisable(GL_LIGHTING)
        # glDisable(GL_DEPTH_TEST)

        glLoadIdentity()
        glClearColor(0.25, 0.25, 0.25, 1.0)

        # glShadeModel(GL_SMOOTH)
        # glEnable(GL_COLOR_MATERIAL)
        # glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        # glEnable(GL_LIGHT0)
        # glLightfv(GL_LIGHT0, GL_AMBIENT, [0.5, 0.5, 1, 1])
        # glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1])

        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (self.display_dim[0] / self.display_dim[1]), 0.1, 100.0)

        glMatrixMode(GL_MODELVIEW)
        gluLookAt(
            self.cameraStartPos[0],
            self.cameraStartPos[1],
            self.cameraStartPos[2],
            0,
            self.cameraStartPos[1],
            0,
            0,
            1,
            0,
        )
        self.camera = Camera()

    def create_mesh_from_model(self, model_name, position=(0, 0, 0)):
        mesh = LODMesh(self.models[model_name], self.camera, position)
        self.meshes.append(mesh)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return

            self.__update_view()

            self.camera.update()
            for mesh in self.meshes:
                if self.dynamicLOD:
                    mesh.step_graph_cut()
                mesh.update()

            pygame.display.flip()
            pygame.time.wait(1)

    def __update_view(self):
        keypress = pygame.key.get_pressed()
        mouse_move = pygame.mouse.get_rel()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        movement_speed = 0.1
        if keypress[pygame.K_w]:
            glTranslatef(0, 0, -movement_speed)
        if keypress[pygame.K_s]:
            glTranslatef(0, 0, movement_speed)
        if keypress[pygame.K_d]:
            glTranslatef(movement_speed, 0, 0)
        if keypress[pygame.K_a]:
            glTranslatef(-movement_speed, 0, 0)

        glRotatef(mouse_move[0]*0.1, 0, 1, 0)
        glRotatef(-mouse_move[1]*0.1, 1, 0, 0)
        
        # On keypress e toggle dynamic LOD
        if keypress[pygame.K_e] and not self.prevKeyState[pygame.K_e]:
            self.dynamicLOD = not self.dynamicLOD
            print("Dynamic LOD: " + str(self.dynamicLOD))

        self.prevKeyState = keypress


if __name__ == "__main__":
    viewer = LODTrisViewer()
    for z in range(10):
        for x in range(5):
            viewer.create_mesh_from_model("flower", (x * 5, 0, z * 5))

    viewer.run()
