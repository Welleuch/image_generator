import runpod
import requests
import json
import base64
import os
import time

# --- NEW: Wait for ComfyUI to wake up ---
def wait_for_service(url, timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(url)
            print("✅ ComfyUI is ready!")
            return True
        except requests.exceptions.ConnectionError:
            print("⏳ Waiting for ComfyUI to start...")
            time.sleep(2)
    return False

# Load workflow
with open('/comfyui/workflow_api.json', 'r') as f:
    workflow_template = json.load(f)

def handler(job):
    # Ensure service is up before processing the first job
    if not wait_for_service("http://127.0.0.1:8188"):
        return {"error": "ComfyUI failed to start within timeout"}

    job_input = job['input']
    user_prompt = job_input.get("prompt")
    
    if user_prompt:
        workflow_template["34:27"]["inputs"]["text"] = user_prompt

    workflow_template["9"]["inputs"]["filename_prefix"] = "serverless_out"

    try:
        response = requests.post("http://127.0.0.1:8188/prompt", json={"prompt": workflow_template})
        # ... rest of your existing logic ...
        return response.json() 
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})