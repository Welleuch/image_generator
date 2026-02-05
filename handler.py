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

def wait_for_images(prompt_id):
    """Polls ComfyUI until the prompt_id is no longer in the queue/running."""
    while True:
        # Check history to see if it's finished
        history_resp = requests.get(f"http://127.0.0.1:8188/history/{prompt_id}").json()
        if prompt_id in history_resp:
            print(f"✅ Image generation for {prompt_id} complete!")
            # Return the filenames created by this prompt
            return history_resp[prompt_id]['outputs']
        
        print("⏳ Waiting for ComfyUI to finish rendering...")
        time.sleep(2) # Wait 2 seconds before checking again

def handler(job):
    print("🎬 Starting batch image generation...")
    try:
        prompts = job['input'].get("visual_prompts", [])
        if isinstance(prompts, str): prompts = [prompts]
        
        results = []
        for i, text in enumerate(prompts):
            # 1. Send to ComfyUI
            # ... (your existing code to update workflow_api.json) ...
            resp = requests.post("http://127.0.0.1:8188/prompt", json={"prompt": workflow}).json()
            prompt_id = resp.get('prompt_id')

            # 2. BLOCKING WAIT (This prevents the 'Fast Finish' bug)
            outputs = wait_for_images(prompt_id)

            # 3. UPLOAD TO R2
            # Use the 'outputs' from above to find the exact file in /comfyui/output/
            # and upload it to your Cloudflare R2.
            image_url = upload_to_r2(prompt_id) # Your upload function
            results.append(image_url)

        return {"status": "success", "image_urls": results}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    if wait_for_comfyui():
        print("🏁 Starte RunPod Serverless Loop...")
        runpod.serverless.start({"handler": handler})
    else:
        print("❌ Abbruch: ComfyUI konnte nicht erreicht werden.")
        exit(1)