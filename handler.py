# handler.py - Using RunPod's ComfyUI setup
import runpod
import requests
import time
import base64
import io
from PIL import Image
import os

print("=" * 60)
print("🚀 COMFYUI IMAGE GENERATION (RunPod Template)")
print("=" * 60)

# ComfyUI server address (from RunPod template)
COMFYUI_SERVER = "127.0.0.1:8188"
MODELS_DIR = "/workspace/models"

def ensure_models_exist():
    """Check if required models are available"""
    required_models = {
        "checkpoints/z-image-turbo-Q8_0.gguf": "/runpod-volume/z-image-turbo-Q8_0.gguf",
        "clip/Qwen3-4B-Q4_K_M.gguf": "/runpod-volume/Qwen3-4B-Q4_K_M.gguf",
        "vae/ae.safetensors": "/runpod-volume/ae.safetensors"
    }
    
    for model_path, volume_path in required_models.items():
        dest_path = f"{MODELS_DIR}/{model_path}"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # Create symlink if model exists in volume
        if os.path.exists(volume_path) and not os.path.exists(dest_path):
            try:
                os.symlink(volume_path, dest_path)
                print(f"✅ Linked {model_path}")
            except Exception as e:
                print(f"⚠️  Could not link {model_path}: {e}")

def load_workflow_template(prompt):
    """Create workflow using your exact nodes"""
    # This should match your local workflow
    workflow = {
        "prompt": {
            "3": {
                "inputs": {
                    "seed": int(time.time()),
                    "steps": 8,
                    "cfg": 1,
                    "sampler_name": "res_multistep",
                    "scheduler": "simple",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {
                    "unet_name": "z-image-turbo-Q8_0.gguf"
                },
                "class_type": "UnetLoaderGGUF"
            },
            "5": {
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                },
                "class_type": "EmptySD3LatentImage"
            },
            "6": {
                "inputs": {
                    "text": prompt,
                    "clip": ["8", 0]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "conditioning": ["6", 0]
                },
                "class_type": "ConditioningZeroOut"
            },
            "8": {
                "inputs": {
                    "clip_name": "Qwen3-4B-Q4_K_M.gguf",
                    "type": "lumina2"
                },
                "class_type": "CLIPLoaderGGUF"
            },
            "9": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["10", 0]
                },
                "class_type": "VAEDecode"
            },
            "10": {
                "inputs": {
                    "vae_name": "ae.safetensors"
                },
                "class_type": "VAELoader"
            },
            "11": {
                "inputs": {
                    "filename_prefix": "ComfyUI/output",
                    "images": ["9", 0]
                },
                "class_type": "SaveImage"
            }
        }
    }
    return workflow

def generate_image(prompt):
    """Generate image using ComfyUI"""
    try:
        # Prepare workflow
        workflow = load_workflow_template(prompt)
        
        # Queue prompt
        response = requests.post(
            f"http://{COMFYUI_SERVER}/prompt",
            json=workflow
        )
        
        if response.status_code != 200:
            return {"error": f"Queue failed: {response.text}"}
        
        prompt_id = response.json()["prompt_id"]
        print(f"✅ Queued: {prompt_id}")
        
        # Wait for completion
        return wait_for_result(prompt_id)
        
    except Exception as e:
        return {"error": f"Generation error: {str(e)}"}

def wait_for_result(prompt_id, timeout=60):
    """Wait for image to be generated"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check history
            response = requests.get(f"http://{COMFYUI_SERVER}/history")
            
            if response.status_code == 200:
                history = response.json()
                
                if prompt_id in history:
                    outputs = history[prompt_id]["outputs"]
                    
                    for node_id in outputs:
                        if "images" in outputs[node_id]:
                            image_info = outputs[node_id]["images"][0]
                            
                            # Download image
                            params = {
                                "filename": image_info["filename"],
                                "subfolder": image_info.get("subfolder", ""),
                                "type": image_info["type"]
                            }
                            
                            img_response = requests.get(
                                f"http://{COMFYUI_SERVER}/view",
                                params=params
                            )
                            
                            if img_response.status_code == 200:
                                # Convert to base64
                                img = Image.open(io.BytesIO(img_response.content))
                                buffered = io.BytesIO()
                                img.save(buffered, format="PNG")
                                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                                
                                return {
                                    "image_base64": img_base64,
                                    "dimensions": f"{img.width}x{img.height}",
                                    "prompt_id": prompt_id
                                }
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Wait error: {e}")
            time.sleep(1)
    
    return {"error": "Timeout"}

def handler(job):
    """Main handler"""
    print(f"\n🎯 Received job")
    
    try:
        input_data = job["input"]
        prompt = input_data.get("prompt", "").strip()
        
        if not prompt:
            return {"error": "No prompt provided"}
        
        print(f"📝 Prompt: {prompt[:100]}...")
        
        # Ensure models are linked
        ensure_models_exist()
        
        # Generate image
        start_time = time.time()
        result = generate_image(prompt)
        generation_time = time.time() - start_time
        
        if "image_base64" in result:
            print(f"✅ Generated in {generation_time:.2f}s")
            return {
                "status": "success",
                "image_base64": result["image_base64"],
                "dimensions": result["dimensions"],
                "generation_time": f"{generation_time:.2f}s",
                "model": "z-image-turbo"
            }
        else:
            return {"error": result.get("error", "Unknown error")}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}

print("\n🏁 Starting RunPod ComfyUI Handler...")
runpod.serverless.start({"handler": handler})