# 1. Schlankeres Basis-Image (~4.5 GB statt 10.8 GB)
FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml

# System-Abhängigkeiten
RUN apt-get update && apt-get install -y git libgl1 libglib2.0-0 && apt-get clean

# 2. ComfyUI Core direkt installieren (URL korrigiert)
RUN git clone https://github.com /comfyui
WORKDIR /comfyui
RUN pip install --no-cache-dir -r requirements.txt

# 3. Deine Anforderungen
RUN pip install --no-cache-dir runpod requests boto3 gguf

# 4. Dateien kopieren
COPY handler.py /handler.py
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json

# 5. Start-Skript (Alles in einem CMD-Block)
CMD ["sh", "-c", "\
  echo 'Setting up custom nodes...' && \
  if [ -d /runpod-volume/custom_nodes/ComfyUI-GGUF ]; then \
    mkdir -p /comfyui/custom_nodes && \
    ln -sf /runpod-volume/custom_nodes/ComfyUI-GGUF /comfyui/custom_nodes/ComfyUI-GGUF && \
    echo 'GGUF nodes symlinked'; \
  else \
    echo 'GGUF nodes not found on NV'; \
  fi && \
  \
  echo 'Starting ComfyUI...' && \
  cd /comfyui && \
  python main.py --listen 127.0.0.1 --port 8188 & \
  \
  echo 'Waiting for ComfyUI (30s)...' && \
  sleep 30 && \
  \
  echo 'Starting handler...' && \
  python -u /handler.py \
"]
