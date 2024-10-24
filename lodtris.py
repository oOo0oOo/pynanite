import os
from LODtris.lod_viewer import LODTrisViewer

# Example model: Cat (Thanks to Alex Meier!)
if not os.path.exists("data/cat"):
    import zipfile
    with zipfile.ZipFile("data/cat.zip", "r") as zip_ref:
        zip_ref.extractall("data")


MODELS = {
    "cat": [
        "data/cat/cat.obj",
        "data/cat/cat.jpg",
        "data/build/cat.pickle",
    ],
    # "flower": [
    #     "data/Flower.obj/Flower.obj",
    #     "data/Flower.obj/Flower_0.jpg",
    #     "data/build/flower.pickle",
    # ],
}


if __name__ == "__main__":
    viewer = LODTrisViewer(
        MODELS,
        # force_mesh_build=True,
        # profile_meshing=True,
        cluster_size_initial=160,
        cluster_size=128,
        group_size=8
    )

    for z in range(5):
        for x in range(10):
            viewer.create_mesh_from_model("cat", (x * 5, 0, z * 5))
    
    viewer.run()
