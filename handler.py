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
    try:
        # The Worker sends { input: { ideas: [...] } }
        job_input = job.get('input', {})
        ideas = job_input.get('ideas', []) # Matches the 'ideas' key in Worker
        
        if not ideas:
            return {"status": "error", "message": "No ideas array found"}

        final_results = []
        for idea in ideas:
            # Matches the keys Llama generates
            name = idea.get('name')
            visual_prompt = idea.get('visual')

            # Your ComfyUI + R2 logic
            image_url = run_comfy_and_upload(visual_prompt)

            # Return exactly what the Frontend is looking for
            final_results.append({
                "name": name,
                "url": image_url 
            })

        return {"results": final_results}
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        # This prevents 'exit code 1' by catching the error
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    if wait_for_comfyui():
        runpod.serverless.start({"handler": handler})