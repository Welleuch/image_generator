#!/bin/bash
# start.sh

# Start ComfyUI in background
cd /workspace/ComfyUI
python3 main.py --listen 0.0.0.0 --port 8188 &

# Wait for server to start
sleep 10

# Start RunPod handler
cd /workspace
python3 handler.py