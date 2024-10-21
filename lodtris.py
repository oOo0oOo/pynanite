from LODtris.lod_viewer import LODTrisViewer


MODELS = {
    "cat": [
        "data/Cat.obj/Cat.obj",
        "data/Cat.obj/Cat.jpg",
        "data/build/Cat.pickle",
    ],
    # "flower": [
    #     "data/Flower.obj/Flower.obj",
    #     "data/Flower.obj/Flower_0.jpg",
    #     "data/build/Flower.pickle"
    # ]
}

if __name__ == "__main__":
    viewer = LODTrisViewer(MODELS)
    for z in range(5):
        for x in range(10):
            viewer.create_mesh_from_model("cat", (x * 5, 0, z * 5))

    viewer.run()
