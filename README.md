# LODtris

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