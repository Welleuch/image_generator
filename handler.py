import os, requests, json, time, runpod, boto3
from botocore.config import Config

# Config
COMFY_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = "/comfyui/output"
WORKFLOW_PATH = "/comfyui/workflow_api.json"  # <-- Fixed path

# R2 Config (same as before)
R2_CONF = {
    'endpoint': "https://d165cffd95013bf358b1f0cac3753628.r2.cloudflarestorage.com",
    'access_key': "a2e07f81a137d0181c024a157367e15f",
    'secret_key': "dca4b1e433bf208a509aea222778e45f666cc2c862f851842c3268c3343bb259",
    'bucket': "ai-gift-assets",
    'public_url': "https://pub-518bf750a6194bb7b92bf803e180ed88.r2.dev"
}

def upload_to_r2(file_path, file_name):
    """Upload file to R2"""
    s3 = boto3.client('s3',
        endpoint_url=R2_CONF['endpoint'],
        aws_access_key_id=R2_CONF['access_key'],
        aws_secret_access_key=R2_CONF['secret_key'],
        config=Config(signature_version='s3v4')
    )
    s3.upload_file(file_path, R2_CONF['bucket'], file_name)
    return f"{R2_CONF['public_url']}/{file_name}"

def wait_for_comfyui(timeout=120):
    """Wait for ComfyUI to start"""
    for i in range(timeout // 5):
        try:
            response = requests.get(f"{COMFY_URL}/system_stats", timeout=5)
            if response.status_code == 200:
                print("✅ ComfyUI is ready!")
                return True
        except:
            pass
        print(f"⏳ Waiting for ComfyUI... ({i*5}s)")
        time.sleep(5)
    print("❌ ComfyUI failed to start")
    return False

def handler(job):
    print("🎬 Starting image generation job")
    
    # Wait for ComfyUI
    if not wait_for_comfyui():
        return {"error": "ComfyUI failed to start"}
    
    job_input = job['input']
    prompt = job_input.get("prompt", "")
    
    if not prompt:
        return {"error": "No prompt provided"}
    
    print(f"📝 Prompt: {prompt[:100]}...")
    
    try:
        # Load workflow - FIXED PATH
        print(f"Loading workflow from: {WORKFLOW_PATH}")
        if not os.path.exists(WORKFLOW_PATH):
            return {"error": f"Workflow file not found at {WORKFLOW_PATH}"}
            
        with open(WORKFLOW_PATH, 'r') as f:
            workflow = json.load(f)
        
        # Update prompt in the workflow
        # Find the CLIPTextEncode node (node "34:27" in your workflow)
        if "34:27" in workflow and "inputs" in workflow["34:27"]:
            workflow["34:27"]["inputs"]["text"] = prompt
        else:
            # Fallback: find any CLIPTextEncode node
            for node_id, node in workflow.items():
                if node.get("class_type") == "CLIPTextEncode":
                    if "text" in node.get("inputs", {}):
                        workflow[node_id]["inputs"]["text"] = prompt
                        break
        
        # Create unique filename
        timestamp = int(time.time())
        file_prefix = f"gen_{timestamp}"
        
        # Update SaveImage node filename
        if "9" in workflow and "inputs" in workflow["9"]:
            workflow["9"]["inputs"]["filename_prefix"] = file_prefix
        else:
            # Fallback: find SaveImage node
            for node_id, node in workflow.items():
                if node.get("class_type") == "SaveImage":
                    workflow[node_id]["inputs"]["filename_prefix"] = file_prefix
                    break
        
        # Send to ComfyUI
        print("🚀 Sending to ComfyUI...")
        response = requests.post(f"{COMFY_URL}/prompt", 
                               json={"prompt": workflow},
                               timeout=30)
        
        if response.status_code != 200:
            return {"error": f"ComfyUI error: {response.text}"}
        
        data = response.json()
        if "error" in data:
            return {"error": f"ComfyUI error: {data['error']}"}
        
        prompt_id = data.get("prompt_id")
        print(f"✅ Prompt ID: {prompt_id}")
        
        # Wait for result
        print("⏳ Waiting for image generation...")
        for attempt in range(60):  # 60 * 2 seconds = 120 seconds timeout
            time.sleep(2)
            
            # Check if file exists in output directory
            if os.path.exists(OUTPUT_DIR):
                files = [f for f in os.listdir(OUTPUT_DIR) 
                        if f.startswith(file_prefix) and f.endswith('.png')]
                if files:
                    file_path = os.path.join(OUTPUT_DIR, files[0])
                    print(f"✅ Image generated: {files[0]}")
                    
                    # Upload to R2
                    print("☁️ Uploading to R2...")
                    r2_url = upload_to_r2(file_path, f"{file_prefix}.png")
                    
                    return {
                        "status": "success",
                        "image_url": r2_url,
                        "images": [r2_url]
                    }
            
            if attempt % 10 == 0:  # Log every 20 seconds
                print(f"Still waiting... ({attempt*2}s)")
        
        return {"error": "Timeout waiting for image"}
        
    except Exception as e:
        print(f"❌ Handler error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

print("🏁 Starting handler...")
runpod.serverless.start({"handler": handler})