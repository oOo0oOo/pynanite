import sys
import os
import subprocess
from cProfile import Profile
from time import time

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame
from pygame.locals import DOUBLEBUF, OPENGL
import numpy as np
from OpenGL.GLU import gluPerspective
from OpenGL.GL import (
    glLoadIdentity, glClearColor, glEnable, glLightfv,
    glMatrixMode, glClear, glPushMatrix, glPopMatrix,
    glOrtho, glRasterPos2i, glDrawPixels, glReadBuffer, glReadPixels,
    GL_LIGHTING, GL_LIGHT0, GL_DIFFUSE, GL_POSITION,
    GL_PROJECTION, GL_DEPTH_TEST, GL_CULL_FACE,
    GL_MODELVIEW, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    GL_RGB, GL_RGBA, GL_UNSIGNED_BYTE, GL_FRONT
)


# # Set the METIS_DLL environment variable to the current path
# Required if we want to use "import metis"
# current_path = os.path.abspath(os.path.dirname(__file__))
# os.environ["METIS_DLL"] = os.path.join(current_path, "libmetis.so")


from LODtris import LODMesh, LODGraph, Camera, __version__




STATS_DELAY = 1.0


class LODTrisViewer:
    def __init__(self, models, display_dim=(1920, 1080), profile_meshing=False, force_mesh_build=False,
                cluster_size_initial=160, cluster_size=128, group_size=8):
        
        print(f"Starting LODTris {__version__}")
        
        pygame.init()
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 20)

        self.display_dim = display_dim
        self.aspect_ratio = display_dim[0] / display_dim[1]
        self.display = pygame.display.set_mode(display_dim, DOUBLEBUF | OPENGL)
        pygame.display.set_caption("LODTris " + __version__)

        if not os.path.exists("data/build"):
            os.makedirs("data/build")

        self.cameraStartPos = [0, 0.5, -4]
        self.prevKeyState = None
        self.dynamicLOD = True
        self._init_opengl()

        self.meshes = []

        if profile_meshing:
            profiler = Profile()
            profiler.enable()
            start_time = time()
        
        self.models = {k: LODGraph(v, 
                                    force_mesh_build,
                                    cluster_size_initial,
                                    cluster_size,
                                    group_size
                                ) for k, v in models.items()}

        if profile_meshing:
            profiler.disable()
            profiler.dump_stats("profile/profile.prof")
            subprocess.run(
                ["gprof2dot", "-f", "pstats", "profile/profile.prof", "-o", "profile/call_graph.dot"]
            )
            subprocess.run(["dot", "-Tpng", "profile/call_graph.dot", "-o", "profile/call_graph.png"])
            print(f"Meshing took {time() - start_time:.2f} seconds")
            sys.exit(0)

    def _init_opengl(self):
        glLoadIdentity()
        glClearColor(0.25, 0.25, 0.25, 1.0)

        # glShadeModel(GL_SMOOTH)
        # glEnable(GL_COLOR_MATERIAL)
        # glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        # Enable lighting
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 0.0, 10.0, 0.0])

        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, self.aspect_ratio, 0.1, 200.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)

        glMatrixMode(GL_MODELVIEW)
        self.camera = Camera()

        # glClear(GL_COLOR_BUFFER_BIT)
        pygame.display.flip()

    def create_mesh_from_model(self, model_name, position=(0, 0, 0), profile=False):
        if profile:
            profiler = Profile()
            profiler.enable()

        position = np.array(position)
        mesh = LODMesh(self.models[model_name], self.camera, position)
        self.meshes.append(mesh)

        if profile:
            profiler.disable()
            profiler.dump_stats("profile/profile.prof")
            subprocess.run(
                ["gprof2dot", "-f", "pstats", "profile/profile.prof", "-o", "profile/call_graph.dot"]
            )
            subprocess.run(["dot", "-Tpng", "profile/call_graph.dot", "-o", "profile/call_graph.png"])
            sys.exit(0)

    def run(self, profile=False):
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

        if profile:
            profiler = Profile()
            profiler.enable()

        def do_quit():
            if profile:
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
            
            # Delete all VBOs properly
            for mesh in self.meshes:
                mesh.shutdown()

        self.last_time = time()
        self.next_stats_time = time() + STATS_DELAY
        self.delta = 0
        textSurface = self.font.render("", True, (255, 255, 255))
        textData = pygame.image.tostring(textSurface, "RGBA", True)

        textInstructions = self.font.render(
            "WASD (+ Shift) to move | Mouse to look | E to toggle dynamic LOD | ESC to quit",
            True,
            (255, 255, 255), (0, 0, 0, 0)
        )
        textInstructionsData = pygame.image.tostring(textInstructions, "RGBA", True)

        print("Starting viewer loop. Press ESC to quit.")

        frames = 0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    do_quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        do_quit()
                        return

            cur_time = time()
            self.delta = cur_time - self.last_time
            self.last_time = cur_time

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self._handle_inputs()

            for mesh in self.meshes:
                if self.dynamicLOD:
                    mesh.step_graph_cut()
                mesh.update()

            # A stats display, updated every second
            if cur_time > self.next_stats_time:
                self.next_stats_time = cur_time + STATS_DELAY
                triangles = sum([m.cluster_mesh.num_vertices // 9 for m in self.meshes])
                triangles = round(triangles / 1000000, 3)

                fps = 1 / self.delta
                msg = f"Dynamic LOD: {self.dynamicLOD} | FPS: {round(fps, 1)} | Triangles: {triangles} M"
                textSurface = self.font.render(
                    msg, True, (255, 255, 255, 255), (0, 0, 0, 0)
                )
                textData = pygame.image.tostring(textSurface, "RGBA", True)

            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0.0, self.display_dim[0], self.display_dim[1], 0.0, -1.0, 1.0)

            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()

            glRasterPos2i(self.display_dim[0] - 350, 20)
            glDrawPixels(
                textSurface.get_width(),
                textSurface.get_height(),
                GL_RGBA,
                GL_UNSIGNED_BYTE,
                textData,
            )

            glRasterPos2i(5, 20)
            glDrawPixels(
                textInstructions.get_width(),
                textInstructions.get_height(),
                GL_RGBA,
                GL_UNSIGNED_BYTE,
                textInstructionsData,
            )

            glPopMatrix()
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)

            pygame.display.flip()
            pygame.time.delay(1000 // 120)  # Limit 120 FPS
            frames += 1

    def _handle_inputs(self):
        keypress = pygame.key.get_pressed()
        mouse_move = pygame.mouse.get_rel()

        # Update the camera position based on keypress and mouse
        movement_speed = 2.0 * self.delta
        if keypress[pygame.K_LSHIFT]:
            movement_speed *= 8

        forward = self.camera._get_forward_vector()
        right = np.cross(forward, [0, 1, 0])
        dmove = np.array([0, 0, 0], dtype=np.float32)
        if keypress[pygame.K_w]:
            dmove += forward * movement_speed
        if keypress[pygame.K_s]:
            dmove -= forward * movement_speed
        if keypress[pygame.K_a]:
            dmove -= right * movement_speed
        if keypress[pygame.K_d]:
            dmove += right * movement_speed

        dmouse = np.maximum(np.minimum(mouse_move, 80), -80) * self.delta
        dmouse[0] *= 0.05
        dmouse[1] *= 0.035

        self.camera.update(dmove, dmouse)

        # On keypress e toggle dynamic LOD
        if keypress[pygame.K_e] and not self.prevKeyState[pygame.K_e]:
            self.dynamicLOD = not self.dynamicLOD

        # Save screenshot on keypress p
        if keypress[pygame.K_p] and not self.prevKeyState[pygame.K_p]:
            width, height = pygame.display.get_surface().get_size()
            glReadBuffer(GL_FRONT)
            pixels = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
            image = pygame.image.fromstring(pixels, (width, height), "RGB")
            image = pygame.transform.flip(
                image, False, True
            )  # Flip the image vertically
            pygame.image.save(image, f"screenshots/{int(time())}.png")

        self.prevKeyState = keypress