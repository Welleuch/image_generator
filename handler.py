import os, requests, json, time, runpod, boto3
from botocore.config import Config

# Config
COMFY_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = "/comfyui/output"
WORKFLOW_PATH = "/comfyui/workflow_api.json"

# R2 Config
R2_CONF = {
    'endpoint': "https://d165cffd95013bf358b1f0cac3753628.r2.cloudflarestorage.com",
    'access_key': "a2e07f81a137d0181c024a157367e15f",
    'secret_key': "dca4b1e433bf208a509aea222778e45f666cc2c862f851842c3268c3343bb259",
    'bucket': "ai-gift-assets",
    'public_url': "https://pub-518bf750a6194bb7b92bf803e180ed88.r2.dev"
}

def upload_to_r2(file_path, file_name):
    """Upload file to R2"""
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

def wait_for_comfyui(timeout=120):
    """Wait for ComfyUI to start"""
    for i in range(timeout // 5):
        try:
            response = requests.get(f"{COMFY_URL}/system_stats", timeout=10)
            if response.status_code == 200:
                print("✅ ComfyUI is ready!")
                return True
        except requests.exceptions.ConnectionError:
            print(f"⏳ Waiting for ComfyUI... ({i*5}s)")
        except Exception as e:
            print(f"⚠️ ComfyUI check error: {e}")
        time.sleep(5)
    print("❌ ComfyUI failed to start within timeout")
    return False

def clean_prompt(prompt):
    """Clean and format prompt for image generation"""
    if not prompt or not isinstance(prompt, str):
        return "3D printable Gray PLA decorative object, desk-sized, minimalist design"
    
    cleaned = prompt.strip()
    
    # Remove common problematic prefixes
    prefixes_to_remove = [
        "PLA Gray",
        "Gray PLA",
        "**Visual Description:**",
        "**Visual:**",
        "Visual:",
        "Description:",
        "Please provide",
        "include the following"
    ]
    
    for prefix in prefixes_to_remove:
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip()
    
    # Ensure it starts with 3D printable
    if not cleaned.lower().startswith('3d printable'):
        cleaned = f"3D printable {cleaned}"
    
    # Ensure it mentions material
    if 'gray' not in cleaned.lower() and 'grey' not in cleaned.lower():
        cleaned = f"Gray PLA {cleaned}"
    elif 'pla' not in cleaned.lower():
        cleaned = cleaned.replace('gray', 'Gray PLA').replace('grey', 'Grey PLA')
    
    # Remove markdown and extra spaces
    cleaned = cleaned.replace('**', '').replace('__', '')
    cleaned = ' '.join(cleaned.split())
    
    # Limit length
    if len(cleaned) > 250:
        cleaned = cleaned[:250] + "..."
    
    return cleaned

def handler(job):
    print("🎬 Starting image generation job")
    
    # Wait for ComfyUI
    if not wait_for_comfyui():
        return {"error": "ComfyUI failed to start"}
    
    try:
        job_input = job['input']
        raw_prompt = job_input.get("prompt", "")
        
        if not raw_prompt:
            return {"error": "No prompt provided"}
        
        # Clean the prompt
        prompt = clean_prompt(raw_prompt)
        print(f"📝 Cleaned prompt: {prompt[:100]}...")
        
        # Load workflow
        print(f"📂 Loading workflow from: {WORKFLOW_PATH}")
        if not os.path.exists(WORKFLOW_PATH):
            return {"error": f"Workflow file not found at {WORKFLOW_PATH}"}
            
        with open(WORKFLOW_PATH, 'r') as f:
            workflow = json.load(f)
        
        # Update prompt in workflow (node 34:27)
        if "34:27" in workflow and "inputs" in workflow["34:27"]:
            workflow["34:27"]["inputs"]["text"] = prompt
        else:
            # Fallback search
            for node_id, node in workflow.items():
                if node.get("class_type") == "CLIPTextEncode":
                    if "text" in node.get("inputs", {}):
                        workflow[node_id]["inputs"]["text"] = prompt
                        break
        
        # Update seed for variety
        seed = int(time.time() * 1000) % 1000000000
        if "34:3" in workflow and "inputs" in workflow["34:3"]:
            workflow["34:3"]["inputs"]["seed"] = seed
        
        # Update filename prefix
        timestamp = int(time.time())
        file_prefix = f"gen_{timestamp}"
        if "9" in workflow and "inputs" in workflow["9"]:
            workflow["9"]["inputs"]["filename_prefix"] = f"output/{file_prefix}"
        
        # Send to ComfyUI
        print("🚀 Sending to ComfyUI...")
        response = requests.post(f"{COMFY_URL}/prompt", 
                               json={"prompt": workflow},
                               timeout=60)
        
        if response.status_code != 200:
            error_text = response.text[:500]
            print(f"❌ ComfyUI error: {error_text}")
            return {"error": f"ComfyUI error: {error_text}"}
        
        data = response.json()
        if "error" in data:
            print(f"❌ ComfyUI error: {data['error']}")
            return {"error": f"ComfyUI error: {data['error']}"}
        
        prompt_id = data.get("prompt_id")
        print(f"✅ Prompt ID: {prompt_id}")
        
        # Wait for result
        print("⏳ Waiting for image generation...")
        found_file = None
        
        for attempt in range(60):  # 2 minute timeout
            time.sleep(2)
            
            # Check output directory
            if os.path.exists(OUTPUT_DIR):
                files = [f for f in os.listdir(OUTPUT_DIR) 
                        if f.startswith(file_prefix) and f.endswith('.png')]
                if files:
                    found_file = os.path.join(OUTPUT_DIR, files[0])
                    print(f"✅ Image generated: {files[0]}")
                    break
            
            if attempt % 10 == 0:  # Log every 20 seconds
                print(f"Still waiting... ({attempt*2}s)")
        
        if not found_file or not os.path.exists(found_file):
            print("❌ Timeout waiting for image")
            return {"error": "Timeout waiting for image generation"}
        
        # Upload to R2
        print("☁️ Uploading to R2...")
        r2_filename = f"{file_prefix}.png"
        r2_url = upload_to_r2(found_file, r2_filename)
        
        print(f"✅ Upload successful: {r2_url}")
        
        return {
            "status": "success",
            "image_url": r2_url,
            "images": [r2_url],
            "prompt_used": prompt,
            "execution_time": f"{time.time() - start_time:.1f}s"
        }
        
    except Exception as e:
        print(f"❌ Handler error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

print("🏁 Starting image generation handler...")
runpod.serverless.start({"handler": handler})