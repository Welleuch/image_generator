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
    
    if os.path.exists("/comfyui_logs.txt"):
        with open("/comfyui_logs.txt", "r") as f:
            print(f"❌ ComfyUI ERROR LOGS:\n{f.read()}")
    return False

def clean_prompt(prompt):
    if not prompt or not isinstance(prompt, str):
        return "3D printable Gray PLA decorative object"
    return prompt.strip()

def upload_to_r2(local_path, r2_filename):
    """Uploads the generated image from ComfyUI output to Cloudflare R2"""
    print(f"📤 Uploading {r2_filename} to R2...")
    s3 = boto3.client(
        's3',
        endpoint_url=R2_CONF['endpoint'],
        aws_access_key_id=R2_CONF['access_key'],
        aws_secret_access_key=R2_CONF['secret_key'],
        config=Config(signature_version='s3v4')
    )
    try:
        s3.upload_file(local_path, R2_CONF['bucket'], r2_filename, ExtraArgs={'ContentType': 'image/png'})
        public_url = f"{R2_CONF['public_url']}/{r2_filename}"
        print(f"✅ Upload successful: {public_url}")
        return public_url
    except Exception as e:
        print(f"❌ R2 Upload Failed: {str(e)}")
        raise e

def handler(job):
    print("🎬 Starting batch image generation...")
    try:
        job_input = job['input']
        prompts = job_input.get("visual_prompts", [])
        
        if isinstance(prompts, str):
            prompts = [prompts]
            
        final_urls = []

        with open(WORKFLOW_PATH, 'r') as f:
            workflow = json.load(f)

        for i, raw_prompt in enumerate(prompts):
            print(f"📸 Processing {i+1}/{len(prompts)}: {raw_prompt}")
            prompt_text = clean_prompt(raw_prompt)
            
            # Update the prompt text in workflow (Node 34:27 in your setup)
            if "34:27" in workflow: 
                workflow["34:27"]["inputs"]["text"] = prompt_text
            
            # 1. Trigger ComfyUI
            response = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow})
            prompt_id = response.json().get('prompt_id')
            
            # 2. BLOCKING WAIT
            completed = False
            history = {}
            while not completed:
                time.sleep(2)
                history_resp = requests.get(f"{COMFY_URL}/history/{prompt_id}").json()
                if prompt_id in history_resp:
                    history = history_resp[prompt_id]
                    completed = True
                    print(f"✅ Image {i+1} generated.")
            
            # 3. GET FILENAME AND UPLOAD
            # Node '9' is your Save Image node
            filename = history['outputs']['9']['images'][0]['filename']
            file_path = os.path.join(OUTPUT_DIR, filename)
            
            r2_url = upload_to_r2(file_path, f"gen_{int(time.time())}_{i}.png")
            final_urls.append(r2_url)

        return {
            "status": "success",
            "image_urls": final_urls
        }
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    if wait_for_comfyui():
        print("🏁 Starte RunPod Serverless Loop...")
        runpod.serverless.start({"handler": handler})
    else:
        print("❌ Abbruch: ComfyUI konnte nicht erreicht werden.")
        exit(1)