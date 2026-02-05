
FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Installiere ALLES Notwendige für OpenCV und Grafik-Nodes
RUN apt-get update && apt-get install -y \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && apt-get clean

RUN git clone https://github.com/Comfy-Org/ComfyUI /comfyui
WORKDIR /comfyui

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod requests boto3 gguf xformers==0.0.24

COPY handler.py /handler.py
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json

# WICHTIG: Leite ComfyUI Logs in eine Datei um, damit wir sie debuggen können
CMD ["sh", "-c", "cd /comfyui && python main.py --listen 127.0.0.1 --port 8188 --use-xformers > /comfyui_logs.txt 2>&1 & python -u /handler.py"]
