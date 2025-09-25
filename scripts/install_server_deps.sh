#!/bin/sh
# Install minimal Python packages needed for analysis into the user site
PYTHON=/usr/bin/python3
if [ ! -x "$PYTHON" ]; then
  echo "python3 not found at $PYTHON"
  exit 1
fi
$PYTHON -m pip install --upgrade pip setuptools wheel --user
$PYTHON -m pip install --user --no-cache-dir praat-parselmouth numpy scipy soundfile librosa
echo INSTALLED
