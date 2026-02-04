FROM runpod/worker-comfyui:5.7.1-base

# Copy ALL necessary files
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json
COPY handler.py /handler.py
COPY requirements.txt /requirements.txt

# Install requirements including gguf
RUN pip install --upgrade pip && pip install -r /requirements.txt

# Install gguf package for GGUF nodes
RUN pip install gguf

ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml

# Start command
CMD ["sh", "-c", "\
  # Symlink GGUF nodes from NV if they exist \
  echo 'Setting up custom nodes...' && \
  if [ -d /runpod-volume/custom_nodes/ComfyUI-GGUF ]; then \
    echo 'Symlinking GGUF nodes from NV...' && \
    mkdir -p /comfyui/custom_nodes && \
    ln -sf /runpod-volume/custom_nodes/ComfyUI-GGUF /comfyui/custom_nodes/ComfyUI-GGUF; \
  fi && \
  \
  # Start ComfyUI \
  echo 'Starting ComfyUI...' && \
  cd /comfyui && python main.py --listen 127.0.0.1 --port 8188 & \
  \
  # Wait for startup \
  echo 'Waiting for ComfyUI to start (45s)...' && \
  sleep 45 && \
  \
  # Start handler \
  echo 'Starting handler...' && \
  python -u /handler.py \
"]