#!/bin/bash

# UNUSED!
# This script is required if you want to use the metis python package
# import metis (this package is not maintained anymore)
# Since we switched to pymetis (actively maintained) this is luckily not required anymore.

set -e

# If temp directory exists, remove it
if [ -d tmp ]; then
    rm -rf tmp
fi
mkdir tmp
cd tmp

# Unfortunately the python bindings are not updated for the newer versions of METIS
# # Clone
# echo "Cloning GKlib and METIS..."
# git clone https://github.com/KarypisLab/GKlib.git
# git clone https://github.com/KarypisLab/METIS.git

# # Build GKlib
# cd GKlib
# make config prefix=$(pwd)
# make install
# cd ..
# cd METIS
# make config shared=1 prefix=$(pwd) gklib_path=../GKlib
# make install

# Download and extract METIS 5.1.0 (sorry internet archive :/ )
echo "Downloading METIS 5.1.0..."
wget http://web.archive.org/web/20170712055800/http://glaros.dtc.umn.edu/gkhome/fetch/sw/metis/metis-5.1.0.tar.gz
tar -xzf metis-5.1.0.tar.gz
cd metis-5.1.0
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