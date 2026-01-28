import runpod
import requests
import json
import base64
import os
import time
import boto3
from botocore.config import Config

# --- CONFIGURATION ---
COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_PATH = "/comfyui/workflow_api.json"
OUTPUT_DIR = "/comfyui/output" # Internal ComfyUI output

# R2 Configuration
R2_CONF = {
    'endpoint': f"https://d165cffd95013bf358b1f0cac3753628.r2.cloudflarestorage.com",
    'access_key': 'a2e07f81a137d0181c024a157367e15f',
    'secret_key': 'dca4b1e433bf208a509aea222778e45f666cc2c862f851842c3268c3343bb259',
    'bucket': 'ai-gift-assets',
    'public_url': 'https://pub-518bf750a6194bb7b92bf803e180ed88.r2.dev'
}

# --- HELPER FUNCTIONS ---

def wait_for_comfyui(timeout=120):
    """Wait for ComfyUI to finish loading GGUF models and start the API."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(COMFY_URL)
            print("✅ ComfyUI is live!")
            return True
        except requests.exceptions.ConnectionError:
            print("⏳ ComfyUI is booting up (loading GGUF weights)...")
            time.sleep(5)
    return False

def upload_to_r2(file_path, file_name):
    """Uploads the generated image to Cloudflare R2."""
    s3 = boto3.client('s3',
        endpoint_url=R2_CONF['endpoint'],
        aws_access_key_id=R2_CONF['access_key'],
        aws_secret_access_key=R2_CONF['secret_key'],
        config=Config(signature_version='s3v4')
    )
    s3.upload_file(file_path, R2_CONF['bucket'], file_name, ExtraArgs={'ContentType': 'image/png'})
    return f"{R2_CONF['public_url']}/{file_name}"

# --- MAIN HANDLER ---

def handler(job):
    # 1. Ensure ComfyUI is actually running
    if not wait_for_comfyui():
        return {"error": "ComfyUI failed to start within timeout."}

    job_input = job['input']
    user_prompt = job_input.get("prompt")
    
    # 2. Load the baked-in workflow
    with open(WORKFLOW_PATH, 'r') as f:
        workflow = json.load(f)

    # 3. Inject the prompt into your specific Z-Image node
    if user_prompt:
        workflow["34:27"]["inputs"]["text"] = user_prompt
    
    # Set unique filename to avoid collisions
    timestamp = int(time.time())
    file_prefix = f"gen_{timestamp}"
    workflow["9"]["inputs"]["filename_prefix"] = file_prefix

    try:
        # 4. Clear old outputs to find the new one easily
        for f in os.listdir(OUTPUT_DIR):
            os.remove(os.path.join(OUTPUT_DIR, f))

        # 5. Send job to ComfyUI
        send_job = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow})
        print(f"Job Sent: {send_job.json()}")

        # 6. Poll for the result (Wait for image to appear)
        found_file = None
        for _ in range(60): # 60 second timeout for generation
            files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(file_prefix)]
            if files:
                found_file = os.path.join(OUTPUT_DIR, files[0])
                break
            time.sleep(2)

        if not found_file:
            return {"error": "Timeout: Image was not generated in time."}

        # 7. Upload to Cloudflare R2
        r2_url = upload_to_r2(found_file, f"{file_prefix}.png")

        # 8. (Optional) Copy to Network Volume for backup
        volume_path = f"/runpod-volume/output/{file_prefix}.png"
        with open(found_file, "rb") as f_in, open(volume_path, "wb") as f_out:
            f_out.write(f_in.read())

        return {
            "status": "success",
            "image_url": r2_url,
            "volume_path": volume_path
        }

    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})