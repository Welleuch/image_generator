FROM runpod/worker-comfyui:5.7.1-base

# Set environment variables early
ENV PYTHONUNBUFFERED=1
ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml
ENV TORCH_FORCE_WEIGHTS_ONLY_LOAD=0

# Copy only essential files
COPY handler.py /handler.py
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json

# Create minimal requirements.txt on the fly
RUN echo "runpod==1.16.5\nrequests==2.31.0\nboto3==1.34.4\ngguf==0.6.0" > /requirements.txt

# Install requirements with cache cleanup
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /requirements.txt && \
    rm /requirements.txt

# Clean up to reduce image size
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/pip

# Optimized start command
CMD ["sh", "-c", "\
  # Setup GGUF nodes from NV \
  echo '🔧 Setting up custom nodes...' && \
  if [ -d /runpod-volume/custom_nodes/ComfyUI-GGUF ]; then \
    mkdir -p /comfyui/custom_nodes && \
    ln -sf /runpod-volume/custom_nodes/ComfyUI-GGUF /comfyui/custom_nodes/ComfyUI-GGUF && \
    echo '✅ GGUF nodes symlinked'; \
  else \
    echo '⚠️ GGUF nodes not found on NV'; \
    echo 'Contents of /runpod-volume/custom_nodes/:' && \
    ls -la /runpod-volume/custom_nodes/ 2>/dev/null || echo 'Directory not accessible'; \
  fi && \
  \
  # Start ComfyUI in background \
  echo '🚀 Starting ComfyUI...' && \
  cd /comfyui && \
  python main.py --listen 127.0.0.1 --port 8188 --disable-auto-launch & \
  \
  # Wait for ComfyUI to be ready \
  echo '⏳ Waiting for ComfyUI to start (40s)...' && \
  sleep 40 && \
  \
  # Verify ComfyUI is ready \
  echo '🔍 Checking if ComfyUI is ready...' && \
  for i in {1..10}; do \
    if curl -s http://127.0.0.1:8188/system_stats >/dev/null; then \
      echo '✅ ComfyUI is ready!'; \
      break; \
    fi; \
    if [ \$i -eq 10 ]; then \
      echo '❌ ComfyUI failed to start after 50s'; \
      exit 1; \
    fi; \
    echo 'Still waiting...'; \
    sleep 5; \
  done && \
  \
  # Start handler \
  echo '🏁 Starting handler...' && \
  python -u /handler.py \
"]