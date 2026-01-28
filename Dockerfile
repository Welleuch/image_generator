# Dockerfile for GPU Endpoint
FROM runpod/base:0.4.0-cuda11.8

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    python3-pip \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt /workspace/requirements.txt

# Install Python packages
RUN pip install --no-cache-dir -r /workspace/requirements.txt

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI

# Install ComfyUI requirements
WORKDIR /workspace/ComfyUI
RUN pip install --no-cache-dir -r requirements.txt

# Install GGUF custom nodes
RUN git clone https://github.com/ssitu/ComfyUI_gguf /workspace/ComfyUI/custom_nodes/ComfyUI_gguf
WORKDIR /workspace/ComfyUI/custom_nodes/ComfyUI_gguf
RUN pip install -r requirements.txt

# Copy application files
WORKDIR /workspace
COPY handler.py /workspace/
COPY workflow_api.py /workspace/

# Create directories
RUN mkdir -p /workspace/ComfyUI/models/checkpoints
RUN mkdir -p /workspace/ComfyUI/models/clip
RUN mkdir -p /workspace/ComfyUI/models/vae
RUN mkdir -p /workspace/ComfyUI/output

# Symlink volume for models
RUN ln -sf /runpod-volume/z-image-turbo-Q8_0.gguf /workspace/ComfyUI/models/checkpoints/
RUN ln -sf /runpod-volume/Qwen3-4B-Q4_K_M.gguf /workspace/ComfyUI/models/clip/
RUN ln -sf /runpod-volume/ae.safetensors /workspace/ComfyUI/models/vae/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/workspace/cache

# Expose port for ComfyUI
EXPOSE 8188

# Start handler
CMD ["python", "-u", "handler.py"]