FROM runpod/worker-comfyui:5.7.1-base

# Copy config and the workflow file into the image
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY workflow_api.json /comfyui/workflow_api.json
COPY handler.py /handler.py

# Set environment variables
ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml

# Create symlinks for nodes AND ensure the output goes to the volume
# We use --output-directory to force ComfyUI to write to your NV
CMD sh -c "mkdir -p /runpod-volume/output && ln -s /runpod-volume/custom_nodes/* /comfyui/custom_nodes/ && python -u /handler.py"