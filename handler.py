# handler.py - GPU Endpoint Main Handler
import runpod
from workflow_api import ComfyUIAPI
import os
import time

print("=" * 60)
print("🚀 COMFYUI IMAGE GENERATION ENDPOINT")
print("=" * 60)

# Initialize ComfyUI API
comfy = None

def start_comfyui():
    """Start ComfyUI server in background"""
    import subprocess
    import threading
    
    def run_comfyui():
        subprocess.run([
            "python", "/workspace/ComfyUI/main.py",
            "--listen", "0.0.0.0",
            "--port", "8188"
        ])
    
    # Start in background thread
    thread = threading.Thread(target=run_comfyui, daemon=True)
    thread.start()
    
    # Wait for server to start
    time.sleep(10)
    print("✅ ComfyUI server started")

def handler(job):
    """Main handler function"""
    print(f"\n🎯 Received image generation job")
    
    try:
        input_data = job["input"]
        prompt = input_data.get("prompt", "").strip()
        
        if not prompt:
            return {"error": "No prompt provided"}
        
        print(f"📝 Prompt: {prompt[:100]}...")
        
        # Generate image
        start_time = time.time()
        result = comfy.generate_image(prompt)
        generation_time = time.time() - start_time
        
        print(f"✅ Image generated in {generation_time:.2f} seconds")
        
        return {
            "status": "success",
            "image_base64": result["image_base64"],
            "generation_time": f"{generation_time:.2f}s",
            "dimensions": result["dimensions"]
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# Start ComfyUI server on init
print("🔧 Starting ComfyUI server...")
start_comfyui()

# Initialize API client
comfy = ComfyUIAPI("127.0.0.1:8188")

print("\n🏁 GPU Endpoint Ready!")
print("Waiting for image generation requests...")

runpod.serverless.start({"handler": handler})