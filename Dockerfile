FROM runpod/worker-comfyui:5.7.1-base

# Copy config and the workflow file into the image
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json
COPY handler.py /handler.py
COPY requirements.txt /requirements.txt

# Force install requirements into the system path to ensure the worker sees them
RUN pip install --upgrade pip && pip install -r /requirements.txt

ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml

# Create symlinks and start - SIMPLIFIED VERSION
CMD ["sh", "-c", "\
  echo '🚀 Starting image generation endpoint...' && \
  echo 'Checking network volume...' && \
  ls -la /runpod-volume/ 2>/dev/null || echo 'Volume not mounted yet' && \
  \
  # Start ComfyUI in background \
  echo 'Starting ComfyUI...' && \
  cd /comfyui && \
  python main.py --listen 127.0.0.1 --port 8188 & \
  \
  # Wait a bit then symlink custom nodes \
  echo 'Waiting for volume...' && \
  sleep 10 && \
  \
  if [ -d /runpod-volume/custom_nodes/ComfyUI-GGUF ]; then \
    echo 'Found GGUF nodes, creating symlink...' && \
    mkdir -p /comfyui/custom_nodes && \
    ln -sf /runpod-volume/custom_nodes/ComfyUI-GGUF /comfyui/custom_nodes/ComfyUI-GGUF && \
    echo 'GGUF symlink created'; \
  else \
    echo 'GGUF nodes not found, checking volume contents:' && \
    ls -la /runpod-volume/ 2>/dev/null || echo 'Cannot list volume'; \
  fi && \
  \
  # Wait for ComfyUI to start \
  echo 'Waiting for ComfyUI to start...' && \
  sleep 60 && \
  \
  # Start handler \
  echo 'Starting handler...' && \
  python -u /handler.py \
"]