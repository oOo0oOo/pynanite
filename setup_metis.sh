#!/bin/bash

set -e
mkdir tmp
cd tmp

# Download and extract METIS 5.1.0
echo "Downloading METIS 5.1.0..."
wget http://web.archive.org/web/20170712055800/http://glaros.dtc.umn.edu/gkhome/fetch/sw/metis/metis-5.1.0.tar.gz
tar -xzf metis-5.1.0.tar.gz
cd metis-5.1.0

# Build METIS
echo "Building METIS..."
make config shared=1
make

# Find and copy the METIS shared library to the root directory
echo "Finding and copying METIS shared library..."
LIBMETIS_PATH=$(find . -name "libmetis.so" | head -n 1)
if [ -z "$LIBMETIS_PATH" ]; then
    echo "libmetis.so not found!"
    exit 1
fi
cp "$LIBMETIS_PATH" ../../libmetis.so

# Clean up
echo "Cleaning up..."
cd ../..
rm -rf tmp

echo "METIS setup completed successfully!"