import os, requests, json, time, runpod, boto3, uuid
from botocore.config import Config

def upload_to_r2(file_path, key):
    # Use environment variables set in RunPod dashboard
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
    try:
        prompt_text = job['input'].get('visual_prompt')
        with open("/workflow_api.json", 'r') as f:
            workflow = json.load(f)
        if "34:27" in workflow:
            workflow["34:27"]["inputs"]["text"] = prompt_text
        # 1. Update Prompt (find your CLIPTextEncode node)
        for node_id in workflow:
            if workflow[node_id].get('class_type') == 'CLIPTextEncode':
                workflow[node_id]['inputs']['text'] = prompt_text
                break

        # 2. Submit to ComfyUI (Internal 127.0.0.1)
        res = requests.post("http://127.0.0.1:8188/prompt", json={"prompt": workflow}).json()
        prompt_id = res['prompt_id']
        
        # 3. Poll for Image
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

        # 4. Upload and Cleanup
        full_path = f"/comfyui/output/{filename}"
        public_url = upload_to_r2(full_path, f"gen_{int(time.time())}.png")
        os.remove(full_path) 

        return {"status": "success", "image_url": public_url}
    except Exception as e:
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})