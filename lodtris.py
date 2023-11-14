import sys
import subprocess
from cProfile import Profile
from time import time

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

from lod_mesh import LODMesh
from lod_graph import LODGraph
from camera import Camera


MODELS = {
    # "flower": [
    #     "data/Flower.obj/Flower.obj",
    #     "data/Flower.obj/Flower_0.jpg",
    #     "data/build/Flower.pickle"
    # ],
    "cat": [
        "data/Cat.obj/Cat.obj",
        "data/Cat.obj/Cat.jpg",
        "data/build/Cat.pickle",
    ]
}


class LODTrisViewer:
    def __init__(self, display_dim=(1920, 1080)):
        pygame.init()
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 20)

        self.display_dim = display_dim
        self.display = pygame.display.set_mode(display_dim, DOUBLEBUF | OPENGL)
        pygame.display.set_caption("LODTris 0.1")

        self.cameraStartPos = [0, 0.5, -4]
        self.prevKeyState = None
        self.dynamicLOD = True
        self.__init_opengl()

        self.meshes = []

        # profiler = Profile()
        # profiler.enable()
        self.models = {k: LODGraph(v) for k, v in MODELS.items()}
        # profiler.disable()
        # profiler.dump_stats("profile/profile.prof")
        # subprocess.run(
        #     ["gprof2dot", "-f", "pstats", "profile/profile.prof", "-o", "profile/call_graph.dot"]
        # )
        # subprocess.run(["dot", "-Tpng", "profile/call_graph.dot", "-o", "profile/call_graph.png"])
        # sys.exit(0)

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

        # Enable lighting
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 0.0, 1.0, 0.0])

        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (self.display_dim[0] / self.display_dim[1]), 0.1, 100.0)
        glEnable(GL_DEPTH_TEST)

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
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

        # profiler = Profile()
        # profiler.enable()

        def do_quit():
            # profiler.disable()
            # profiler.dump_stats("profile/profile.prof")
            # subprocess.run(
            #     [
            #         "gprof2dot",
            #         "-f",
            #         "pstats",
            #         "profile/profile.prof",
            #         "-o",
            #         "profile/call_graph.dot",
            #     ]
            # )
            # subprocess.run(
            #     [
            #         "dot",
            #         "-Tpng",
            #         "profile/call_graph.dot",
            #         "-o",
            #         "profile/call_graph.png",
            #     ]
            # )
            pygame.quit()

        self.last_time = time()  # Starter tick
        self.delta = 0
        textSurface = self.font.render("", True, (255, 255, 255))
        textData = pygame.image.tostring(textSurface, "RGBA", True)

        frames = 0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    do_quit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        do_quit()

            cur_time = time()
            self.delta = cur_time - self.last_time
            self.last_time = cur_time

            self.__update_view()

            for mesh in self.meshes:
                if self.dynamicLOD:
                    mesh.step_graph_cut()
                mesh.update()

            if frames % 60 == 0:  # Every 60 frames, update the FPS counter
                triangles = sum([m.cluster_mesh.num_vertices // 9 for m in self.meshes])
                triangles = round(triangles / 1000000, 2)

                fps = 1 / self.delta
                msg = f"Dynamic LOD: {self.dynamicLOD} | FPS: {round(fps, 1)} | Triangles: {triangles} M"
                textSurface = self.font.render(
                    msg, True, (255, 255, 255, 255), (0, 0, 0, 0)
                )
                textData = pygame.image.tostring(textSurface, "RGBA", True)

            # Save current matrices
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0.0, self.display_dim[0], self.display_dim[1], 0.0, -1.0, 1.0)

            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()

            glRasterPos2i(5, 20)
            glDrawPixels(
                textSurface.get_width(),
                textSurface.get_height(),
                GL_RGBA,
                GL_UNSIGNED_BYTE,
                textData,
            )

            # Restore previous matrices
            glPopMatrix()
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)

            pygame.display.flip()
            pygame.time.delay(1000 // 120)  # Limit 120 FPS
            frames += 1

    def __update_view(self):
        keypress = pygame.key.get_pressed()
        mouse_move = pygame.mouse.get_rel()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Update the camera position based on keypress
        movement_speed = 2.0 * self.delta
        if keypress[pygame.K_LSHIFT]:
            movement_speed *= 8
        
        xangle = self.camera.look_angle[0]
        if keypress[pygame.K_w]:
            self.camera.position[0] += -np.sin(xangle) * movement_speed
            self.camera.position[2] += -np.cos(xangle) * movement_speed
        if keypress[pygame.K_s]:
            self.camera.position[0] += np.sin(xangle) * movement_speed
            self.camera.position[2] += np.cos(xangle) * movement_speed
        if keypress[pygame.K_a]:
            self.camera.position[0] += np.sin(xangle - np.pi/2) * movement_speed
            self.camera.position[2] += np.cos(xangle - np.pi/2) * movement_speed
        if keypress[pygame.K_d]:
            self.camera.position[0] += np.sin(xangle + np.pi/2) * movement_speed
            self.camera.position[2] += np.cos(xangle + np.pi/2) * movement_speed

        # Rotate view according to mouse movement
        mouse_move = np.maximum(np.minimum(mouse_move, 80), -80)
        self.camera.look_angle[0] -= mouse_move[0] * 0.05 * self.delta
        self.camera.look_angle[1] -= mouse_move[1] * 0.035 * self.delta

        # Update the camera's position and orientation
        glLoadIdentity()
        gluLookAt(
            self.camera.position[0], self.camera.position[1], self.camera.position[2], 
            self.camera.position[0] - np.sin(self.camera.look_angle[0]) * np.cos(self.camera.look_angle[1]), 
            self.camera.position[1] + np.sin(self.camera.look_angle[1]), 
            self.camera.position[2] - np.cos(self.camera.look_angle[0]) * np.cos(self.camera.look_angle[1]), 
            0, 1, 0
        )

        # self.camera.update()

        # On keypress e toggle dynamic LOD
        if keypress[pygame.K_e] and not self.prevKeyState[pygame.K_e]:
            self.dynamicLOD = not self.dynamicLOD

        # Save screenshot on keypress p
        if keypress[pygame.K_p] and not self.prevKeyState[pygame.K_p]:
            width, height = pygame.display.get_surface().get_size()
            glReadBuffer(GL_FRONT)
            pixels = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
            image = pygame.image.fromstring(pixels, (width, height), 'RGB')
            image = pygame.transform.flip(image, False, True)  # Flip the image vertically
            pygame.image.save(image, f"screenshots/{int(time())}.png")

        self.prevKeyState = keypress


if __name__ == "__main__":
    viewer = LODTrisViewer()
    for z in range(5):
        for x in range(10):
            viewer.create_mesh_from_model("cat", (x * 5, 0, z * 5))

    viewer.run()
