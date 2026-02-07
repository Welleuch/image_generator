import os, requests, json, time, runpod, boto3, uuid
from botocore.config import Config
import socket
import time

# This pulls the /etc/comfy_workflow.json path from Docker
WORKFLOW_PATH = os.getenv("WORKFLOW_PATH", "/etc/comfy_workflow.json")

def load_workflow():
    try:
        with open(WORKFLOW_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"CRITICAL ERROR: Workflow file missing at {WORKFLOW_PATH}")
        raise

def wait_for_service(host="127.0.0.1", port=8188, timeout=300):
    """Wait for the ComfyUI server to become reachable."""
    start_time = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                print(f"Connected to ComfyUI on {host}:{port}")
                return True
        except (socket.timeout, ConnectionRefusedError):
            if time.time() - start_time > timeout:
                raise Exception(f"Timeout: ComfyUI service not ready after {timeout}s")
            print("Waiting for ComfyUI to start...")
            time.sleep(2)

def upload_to_r2(file_path, key):
    s3_client = boto3.client(
        's3',
        endpoint_url=os.environ.get('R2_ENDPOINT'),
        aws_access_key_id=os.environ.get('R2_ACCESS_KEY'),
        aws_secret_access_key=os.environ.get('R2_SECRET_KEY'),
        config=Config(signature_version='s3v4')
    )
    s3_client.upload_file(file_path, os.environ.get('R2_BUCKET'), key, ExtraArgs={'ContentType': 'image/png'})
    return f"{os.environ.get('R2_PUBLIC_URL')}/{key}"

def handler(job):
    # Wait up to 5 minutes for the local server to start
    wait_for_service("127.0.0.1", 8188) 
    
    client = ComfyUIClient()
    try:
        prompt_text = job['input'].get('visual_prompt')
        
        # CHANGED: Use the robust loader instead of hardcoded root path
        workflow = load_workflow()

        # Target specific node if it exists
        if "34:27" in workflow:
            workflow["34:27"]["inputs"]["text"] = prompt_text
        
        # Fallback: Update any CLIPTextEncode node
        for node_id in workflow:
            if workflow[node_id].get('class_type') == 'CLIPTextEncode':
                workflow[node_id]['inputs']['text'] = prompt_text
                break

        # Submit to ComfyUI
        res = requests.post("http://127.0.0.1:8188/prompt", json={"prompt": workflow}).json()
        if 'error' in res:
            raise Exception(f"ComfyUI Error: {res['error']}")
            
        prompt_id = res['prompt_id']
        
        # Poll for Image
        filename = None
        while not filename:
            hist = requests.get(f"http://127.0.0.1:8188/history/{prompt_id}").json()
            if prompt_id in hist:
                outputs = hist[prompt_id]['outputs']
                for node in outputs:
                    if 'images' in outputs[node]:
                        filename = outputs[node]['images'][0]['filename']
                        break
                break
            time.sleep(1)

        # Upload and Cleanup
        full_path = f"/comfyui/output/{filename}"
        public_url = upload_to_r2(full_path, f"gen_{int(time.time())}.png")
        
        if os.path.exists(full_path):
            os.remove(full_path) 

        return {"status": "success", "image_url": public_url}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})