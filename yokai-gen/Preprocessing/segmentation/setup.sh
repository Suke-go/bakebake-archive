#!/bin/bash

# Create directories
mkdir -p inputs outputs processed checkpoints

# Clone Grounded-Segment-Anything if not exists
if [ ! -d "Grounded-Segment-Anything" ]; then
    echo "Cloning Grounded-Segment-Anything..."
    git clone https://github.com/IDEA-Research/Grounded-Segment-Anything.git
fi

# Instructions for weights
echo "Downloading weights..."
cd checkpoints
if [ ! -f "groundingdino_swint_ogc.pth" ]; then
    wget https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
fi
if [ ! -f "sam_vit_h_4b8939.pth" ]; then
    wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth
fi
cd ..

echo "Setup complete."
echo "Please ensure you have installed the requirements for Grounded-Segment-Anything."
echo "Typically:"
echo "pip install -r Grounded-Segment-Anything/requirements.txt"
echo "pip install gradio"

