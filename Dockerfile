FROM runpod/worker-comfyui:5.7.1-base

# Copy config and the workflow file into the image
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json
COPY handler.py /handler.py
COPY requirements.txt /requirements.txt

# Force install requirements into the system path to ensure the worker sees them
RUN pip install --upgrade pip && pip install -r /requirements.txt

ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml

# Create symlinks and start
CMD ["sh", "-c", "\
  # Wait for volume to mount first \
  echo '⏳ Waiting for network volume to mount...' && \
  while [ ! -d /runpod-volume/custom_nodes ]; do \
    echo 'Volume not ready, waiting...' && \
    sleep 5; \
  done && \
  \
  # Create symlinks to custom nodes from NV BEFORE starting ComfyUI \
  echo '🔗 Creating symlinks to custom nodes from NV...' && \
  mkdir -p /comfyui/custom_nodes && \
  \
  # GGUF nodes \
  if [ -d /runpod-volume/custom_nodes/ComfyUI-GGUF ]; then \
    echo 'Symlinking GGUF nodes...' && \
    ln -sf /runpod-volume/custom_nodes/ComfyUI-GGUF /comfyui/custom_nodes/ComfyUI-GGUF; \
    # Install GGUF dependencies if requirements.txt exists \
    if [ -f /runpod-volume/custom_nodes/ComfyUI-GGUF/requirements.txt ]; then \
      echo 'Installing GGUF dependencies...' && \
      pip install -r /runpod-volume/custom_nodes/ComfyUI-GGUF/requirements.txt; \
    fi; \
  else \
    echo '❌ WARNING: GGUF nodes not found on volume at /runpod-volume/custom_nodes/ComfyUI-GGUF'; \
    echo 'Contents of /runpod-volume/custom_nodes:' && \
    ls -la /runpod-volume/custom_nodes/ 2>/dev/null || echo 'Directory not found'; \
  fi && \
  \
  # Also check for other custom nodes you might have \
  if [ -d /runpod-volume/custom_nodes/comfyui-rmbg ]; then \
    echo 'Symlinking RmBG nodes...' && \
    ln -sf /runpod-volume/custom_nodes/comfyui-rmbg /comfyui/custom_nodes/comfyui-rmbg; \
  fi && \
  \
  # Warm-up: pre-start ComfyUI \
  echo '🚀 Starting ComfyUI...' && \
  cd /comfyui && \
  python main.py --listen 127.0.0.1 --port 8188 & \
  \
  # Wait longer for ComfyUI to start and load custom nodes \
  echo '⏳ Waiting for ComfyUI to fully start (loading custom nodes)...' && \
  sleep 90 && \
  \
  # Verify ComfyUI is ready and can list nodes \
  echo '✅ Checking if ComfyUI is ready...' && \
  curl -f http://127.0.0.1:8188/system_stats >/dev/null 2>&1 && \
  echo '✅ ComfyUI is ready!' || echo '❌ ComfyUI failed to start' && \
  \
  # Start handler \
  echo '🏁 Starting handler...' && \
  python -u /handler.py \
"]