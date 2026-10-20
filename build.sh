#!/usr/bin/env bash
# exit on error
set -o errexit

# Project ke core directory path ko secure karna
PROJECT_ROOT=$(pwd)

# Python dependencies install karein
pip install -r requirements.txt

# Chrome aur Chromedriver install karne ka sahi path
STORAGE_DIR=/opt/render/project/.render

if [ ! -d "$STORAGE_DIR/chrome" ]; then
  echo "...Downloading Google Chrome Stable Binary"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -O google-chrome-stable_current_amd64.deb https://google.com
  dpkg -x google-chrome-stable_current_amd64.deb .
  rm google-chrome-stable_current_amd64.deb
  cd $PROJECT_ROOT
else
  echo "...Using cached Chrome context"
fi

if [ ! -d "$STORAGE_DIR/chromedriver" ]; then
  echo "...Downloading Chromedriver Stable Version"
  mkdir -p $STORAGE_DIR/chromedriver
  cd $STORAGE_DIR/chromedriver
  wget https://googleapis.com
  unzip chromedriver-linux64.zip
  mv chromedriver-linux64/chromedriver .
  rm -r chromedriver-linux64 chromedriver-linux64.zip
  cd $PROJECT_ROOT
else
  echo "...Using cached Chromedriver maps"
fi
