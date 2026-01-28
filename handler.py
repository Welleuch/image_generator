# handler.py
import runpod
from comfy_api import ComfyUIClient
import time

print("=" * 60)
print("🚀 COMFYUI IMAGE GENERATION ENDPOINT")
print("Model: z-image-turbo (8 steps, cfg=1)")
print("=" * 60)

# Initialize ComfyUI client
comfy = ComfyUIClient("127.0.0.1:8188")

def handler(job):
    """Main handler function"""
    print(f"\n🎯 Received image generation job")
    
    try:
        input_data = job["input"]
        prompt = input_data.get("prompt", "").strip()
        
        if not prompt:
            return {"error": "No prompt provided"}
        
        # Optional parameters
        seed = input_data.get("seed")
        if seed:
            seed = int(seed)
        
        print(f"📝 Prompt: {prompt[:100]}...")
        if seed:
            print(f"🌱 Seed: {seed}")
        
        # Generate image
        start_time = time.time()
        result = comfy.generate_image(prompt, seed)
        generation_time = time.time() - start_time
        
        print(f"✅ Image generated in {generation_time:.2f} seconds")
        
        return {
            "status": "success",
            "image_base64": result["image_base64"],
            "dimensions": result["dimensions"],
            "generation_time": f"{generation_time:.2f}s",
            "model": "z-image-turbo",
            "steps": 8,
            "cfg": 1
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

print("\n🏁 ComfyUI Image Generator Ready!")
print("Using your exact workflow: z-image-turbo, 8 steps, cfg=1")
runpod.serverless.start({"handler": handler})