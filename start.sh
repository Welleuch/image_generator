#!/bin/bash
# start.sh

# Start ComfyUI server (using RunPod's setup)
cd /workspace/comfyui-worker
python main.py &

# Wait for server to start
sleep 15

# Start our handler
cd /workspace
python handler.py