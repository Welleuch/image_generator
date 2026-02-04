FROM runpod/worker-comfyui:5.7.1-base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml

# Copy ONLY essential files (3 files total)
COPY handler.py /handler.py
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json

# Install requirements WITHOUT version pinning
RUN pip install --no-cache-dir runpod requests boto3 gguf

# Clean up to reduce image size
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/pip

# Optimized start command
CMD ["sh", "-c", "\
  # Setup GGUF nodes from NV \
  echo 'Setting up custom nodes...' && \
  if [ -d /runpod-volume/custom_nodes/ComfyUI-GGUF ]; then \
    mkdir -p /comfyui/custom_nodes && \
    ln -sf /runpod-volume/custom_nodes/ComfyUI-GGUF /comfyui/custom_nodes/ComfyUI-GGUF && \
    echo 'GGUF nodes symlinked'; \
  else \
    echo 'GGUF nodes not found on NV'; \
  fi && \
  \
  # Start ComfyUI \
  echo 'Starting ComfyUI...' && \
  cd /comfyui && \
  python main.py --listen 127.0.0.1 --port 8188 & \
  \
  # Wait for startup \
  echo 'Waiting for ComfyUI (30s)...' && \
  sleep 30 && \
  \
  # Start handler \
  echo 'Starting handler...' && \
  python -u /handler.py \
"]