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
# Added 'pip install gguf' right at the start as a safety measure
CMD ["sh", "-c", "\
  # Warm-up: pre-start ComfyUI \
  echo '🚀 Pre-warming ComfyUI...' && \
  cd /comfyui && \
  python main.py --listen 127.0.0.1 --port 8188 & \
  \
  # Wait for ComfyUI to start \
  echo '⏳ Waiting for ComfyUI to start...' && \
  sleep 30 && \
  \
  # Start handler \
  echo '🏁 Starting handler...' && \
  python -u /handler.py \
"]