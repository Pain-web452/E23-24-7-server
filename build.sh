#!/usr/bin/env bash
# exit on error
set -o errexit

# Simple packages install karna bina kisi download ke
pip install --upgrade pip
pip install -r requirements.txt

echo "Build finished smoothly!"
