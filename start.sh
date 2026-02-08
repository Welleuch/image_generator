#!/bin/bash

# 1. Start ComfyUI in the background
# We don't redirect to a file anymore so you can see errors in RunPod logs
cd /comfyui
python main.py --listen 0.0.0.0 --port 8188 --highvram &

# 2. Wait for the port to open
echo "Waiting for ComfyUI to start on port 8188..."
while ! curl -s http://127.0.0.1:8188/history > /dev/null; do
  echo "Still waiting for ComfyUI API..."
  sleep 5
done

echo "✅ ComfyUI is READY."

# 3. Start the RunPod handler
# Make sure this path matches where you COPY it in your Dockerfile
echo "🚀 Starting RunPod Handler..."
python -u /handler.py