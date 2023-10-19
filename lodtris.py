import sys
import subprocess
from cProfile import Profile

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

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
        # profiler.dump_stats("profile/profile.prof")
        # subprocess.run(
        #     ["gprof2dot", "-f", "pstats", "profile/profile.prof", "-o", "profile/call_graph.dot"]
        # )
        # subprocess.run(["dot", "-Tpng", "profile/call_graph.dot", "-o", "profile/call_graph.png"])
        # sys.exit(0)

        pygame.init()
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 36)

        self.display_dim = display_dim
        self.display = pygame.display.set_mode(display_dim, DOUBLEBUF | OPENGL)
        pygame.display.set_caption("LODTris 0.1")
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
        position = np.array(position)
        mesh = LODMesh(self.models[model_name], self.camera, position)
        self.meshes.append(mesh)

    def run(self):
        profiler = Profile()
        profiler.enable()

        def do_quit():
            profiler.disable()
            profiler.dump_stats("profile/profile.prof")
            subprocess.run(
                [
                    "gprof2dot",
                    "-f",
                    "pstats",
                    "profile/profile.prof",
                    "-o",
                    "profile/call_graph.dot",
                ]
            )
            subprocess.run(
                [
                    "dot",
                    "-Tpng",
                    "profile/call_graph.dot",
                    "-o",
                    "profile/call_graph.png",
                ]
            )
            pygame.quit()

        start_ticks = pygame.time.get_ticks()  # Starter tick
        frames = 0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    do_quit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        do_quit()

            self.__update_view()

            self.camera.update()
            for mesh in self.meshes:
                if self.dynamicLOD:
                    mesh.step_graph_cut()
                mesh.update()

            # if frames % 10 == 0: # Every 10 frames, update the FPS counter
            #     end_ticks = pygame.time.get_ticks()
            #     fps = 10000 / (end_ticks - start_ticks)
            #     start_ticks = end_ticks
            #     print(f"FPS: {fps} | Triangles: {self.renderer.total_vertices // 3}")
            #     fps_text = self.font.render(f"FPS: {fps}", True, (255, 255, 255))
            #     triangles_text = self.font.render(f"Triangles: {self.renderer.total_vertices // 3}", True, (255, 255, 255))

            # print(f"Triangles: {self.renderer.total_vertices // 3}")
            # self.display.blit(fps_text, (10, 10))
            # self.display.blit(triangles_text, (10, 50))

            pygame.display.flip()
            pygame.time.delay(1000 // 120)  # Limit 120 FPS
            frames += 1

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

        glRotatef(mouse_move[0] * 0.1, 0, 1, 0)
        glRotatef(-mouse_move[1] * 0.1, 1, 0, 0)

        # On keypress e toggle dynamic LOD
        if keypress[pygame.K_e] and not self.prevKeyState[pygame.K_e]:
            self.dynamicLOD = not self.dynamicLOD
            print("Dynamic LOD: " + str(self.dynamicLOD))

        self.prevKeyState = keypress


if __name__ == "__main__":
    viewer = LODTrisViewer()
    for z in range(7):
        for x in range(7):
            viewer.create_mesh_from_model("flower", (x * 5, 0, z * 5))

    viewer.run()
