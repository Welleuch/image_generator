FROM runpod/worker-comfyui:5.7.1-base

# Copy ONLY essential files
COPY handler.py /handler.py
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

# Use a tiny requirements.txt with only what's needed
RUN echo "runpod\nrequests\nboto3" > /requirements.txt

# Install minimal requirements
RUN pip install --no-cache-dir -r /requirements.txt

ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml

# Simple start command
CMD ["sh", "-c", "\
  # Symlink GGUF nodes from NV if they exist \
  if [ -d /runpod-volume/custom_nodes/ComfyUI-GGUF ]; then \
    echo 'Symlinking GGUF nodes from NV...' && \
    mkdir -p /comfyui/custom_nodes && \
    ln -sf /runpod-volume/custom_nodes/ComfyUI-GGUF /comfyui/custom_nodes/ComfyUI-GGUF; \
  fi && \
  \
  # Start ComfyUI \
  cd /comfyui && python main.py --listen 127.0.0.1 --port 8188 & \
  \
  # Wait for startup \
  sleep 45 && \
  \
  # Start handler \
  python -u /handler.py \
"]