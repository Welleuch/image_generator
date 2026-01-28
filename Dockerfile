FROM runpod/worker-comfyui:5.7.1-base

COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json
COPY handler.py /handler.py

ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml

# 1. Create necessary folders
# 2. Link your custom nodes
# 3. Start ComfyUI in the background (&)
# 4. Start the handler
CMD sh -c "mkdir -p /runpod-volume/output && ln -s /runpod-volume/custom_nodes/* /comfyui/custom_nodes/ && python /comfyui/main.py --listen 127.0.0.1 --port 8188 & python -u /handler.py"