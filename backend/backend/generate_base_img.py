import os
import requests
import base64

from dotenv import load_dotenv
load_dotenv()  # Add this at the top of generate_base_img.py

def generate_base_image(prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
    }
    
    payload = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1024x1024",
        "quality": "high",
        "background": "opaque",
        "n": 1
    }
    
    response = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        image_data = base64.b64decode(data['data'][0]['b64_json'])
        with open('typeface_base.png', 'wb') as f:
            f.write(image_data)
        return 'typeface_base.png'
    else:
        raise Exception(f"Image generation failed: {response.text}")
