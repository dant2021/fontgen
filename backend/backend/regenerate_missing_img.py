# regenerate_missing_img.py
import argparse
import os
import base64
from typing import List
from openai import OpenAI
from PIL import Image
from dotenv import load_dotenv
from make_regen_image import generate_glyph_images

load_dotenv()  # Load environment variables

def generate_missing_glyphs_image(missing_glyphs: List[str], job_id: str, base_image_path: str = None):
    """Generate extended image with missing glyphs"""
    # Create output directories

    job_dir = f"uploads/{job_id}"
    os.makedirs(job_dir, exist_ok=True)

    output_dir = f"output/{job_id}"

    font_path = f"{output_dir}/MyFont.otf"

    missing_glyphs_path = generate_glyph_images(font_path, job_dir, missing_glyphs, image_size=100, max_width=1024, max_height=1024)

    base_image_path = missing_glyphs_path



    if base_image_path is None:
        base_image_path = "job_dir/base_image.png"
    
    # Load base image
    base_img = Image.open(base_image_path)
    width, height = base_img.size

    missing_chars_str = ", ".join([f"{char}" for char in missing_glyphs])
    prompt = generate_regeneration_prompt(job_dir, missing_chars_str)
    print(f"Prompt: {prompt}")
    
    # Use edit API with mask
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    try:
        response = client.images.edit(
            model="gpt-image-1",
            image=open(base_image_path, "rb"),
            prompt=prompt,
            size="1024x1024"
        )
        
        # Save result
        image_data = base64.b64decode(response.data[0].b64_json)
        output_path = os.path.join(job_dir, "regenerated_glyphs.png")
        
        with open(output_path, 'wb') as f:
            f.write(image_data)
        
        # Save prompt for debugging
        with open(os.path.join(job_dir, "regeneration_prompt.txt"), 'w') as f:
            f.write(prompt)
        
        return output_path
        
    except Exception as e:
        error_msg = f"Image generation failed: {str(e)}"
        print(error_msg)
        with open(os.path.join(job_dir, "regeneration_error.txt"), 'w') as f:
            f.write(error_msg)
        raise Exception(error_msg)
    
def generate_regeneration_prompt(job_dir: str, missing_glyphs: str) -> str:
    """Generate a prompt for regenerating specific characters.
    
    Args:
        job_dir (str): The directory of the job
        missing_glyphs (str): String of characters to regenerate
        
    Returns:
        str: A detailed prompt for character regeneration
    """
    # Enhance the user's input using AI
    enhanced_path = os.path.join(job_dir, "better_prompt.txt")
    with open(enhanced_path, "r") as f:
        enhanced_style = f.read()

    print(f"Enhanced style: {enhanced_style}")
    prompt = (
        f"""A high-resolution 2D digital graphic extending an existing typeface by regenerating the following missing glyphs: {missing_glyphs}. 
        The new characters must match the original font style exactly: {enhanced_style} 
        Place the regenerated characters in the transparent lower portion of the image, arranged in a neat, evenly spaced grid with consistent rows and aligned baselines. 
        Ensure every specified character is present, clearly legible, and visually harmonious with the existing glyphs above. 
        Maintain consistent stroke weight, proportions, and design details to ensure seamless integration into the original typeface."""
    )
    return f"{prompt}"
    
if __name__ == "__main__":
    generate_missing_glyphs_image(
        "A font with a modern, clean look, featuring a bold and geometric sans-serif style.",
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        "test_job",
        "/workspaces/font-gen/back_end/typeface_base.png"
    )
