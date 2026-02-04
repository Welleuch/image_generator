
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

def wait_for_comfyui(timeout=180):  # Increased from 120 to 180 seconds
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try to connect to ComfyUI
            response = requests.get(f"{COMFY_URL}/system_stats", timeout=5)
            if response.status_code == 200:
                print("✅ ComfyUI is ready!")
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
    
    # First, wait for ComfyUI to be ready (with longer timeout)
    if not wait_for_comfyui(180):
        return {
            "error": "ComfyUI failed to start within 3 minutes",
            "status": "failed",
            "note": "Endpoint is cold-starting, please try again in 2 minutes"
        }
    
    job_input = job['input']
    user_prompt = job_input.get("prompt")
    
    print(f"📝 Prompt: {user_prompt[:100]}...")
    workflow = json.load(f)

    if user_prompt:
        workflow["34:27"]["inputs"]["text"] = user_prompt
    
    file_prefix = f"gen_{int(time.time())}"
    workflow["9"]["inputs"]["filename_prefix"] = file_prefix

    try:
        # Clear old outputs
        if os.path.exists(OUTPUT_DIR):
            for f in os.listdir(OUTPUT_DIR):
                os.remove(os.path.join(OUTPUT_DIR, f))

        # Send job
        response = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow})
        res_json = response.json()
        
        # Check if ComfyUI rejected the prompt (e.g., missing nodes)
        if "error" in res_json:
            return {"error": "ComfyUI Prompt Error", "details": res_json["error"]}

        # Wait for image
        found_file = None
        for _ in range(60):
            if os.path.exists(OUTPUT_DIR):
                files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(file_prefix)]
                if files:
                    found_file = os.path.join(OUTPUT_DIR, files[0])
                    break
            time.sleep(2)

        if not found_file:
            return {"error": "Timeout: Image not generated. Check logs for node errors."}

        # Upload & Backup
        r2_url = upload_to_r2(found_file, f"{file_prefix}.png")
        volume_path = f"/runpod-volume/output/{file_prefix}.png"
        
        os.makedirs("/runpod-volume/output", exist_ok=True)
        with open(found_file, "rb") as f_in, open(volume_path, "wb") as f_out:
            f_out.write(f_in.read())

        return {"status": "success", "image_url": r2_url}

    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})