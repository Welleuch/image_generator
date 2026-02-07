#!/bin/bash

# 1. Start ComfyUI in the background
# We use the path established in your Dockerfile WORKDIR
cd /comfyui
python main.py --listen 0.0.0.0 --port 8188 --highvram > /comfyui_logs.txt 2>&1 &

# 2. Wait for ComfyUI to be ready (Solid Solution)
echo "Waiting for ComfyUI to start on port 8188..."
until curl -s http://127.0.0.1:8188/history > /dev/null; do
  echo "ComfyUI is still loading models... retrying in 2s"
  sleep 2
done

echo "✅ ComfyUI is READY. Starting RunPod Handler..."

# 3. Start the RunPod handler
# The handler is copied to the root (/) in your Dockerfile
python -u /handler.py