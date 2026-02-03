"""
Z-Image RunPod Serverless Handler - UPDATED FOR WORKER
"""

import os
import runpod
import torch
import base64
import time
from io import BytesIO
from diffusers import ZImagePipeline

# Global pipeline
pipe = None

def log(msg):
    print(msg, flush=True)

def init_model():
    global pipe
    log("--- 🚀 Z-Image Startup ---")
    
    try:
        t0 = time.time()
        log("📥 Loading Z-Image Pipeline...")
        
        pipe = ZImagePipeline.from_pretrained(
            "Tongyi-MAI/Z-Image-Turbo",
            torch_dtype=torch.bfloat16,
            use_safetensors=True,
            cache_dir="/runpod-volume/models",
            device_map="auto"
        )
        
        pipe.enable_attention_slicing()
        log(f"✨ READY IN {time.time()-t0:.1f}s")

    except Exception as e:
        log(f"❌ LOAD ERROR: {e}")
        import traceback
        traceback.print_exc()

def handler(job):
    try:
        job_input = job.get("input", {})
        req_type = job_input.get("type", "GEN_IMAGE")
        
        if pipe is None: 
            return {"error": "Pipeline not initialized"}
        
        prompt = job_input.get("visual_prompt") or job_input.get("prompt", "")
        seed = job_input.get("seed", 42)
        width = job_input.get("width", 1024)
        height = job_input.get("height", 1024)
        
        log(f"🎨 Generating: {prompt[:50]}...")
        
        result = pipe(
            prompt=prompt, 
            width=width, 
            height=height,
            num_inference_steps=9, 
            guidance_scale=0.0,
            generator=torch.Generator("cpu").manual_seed(seed)
        )
        
        # Convert to base64
        buffer = BytesIO()
        result.images[0].save(buffer, format="JPEG", quality=85)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        log("✅ Image generated successfully")
        
        # Return in the format Worker expects
        return {
            "image_base64": image_base64,
            "prompt": prompt,
            "width": width,
            "height": height,
            "seed": seed
        }
            
    except Exception as e:
        log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

init_model()
runpod.serverless.start({"handler": handler})