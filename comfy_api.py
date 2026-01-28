# comfy_api.py
import json
import requests
import time
import base64
import io
from PIL import Image

class ComfyUIClient:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = "runpod_client"
    
    def get_workflow(self, prompt, seed=None):
        """Create workflow JSON matching your local setup"""
        if seed is None:
            seed = int(time.time() * 1000)
        
        workflow = {
            "9": {
                "inputs": {
                    "filename_prefix": "output/zimg",
                    "images": ["34:8", 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Image"}
            },
            "34": {
                "inputs": {},
                "class_type": "ConditioningConcat",
                "_meta": {"title": "Conditioning (Concat)"}
            },
            "34:33": {
                "inputs": {
                    "conditioning": ["34:27", 0]
                },
                "class_type": "ConditioningZeroOut",
                "_meta": {"title": "ConditioningZeroOut"}
            },
            "34:29": {
                "inputs": {
                    "vae_name": "ae.safetensors"
                },
                "class_type": "VAELoader",
                "_meta": {"title": "Load VAE"}
            },
            "34:8": {
                "inputs": {
                    "samples": ["34:3", 0],
                    "vae": ["34:29", 0]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "34:37": {
                "inputs": {
                    "unet_name": "z-image-turbo-Q8_0.gguf"
                },
                "class_type": "UnetLoaderGGUF",
                "_meta": {"title": "Unet Loader (GGUF)"}
            },
            "34:13": {
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                },
                "class_type": "EmptySD3LatentImage",
                "_meta": {"title": "EmptySD3LatentImage"}
            },
            "34:27": {
                "inputs": {
                    "text": prompt,
                    "clip": ["34:55", 0]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            "34:3": {
                "inputs": {
                    "seed": seed,
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
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "34:55": {
                "inputs": {
                    "clip_name": "Qwen3-4B-Q4_K_M.gguf",
                    "type": "lumina2"
                },
                "class_type": "CLIPLoaderGGUF",
                "_meta": {"title": "CLIPLoader (GGUF)"}
            }
        }
        
        return workflow
    
    def generate_image(self, prompt, seed=None):
        """Generate image using ComfyUI"""
        
        # Get workflow
        workflow = self.get_workflow(prompt, seed)
        
        # Queue prompt
        response = requests.post(
            f"http://{self.server_address}/prompt",
            json={"prompt": workflow}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to queue prompt: {response.text}")
        
        prompt_id = response.json()["prompt_id"]
        print(f"Prompt ID: {prompt_id}")
        
        # Wait for completion
        return self.wait_for_image(prompt_id)
    
    def wait_for_image(self, prompt_id, timeout=60):
        """Wait for image generation to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check history
            response = requests.get(f"http://{self.server_address}/history")
            
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    # Get output
                    outputs = history[prompt_id]["outputs"]
                    
                    for node_id in outputs:
                        if "images" in outputs[node_id]:
                            image_info = outputs[node_id]["images"][0]
                            
                            # Download image
                            image_url = f"http://{self.server_address}/view"
                            params = {
                                "filename": image_info["filename"],
                                "subfolder": image_info.get("subfolder", ""),
                                "type": image_info["type"]
                            }
                            
                            img_response = requests.get(image_url, params=params)
                            
                            if img_response.status_code == 200:
                                # Convert to base64
                                image = Image.open(io.BytesIO(img_response.content))
                                buffered = io.BytesIO()
                                image.save(buffered, format="PNG")
                                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                                
                                return {
                                    "image_base64": img_base64,
                                    "dimensions": f"{image.width}x{image.height}",
                                    "prompt_id": prompt_id
                                }
            
            time.sleep(1)
        
        raise Exception("Generation timeout")