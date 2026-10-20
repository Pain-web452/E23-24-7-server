#!/usr/bin/env bash
# exit on error
set -o errexit

# Install python dependencies from requirements
pip install -r requirements.txt

# Dynamic container validation storage parameters path binding
STORAGE_DIR=/opt/render/project/.render

if [ ! -d "$STORAGE_DIR/chrome" ]; then
  echo "...Downloading Stable Linux Google Chrome Binary Instance"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget https://google.com
  dpkg -x google-chrome-stable_current_amd64.deb .
  rm google-chrome-stable_current_amd64.deb
  cd $HOME/project/src
else
  echo "...Using cached Chrome context data"
fi

if [ ! -d "$STORAGE_DIR/chromedriver" ]; then
  echo "...Downloading Chromedriver matching instance version"
  mkdir -p $STORAGE_DIR/chromedriver
  cd $STORAGE_DIR/chromedriver
  wget https://googleapis.com
  unzip chromedriver-linux64.zip
  mv chromedriver-linux64/chromedriver .
  rm -r chromedriver-linux64 chromedriver-linux64.zip
  cd $HOME/project/src
else
  echo "...Using cached Chromedriver reference maps"
fi
