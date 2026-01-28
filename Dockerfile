# Dockerfile - ComfyUI on RunPod
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-dev \
    git \
    wget \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Create workspace
WORKDIR /workspace

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git

# Install ComfyUI requirements
WORKDIR /workspace/ComfyUI
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
RUN pip3 install --no-cache-dir -r requirements.txt

# Install ComfyUI GGUF nodes
RUN git clone https://github.com/ssitu/ComfyUI_gguf custom_nodes/ComfyUI_gguf
WORKDIR /workspace/ComfyUI/custom_nodes/ComfyUI_gguf
RUN pip3 install -r requirements.txt

# Copy our handler
WORKDIR /workspace
COPY handler.py .
COPY comfy_api.py .

# Create model directories
RUN mkdir -p /workspace/ComfyUI/models/checkpoints
RUN mkdir -p /workspace/ComfyUI/models/clip
RUN mkdir -p /workspace/ComfyUI/models/vae
RUN mkdir -p /workspace/ComfyUI/models/unet
RUN mkdir -p /workspace/ComfyUI/output

# Create symlinks to volume models
RUN ln -sf /runpod-volume/z-image-turbo-Q8_0.gguf /workspace/ComfyUI/models/unet/
RUN ln -sf /runpod-volume/Qwen3-4B-Q4_K_M.gguf /workspace/ComfyUI/models/clip/
RUN ln -sf /runpod-volume/ae.safetensors /workspace/ComfyUI/models/vae/

# Set environment
ENV PYTHONUNBUFFERED=1

# Expose ComfyUI port
EXPOSE 8188

# Start the server and handler
COPY start.sh /workspace/
RUN chmod +x /workspace/start.sh
CMD ["/workspace/start.sh"]