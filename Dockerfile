# Dockerfile - Based on their template
FROM runpod/base:0.4.0

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

# Clone RunPod's ComfyUI worker
RUN git clone https://github.com/runpod-workers/worker-comfyui.git /workspace/comfyui-worker
WORKDIR /workspace/comfyui-worker

# Install requirements from their template
RUN pip install --no-cache-dir -r requirements.txt

# Copy our custom files
COPY handler.py /workspace/
COPY comfy_api.py /workspace/
COPY start.sh /workspace/

# Install our requirements
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for models
RUN mkdir -p /workspace/models

# Set environment
ENV PYTHONUNBUFFERED=1

# Start script
RUN chmod +x /workspace/start.sh
CMD ["/workspace/start.sh"]