import os, requests, json, time, boto3
from fastapi import FastAPI, Request
from botocore.config import Config
import botocore.session

# FORCE the environment to forget any local AWS regions
os.environ.pop('AWS_DEFAULT_REGION', None)
os.environ.pop('AWS_REGION', None)

app = FastAPI()

# --- DYNAMIC PATH CONFIGURATION ---
# This identifies the 'image-generator' folder where this script lives
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# This identifies the 'Downloads' folder
DOWNLOADS_DIR = os.path.dirname(CURRENT_DIR)

# Folder 1: Image Generator (Where we are)
IMAGE_WORKFLOW = os.path.join(CURRENT_DIR, "workflow_api.json")

# Folder 2: 3D Mesh Generator (Next door in Downloads)
MESH_FOLDER = os.path.join(DOWNLOADS_DIR, "3d-mesh-generator")
MESH_WORKFLOW = os.path.join(MESH_FOLDER, "workflow_api.json")

# ComfyUI Paths (Shared by both workflows on your machine)
COMFY_URL = "http://127.0.0.1:8188"
COMFY_INPUT = "C:/Users/Administrator/Downloads/ComfyUI_windows_portable_nvidia/ComfyUI_windows_portable/ComfyUI/input/"
COMFY_OUTPUT = "C:/Users/Administrator/Downloads/ComfyUI_windows_portable_nvidia/ComfyUI_windows_portable/ComfyUI/output/"

R2_CONF = {
    'endpoint': "https://d165cffd95013bf358b1f0cac3753628.r2.cloudflarestorage.com",
    'access_key': "a2e07f81a137d0181c024a157367e15f",
    'secret_key': "dca4b1e433bf208a509aea222778e45f666cc2c862f851842c3268c3343bb259",
    'bucket': "ai-gift-assets",
    'public_url': "https://pub-518bf750a6194bb7b92bf803e180ed88.r2.dev"
}

def upload_to_r2(local_path, r2_filename, content_type='image/png'):
    print(f"📤 Uploading to R2: {r2_filename}")
    bc_session = botocore.session.get_session()
    bc_session.set_config_variable('region', 'weur')
    
    session = boto3.Session(
        botocore_session=bc_session,
        aws_access_key_id=R2_CONF['access_key'],
        aws_secret_access_key=R2_CONF['secret_key']
    )
    
    r2_config = Config(region_name='weur', signature_version='s3v4')
    s3 = session.client('s3', endpoint_url=R2_CONF['endpoint'], config=r2_config)

    try:
        with open(local_path, "rb") as data:
            s3.put_object(
                Bucket=R2_CONF['bucket'], 
                Key=r2_filename, 
                Body=data, 
                ContentType=content_type
            )
        print(f"🧹 Cleanup: Removing local file {local_path}")
        os.remove(local_path)
        return f"{R2_CONF['public_url'].rstrip('/')}/{r2_filename}"
    except Exception as e:
        print(f"❌ R2 Error: {str(e)}")
        raise e

@app.post("/test-generate")
async def handle_request(request: Request):
    try:
        data = await request.json()
        ideas = data.get('ideas', [])
        final_results = []

        for idea in ideas:
            print(f"🎨 Generating Image for: {idea['name']}")
            with open(IMAGE_WORKFLOW, 'r') as f:
                workflow = json.load(f)

            # Update prompt for 2D generation
            for node_id in workflow:
                if workflow[node_id].get('class_type') == 'CLIPTextEncode':
                    workflow[node_id]['inputs']['text'] = idea['visual']
                    break
            
            res = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}).json()
            prompt_id = res['prompt_id']
            
            filename = None
            while not filename:
                hist = requests.get(f"{COMFY_URL}/history/{prompt_id}").json()
                if prompt_id in hist:
                    outputs = hist[prompt_id]['outputs']
                    for node in outputs:
                        if 'images' in outputs[node]:
                            filename = outputs[node]['images'][0]['filename']
                            break
                    break
                time.sleep(1)

            full_local_path = os.path.join(COMFY_OUTPUT, filename)
            img_url = upload_to_r2(full_local_path, f"gen_{int(time.time())}.png")
            final_results.append({"name": idea['name'], "url": img_url})

        return {"results": final_results}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"error": str(e)}, 500

@app.post("/test-generate-3d")
async def handle_3d_request(request: Request):
    try:
        data = await request.json()
        image_url = data.get('image_url')
        print(f"📦 EXECUTING 3D WORKFLOW FOR: {image_url}")

        # 1. Download input image to ComfyUI input folder
        img_data = requests.get(image_url).content
        input_filename = f"mesh_input_{int(time.time())}.png"
        with open(os.path.join(COMFY_INPUT, input_filename), "wb") as f:
            f.write(img_data)

        # 2. Load your clean workflow_api.json
        with open(MESH_WORKFLOW, 'r') as f:
            workflow = json.load(f)

        # 3. Update the LoadImage node (Node 56) [cite: 11]
        if "56" in workflow:
            workflow["56"]["inputs"]["image"] = input_filename

        # 4. Submit to ComfyUI
        res = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}).json()
        if 'prompt_id' not in res:
            raise Exception(f"ComfyUI Error: {res}")
        
        prompt_id = res['prompt_id']
        print(f"🚀 Job Submitted. ID: {prompt_id}")

        # 5. Polling Logic (Analogue to Image Gen)
        filename = None
        while not filename:
            hist_res = requests.get(f"{COMFY_URL}/history/{prompt_id}").json()
            
            if prompt_id in hist_res:
                outputs = hist_res[prompt_id].get('outputs', {})
                
                # Search nodes for the 3D output key
                for node_id in outputs:
                    node_output = outputs[node_id]
                    
                    # CHANGE: Look for "3d" instead of "images" or "mesh"
                    if '3d' in node_output:
                        # Grab the exact filename ComfyUI generated (e.g., 3d_mesh_00001_.glb)
                        filename = node_output['3d'][0]['filename']
                        break
                break
            
            time.sleep(2)

        if not filename:
            raise Exception("Workflow finished but no '3d' key found in history.")

        # Construct the final path using the filename found in the history
        full_local_path = os.path.join(COMFY_OUTPUT, filename)
        print(f"✅ Found Mesh: {full_local_path}")

        # Upload to R2 [cite: 25]
        unique_r2_key = f"model_{int(time.time())}.glb"
        r2_url = upload_to_r2(
            full_local_path, 
            unique_r2_key, 
            content_type='model/gltf-binary'
        )

        # 7. Cleanup (Optional: deletes the local file after successful upload)
        if os.path.exists(full_local_path):
            os.remove(full_local_path)
            print(f"🧹 Cleanup: Removed {filename}")

        return {"status": "success", "mesh_url": r2_url}

    except Exception as e:
        print(f"❌ 3D Generation Error: {str(e)}")
        return {"error": str(e)}, 500

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)