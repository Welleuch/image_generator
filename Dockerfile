FROM runpod/worker-comfyui:5.7.1-base

# Copy our configuration files
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
COPY handler.py /handler.py

# Set the path config environment variable
ENV COMFYUI_PATH_CONFIG=/comfyui/extra_model_paths.yaml

# The Start Command will create symlinks before starting the handler
# This connects the custom_nodes from your Volume to the internal ComfyUI
CMD sh -c "ln -s /runpod-volume/custom_nodes/* /comfyui/custom_nodes/ && python -u /handler.py"