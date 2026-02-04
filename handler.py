
import runpod
import requests
import json
import os
import time
import boto3
from botocore.config import Config

# --- CONFIGURATION ---
COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_PATH = "/comfyui/workflow_api.json"
OUTPUT_DIR = "/comfyui/output"

# Cloudflare R2 Config
R2_CONF = {
    'endpoint': "https://d165cffd95013bf358b1f0cac3753628.r2.cloudflarestorage.com",
    'access_key': "a2e07f81a137d0181c024a157367e15f",
    'secret_key': "dca4b1e433bf208a509aea222778e45f666cc2c862f851842c3268c3343bb259", 
    'bucket': "ai-gift-assets",
    'public_url': "https://pub-518bf750a6194bb7b92bf803e180ed88.r2.dev"
}

def wait_for_comfyui(timeout=240):  # Increased to 4 minutes
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try to connect to ComfyUI
            response = requests.get(f"{COMFY_URL}/system_stats", timeout=10)
            if response.status_code == 200:
                print("✅ ComfyUI is ready!")
                
                # Also check if GGUF nodes are loaded
                try:
                    obj_res = requests.get(f"{COMFY_URL}/object_info", timeout=5)
                    if obj_res.status_code == 200:
                        obj_info = obj_res.json()
                        if 'UnetLoaderGGUF' in str(obj_info):
                            print("✅ GGUF nodes are loaded!")
                        else:
                            print("⚠️ GGUF nodes may not be loaded")
                except:
                    pass
                    
                return True
        except requests.exceptions.ConnectionError:
            print(f"⏳ Waiting for ComfyUI... ({int(time.time() - start_time)}s)")
        except Exception as e:
            print(f"⚠️ ComfyUI check error: {e}")
        time.sleep(5)
    print("❌ ComfyUI failed to start within timeout")
    return False

def upload_to_r2(file_path, file_name):
    s3 = boto3.client('s3',
        endpoint_url=R2_CONF['endpoint'],
        aws_access_key_id=R2_CONF['access_key'],
        aws_secret_access_key=R2_CONF['secret_key'],
        config=Config(signature_version='s3v4')
    )
    s3.upload_file(file_path, R2_CONF['bucket'], file_name, ExtraArgs={'ContentType': 'image/png'})
    return f"{R2_CONF['public_url']}/{file_name}"

def handler(job):
    print(f"🎬 Starting image generation job")
    
    # Wait for ComfyUI to be ready
    if not wait_for_comfyui(180):
        return {
            "status": "failed",
            "error": "ComfyUI failed to start",
            "note": "Endpoint is cold-starting"
        }
    
    job_input = job['input']
    user_prompt = job_input.get("prompt", "")
    
    if not user_prompt:
        return {"error": "No prompt provided"}
    
    print(f"📝 Prompt: {user_prompt}")
    
    try:
        # Load workflow
        with open("/comfyui/workflow_api.json", 'r') as f:
            workflow = json.load(f)
        
        # Update prompt in workflow
        if "34:27" in workflow and "inputs" in workflow["34:27"]:
            workflow["34:27"]["inputs"]["text"] = user_prompt
        
        # Create unique filename
        timestamp = int(time.time())
        file_prefix = f"gen_{timestamp}"
        workflow["9"]["inputs"]["filename_prefix"] = file_prefix

        # Clear old outputs
        if os.path.exists(OUTPUT_DIR):
            for f in os.listdir(OUTPUT_DIR):
                os.remove(os.path.join(OUTPUT_DIR, f))

        # Send job to ComfyUI
        print("Sending prompt to ComfyUI...")
        response = requests.post(f"{COMFY_URL}/prompt", 
                               json={"prompt": workflow}, 
                               timeout=30)
        
        if response.status_code != 200:
            return {"error": f"ComfyUI rejected prompt: {response.text}"}
        
        res_json = response.json()
        if "error" in res_json:
            return {"error": f"ComfyUI error: {res_json['error']}"}
        
        prompt_id = res_json.get("prompt_id")
        print(f"Prompt ID: {prompt_id}")

        # Wait for image with timeout
        found_file = None
        for attempt in range(60):  # 60 * 2 seconds = 120 seconds timeout
            try:
                # Check history
                history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=5)
                if history_res.status_code == 200:
                    history = history_res.json()
                    if prompt_id in history:
                        # Image should be generated
                        if os.path.exists(OUTPUT_DIR):
                            files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(file_prefix)]
                            if files:
                                found_file = os.path.join(OUTPUT_DIR, files[0])
                                print(f"Found output file: {found_file}")
                                break
            except:
                pass  # Ignore connection errors while polling
            
            time.sleep(2)

        if not found_file or not os.path.exists(found_file):
            return {"error": "Image generation timeout or failed"}

        # Upload to R2
        file_name = f"{file_prefix}.png"
        r2_url = upload_to_r2(found_file, file_name)
        
        print(f"✅ Image generated successfully: {r2_url}")
        
        # Return with proper structure
        return {
            "status": "success",
            "image_url": r2_url,
            "images": [r2_url]  # Also return as array for frontend compatibility
        }

    except Exception as e:
        print(f"❌ Handler error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})