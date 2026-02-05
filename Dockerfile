# 1. Basis-Image (Vorteil: Wird lokal nach dem ersten Mal gecacht)
FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml

# System-Abhängigkeiten
RUN apt-get update && apt-get install -y git libgl1 libglib2.0-0 && apt-get clean

# 2. ComfyUI Core - AKTUALISIERTE URL
RUN git clone https://github.com/Comfy-Org/ComfyUI /comfyui
WORKDIR /comfyui

# 3. Installation der Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod requests boto3 gguf xformers==0.0.24

# 4. Dateien aus Ihrem lokalen Ordner in das Image kopieren
COPY handler.py /handler.py
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json

# 5. Start-Befehl
CMD ["sh", "-c", "\
  cd /comfyui && \
  python main.py --listen 127.0.0.1 --port 8188 --use-xformers & \
  sleep 30 && \
  python -u /handler.py \
"]
