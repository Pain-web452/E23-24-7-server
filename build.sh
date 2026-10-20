#!/usr/bin/env bash
# exit on error
set -o errexit

# Simple packnstall karna bina kisi download ke
pip install --upgrade pip
pip install -r requirements.txt

echo "Build finished smoothly!"
