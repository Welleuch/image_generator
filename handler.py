import os, requests, json, time, runpod, boto3
from botocore.config import Config

COMFY_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = "/comfyui/output"
WORKFLOW_PATH = "/comfyui/workflow_api.json"

R2_CONF = {
    'endpoint': "https://d165cffd95013bf358b1f0cac3753628.r2.cloudflarestorage.com",
    'access_key': "a2e07f81a137d0181c024a157367e15f",
    'secret_key': "dca4b1e433bf208a509aea222778e45f666cc2c862f851842c3268c3343bb259",
    'bucket': "ai-gift-assets",
    'public_url': "https://pub-518bf750a6194bb7b92bf803e180ed88.r2.dev"
}

def wait_for_comfyui(timeout=300):
    print(f"🚀 Warte auf ComfyUI unter {COMFY_URL}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{COMFY_URL}/system_stats", timeout=5)
            if response.status_code == 200:
                print(f"✅ ComfyUI ist bereit nach {int(time.time() - start_time)}s!")
                return True
        except Exception:
            pass
        time.sleep(5)
    
    # FIX: This now runs if the loop times out
    if os.path.exists("/comfyui_logs.txt"):
        with open("/comfyui_logs.txt", "r") as f:
            print(f"❌ ComfyUI ERROR LOGS:\n{f.read()}")
    return False

def clean_prompt(prompt):
    if not prompt or not isinstance(prompt, str):
        return "3D printable Gray PLA decorative object"
    return prompt.strip()

def handler(job):
    print("🎬 Starting batch image generation...")
    try:
        job_input = job['input']
        # If llama sends a list called 'visual_prompts', we use it
        prompts = job_input.get("visual_prompts", [])
        
        # If it's just a single string, wrap it in a list
        if isinstance(prompts, str):
            prompts = [prompts]
            
        final_urls = []

        with open(WORKFLOW_PATH, 'r') as f:
            base_workflow = json.load(f)

        for i, raw_prompt in enumerate(prompts):
            print(f"📸 Processing image {i+1}/{len(prompts)}: {raw_prompt[:30]}...")
            prompt = clean_prompt(raw_prompt)
            
            # Update workflow nodes
            if "34:27" in base_workflow: base_workflow["34:27"]["inputs"]["text"] = prompt
            
            # Send to ComfyUI
            response = requests.post(f"{COMFY_URL}/prompt", json={"prompt": base_workflow})
            prompt_id = response.json().get('prompt_id')

            # --- POLLING LOGIC ---
            # Wait for the image to be generated before moving to the next one
            image_url = wait_for_image_and_upload(prompt_id) # You need to implement this helper
            final_urls.append(image_url)

        return {
            "status": "success",
            "image_urls": final_urls,
            "count": len(final_urls)
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if wait_for_comfyui():
        print("🏁 Starte RunPod Serverless Loop...")
        runpod.serverless.start({"handler": handler})
    else:
        print("❌ Abbruch: ComfyUI konnte nicht erreicht werden.")
        exit(1)