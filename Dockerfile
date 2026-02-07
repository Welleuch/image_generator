# We move to 2.4.0 to fix the uint64 error
FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Absolute path definition - THE single source of truth
ENV WORKFLOW_PATH=/etc/comfy_workflow.json

RUN apt-get update && apt-get install -y git libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender1 && apt-get clean

RUN git clone https://github.com/Comfy-Org/ComfyUI /comfyui
WORKDIR /comfyui

RUN cd custom_nodes && git clone https://github.com/city96/ComfyUI-GGUF.git

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod requests boto3 gguf

# Copy to the EXACT path defined above
COPY workflow_api.json ${WORKFLOW_PATH}
COPY handler.py /handler.py
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

# Launch
CMD ["sh", "-c", "cd /comfyui && python main.py --listen 0.0.0.0 --port 8188 --highvram > /comfyui_logs.txt 2>&1 & python -u /handler.py"]