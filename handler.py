import os, requests, json, time, runpod, boto3
from botocore.config import Config

# Config
COMFY_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = "/comfyui/output"
WORKFLOW_PATH = "/comfyui/workflow_api.json"

# R2 Config (Deine Daten)
R2_CONF = {
    'endpoint': "https://d165cffd95013bf358b1f0cac3753628.r2.cloudflarestorage.com",
    'access_key': "a2e07f81a137d0181c024a157367e15f",
    'secret_key': "dca4b1e433bf208a509aea222778e45f666cc2c862f851842c3268c3343bb259",
    'bucket': "ai-gift-assets",
    'public_url': "https://pub-518bf750a6194bb7b92bf803e180ed88.r2.dev"
}

def upload_to_r2(file_path, file_name):
    try:
        s3 = boto3.client('s3',
            endpoint_url=R2_CONF['endpoint'],
            aws_access_key_id=R2_CONF['access_key'],
            aws_secret_access_key=R2_CONF['secret_key'],
            config=Config(signature_version='s3v4')
        )
        s3.upload_file(file_path, R2_CONF['bucket'], file_name, 
                      ExtraArgs={'ContentType': 'image/png'})
        return f"{R2_CONF['public_url']}/{file_name}"
    except Exception as e:
        print(f"❌ R2 upload error: {e}")
        raise

def wait_for_comfyui(timeout=300):
    """Prüft dynamisch, ob ComfyUI bereit ist"""
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
    
    # Logic moved outside the loop so it actually runs on failure
    if os.path.exists("/comfyui_logs.txt"):
        with open("/comfyui_logs.txt", "r") as f:
            print(f"❌ ComfyUI failed to start. Logs:\n{f.read()}")
    return False

def clean_prompt(prompt):
    # ... (Deine bestehende clean_prompt Logik beibehalten) ...
    if not prompt or not isinstance(prompt, str):
        return "3D printable Gray PLA decorative object"
    cleaned = prompt.strip()
    return cleaned

def handler(job):
    # Die Zeitmessung sollte hier starten
    start_time = time.time()
    print("🎬 Starte Bildgenerierung...")
    
    try:
        job_input = job['input']
        raw_prompt = job_input.get("prompt", "")
        prompt = clean_prompt(raw_prompt)
        
        with open(WORKFLOW_PATH, 'r') as f:
            workflow = json.load(f)
        
        # Node-Updates (wie in deinem Code)
        if "34:27" in workflow: workflow["34:27"]["inputs"]["text"] = prompt
        
        # Seed & Filename
        seed = int(time.time() * 1000) % 1000000000
        timestamp = int(time.time())
        file_prefix = f"gen_{timestamp}"
        if "9" in workflow: workflow["9"]["inputs"]["filename_prefix"] = f"output/{file_prefix}"

        # Request an ComfyUI
        response = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}, timeout=60)
        
        # ... (Warten auf Datei und R2 Upload wie in deinem Code) ...
        # Hier gekürzt für die Übersicht:
        found_file = None # Hier kommt deine Such-Logik rein
        
        # (Platzhalter für deine R2 Upload Logik)
        r2_url = "URL_NACH_UPLOAD" 

        return {
            "status": "success",
            "image_url": r2_url,
            "prompt_used": prompt
        }
    except Exception as e:
        return {"error": str(e)}

# DAS IST DER ENTSCHEIDENDE NEUE TEIL
if __name__ == "__main__":
    # Erst warten wir, bis der Hintergrund-Prozess (main.py) wirklich da ist
    if wait_for_comfyui():
        print("🏁 Starte RunPod Serverless Loop...")
        runpod.serverless.start({"handler": handler})
    else:
        print("❌ Abbruch: ComfyUI konnte nicht erreicht werden.")
        exit(1)
