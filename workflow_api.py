# workflow_api.py - ComfyUI API Integration
import json
import base64
import time
import requests
from PIL import Image
import io

class ComfyUIAPI:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
    
    def generate_image(self, prompt, workflow_template=None, seed=None):
        """Generate image using ComfyUI API"""
        
        if workflow_template is None:
            # Use your workflow template
            workflow_template = {
                "9": {
                    "inputs": {"filename_prefix": "output/zimg", "images": ["34:8", 0]},
                    "class_type": "SaveImage"
                },
                "34:33": {
                    "inputs": {"conditioning": ["34:27", 0]},
                    "class_type": "ConditioningZeroOut"
                },
                "34:29": {
                    "inputs": {"vae_name": "ae.safetensors"},
                    "class_type": "VAELoader"
                },
                "34:8": {
                    "inputs": {"samples": ["34:3", 0], "vae": ["34:29", 0]},
                    "class_type": "VAEDecode"
                },
                "34:37": {
                    "inputs": {"unet_name": "z-image-turbo-Q8_0.gguf"},
                    "class_type": "UnetLoaderGGUF"
                },
                "34:13": {
                    "inputs": {"width": 512, "height": 512, "batch_size": 1},
                    "class_type": "EmptySD3LatentImage"
                },
                "34:27": {
                    "inputs": {"text": prompt, "clip": ["34:55", 0]},
                    "class_type": "CLIPTextEncode"
                },
                "34:3": {
                    "inputs": {
                        "seed": seed if seed else int(time.time() * 1000),
                        "steps": 8,
                        "cfg": 1,
                        "sampler_name": "res_multistep",
                        "scheduler": "simple",
                        "denoise": 1,
                        "model": ["34:37", 0],
                        "positive": ["34:27", 0],
                        "negative": ["34:33", 0],
                        "latent_image": ["34:13", 0]
                    },
                    "class_type": "KSampler"
                },
                "34:55": {
                    "inputs": {"clip_name": "Qwen3-4B-Q4_K_M.gguf", "type": "lumina2"},
                    "class_type": "CLIPLoaderGGUF"
                }
            }
        
        # Queue the prompt
        response = requests.post(
            f"http://{self.server_address}/prompt",
            json={"prompt": workflow_template}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to queue prompt: {response.text}")
        
        prompt_id = response.json()["prompt_id"]
        print(f"✅ Prompt queued with ID: {prompt_id}")
        
        # Wait for completion
        image_data = self.wait_for_completion(prompt_id)
        
        return image_data
    
    def wait_for_completion(self, prompt_id, timeout=300):
        """Wait for image generation to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check history
            response = requests.get(f"http://{self.server_address}/history/{prompt_id}")
            
            if response.status_code == 200 and response.json():
                history = response.json()
                if prompt_id in history:
                    # Get output images
                    outputs = history[prompt_id]["outputs"]
                    
                    for node_id in outputs:
                        if "images" in outputs[node_id]:
                            image_info = outputs[node_id]["images"][0]
                            # Download image
                            image_response = requests.get(
                                f"http://{self.server_address}/view?filename={image_info['filename']}&subfolder={image_info['subfolder']}&type={image_info['type']}"
                            )
                            
                            if image_response.status_code == 200:
                                # Convert to base64
                                img = Image.open(io.BytesIO(image_response.content))
                                buffered = io.BytesIO()
                                img.save(buffered, format="PNG")
                                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                                
                                return {
                                    "image_base64": img_base64,
                                    "dimensions": f"{img.width}x{img.height}",
                                    "prompt_id": prompt_id
                                }
            
            time.sleep(1)
        
        raise Exception("Generation timeout")