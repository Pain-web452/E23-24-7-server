#!/usr/bin/env bash
# exit on error
set -o errexit

PROJECT_ROOT=$(pwd)

# Dependencies install karein
pip install -r requirements.txt

STORAGE_DIR=/opt/render/project/.render
mkdir -p $STORAGE_DIR/chrome
mkdir -p $STORAGE_DIR/chromedriver

# 1. GOOGLE CHROME INSTALLATION WITH CACHE BYPASS
echo "...Downloading Stable Linux Google Chrome"
cd $STORAGE_DIR/chrome

# Agar koi purani corrupt file padi ho toh use delete karna
rm -f google-chrome-stable_current_amd64.deb index.html

# Direct original static mirror URL framework integration
wget --no-cache -O google-chrome-stable_current_amd64.deb https://google.com

dpkg -x google-chrome-stable_current_amd64.deb .
rm -f google-chrome-stable_current_amd64.deb
cd $PROJECT_ROOT

# 2. CHROMEDRIVER INSTALLATION
echo "...Downloading Chromedriver Stable Version"
cd $STORAGE_DIR/chromedriver

rm -rf chromedriver-linux64 chromedriver-linux64.zip chromedriver

wget --no-cache https://googleapis.com
unzip chromedriver-linux64.zip
mv chromedriver-linux64/chromedriver .
rm -rf chromedriver-linux64 chromedriver-linux64.zip
cd $PROJECT_ROOT

echo "Build Script Finished Successfully!"
