# LODtris

Simplified implementation of automatic level of detail for meshes (wannabe Nanite tesselation) in Python. This is just an experiment and is missing many features to be useful in a real-world scenario.

## Background

I attempted to do this relatively clean without looking at any other implementation. The main source was the following video:

[https://www.youtube.com/watch?v=eviSykqSUUw](https://www.youtube.com/watch?v=eviSykqSUUw)


## Features



## Installation / Usage

Note:
    This setup is only tested on Ubuntu 24.04.1. The trickiest thing will be METIS.

```sh
# Clone the repo
git clone https://github.com/yourusername/LODtris.git
cd LODtris

# Setup venv
python -m venv venv
source venv/bin/activate

# Install py dependencies
pip install -r requirements.txt

# Download and build METIS
./setup_metis.sh

# Run the app
python lodtris.py
```

## License

MIT