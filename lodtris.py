import os

# Set the METIS_DLL environment variable to the current path
current_path = os.path.abspath(os.path.dirname(__file__))
os.environ["METIS_DLL"] = os.path.join(current_path, "libmetis.so")
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"


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
}

if __name__ == "__main__":
    viewer = LODTrisViewer(MODELS, force_mesh_build=False)
    for z in range(5):
        for x in range(10):
            viewer.create_mesh_from_model("cat", (x * 5, 0, z * 5))

    viewer.run()
