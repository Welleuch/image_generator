FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

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

# INSTALL GGUF NODES - This is why your workflow was failing to load nodes
RUN cd custom_nodes && git clone https://github.com/city96/ComfyUI-GGUF.git

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod requests boto3 gguf

COPY handler.py /handler.py
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json

# REMOVED --use-xformers because it causes the crash
# Added --highvram to ensure Flux models load properly
CMD ["sh", "-c", "cd /comfyui && python main.py --listen 0.0.0.0 --port 8188 --highvram > /comfyui_logs.txt 2>&1 & python -u /handler.py"]