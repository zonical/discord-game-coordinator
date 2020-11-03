#!/bin/bash
echo "Checking python3 install."
sudo apt-get install python3-dev libffi-dev libssl-dev
echo "Checking libraries for updates..."
pip3 install -r "./requirements.txt"