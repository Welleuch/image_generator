import os, requests, json, time, runpod, boto3
from botocore.config import Config

COMFY_URL = "http://127.0.0.1:8188"
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
                print(f"✅ ComfyUI ist bereit!")
                return True
        except: pass
        time.sleep(5)
    return False

def upload_to_r2(local_path, r2_filename):
    print(f"📤 Uploading {r2_filename} to R2...")
    s3 = boto3.client('s3',
        endpoint_url=R2_CONF['endpoint'],
        aws_access_key_id=R2_CONF['access_key'],
        aws_secret_access_key=R2_CONF['secret_key'],
        config=Config(signature_version='s3v4')
    )
    try:
        filesize = os.path.getsize(local_path)
        print(f"📝 Local file size: {filesize} bytes")
        if filesize == 0: raise Exception("Local file is empty!")

        with open(local_path, "rb") as data:
            s3.put_object(Bucket=R2_CONF['bucket'], Key=r2_filename, Body=data, ContentType='image/png')
        return f"{R2_CONF['public_url']}/{r2_filename}"
    except Exception as e:
        print(f"❌ R2 Error: {str(e)}")
        raise e

def handler(job):
    print("🎬 Starting batch image generation...")
    try:
        prompts = job['input'].get("visual_prompts", [])
        if isinstance(prompts, str): prompts = [prompts]
        final_urls = []

        with open(WORKFLOW_PATH, 'r') as f:
            workflow = json.load(f)

        for i, raw_prompt in enumerate(prompts):
            print(f"📸 Processing: {raw_prompt}")
            if "34:27" in workflow: workflow["34:27"]["inputs"]["text"] = raw_prompt.strip()
            
            # 1. Trigger
            res = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}).json()
            prompt_id = res['prompt_id']
            
            # 2. Wait
            completed = False
            while not completed:
                time.sleep(2)
                hist = requests.get(f"{COMFY_URL}/history/{prompt_id}").json()
                if prompt_id in hist: completed = True
            
            # 3. Fetch Image via API (Universal way)
            img_info = hist[prompt_id]['outputs']['9']['images'][0]
            filename = img_info['filename']
            subfolder = img_info.get('subfolder', '')
            
            view_url = f"{COMFY_URL}/view?filename={filename}&subfolder={subfolder}&type=output"
            print(f"📥 Fetching image from: {view_url}")
            
            img_data = requests.get(view_url).content
            temp_path = f"/tmp/{filename.split('/')[-1]}"
            with open(temp_path, "wb") as f: f.write(img_data)
            
            # 4. Upload
            final_urls.append(upload_to_r2(temp_path, f"gen_{int(time.time())}_{i}.png"))
            if os.path.exists(temp_path): os.remove(temp_path)

        return {"status": "success", "image_urls": final_urls}
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    if wait_for_comfyui():
        runpod.serverless.start({"handler": handler})