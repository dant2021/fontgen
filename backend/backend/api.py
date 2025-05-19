from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import shutil
from pathlib import Path
import uuid
import json
from image_processing import load_and_threshold_image
from svg_generation import trace_bitmap_to_svg_paths
from glyph_segmentation import merge_glyph_paths
from font_generation import create_font_from_glyphs
from font_regen import build_replacement_font, drop_in_replacement
from generate_base_img import generate_base_image
from improve_prompt import generate_prompt
from font_normalization import normalize_glyph_heights
import uvicorn
import datetime
from regenerate_missing_img import generate_missing_glyphs_image

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("debug", exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "Font Generator API is running"}

@app.post("/generate-from-prompt")
async def generate_font_from_prompt(background_tasks: BackgroundTasks, prompt: str = Form(...)):
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create directories for this job
    job_dir = Path(f"uploads/{job_id}")
    output_dir = Path(f"output/{job_id}")
    debug_dir = Path(f"debug/{job_id}")
    
    os.makedirs(job_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(debug_dir, exist_ok=True)

    # Process the prompt in the background
    background_tasks.add_task(
        process_prompt_to_font,
        prompt,
        str(job_dir),
        str(output_dir),
        str(debug_dir),
        job_id
    )
    
    return {
        "job_id": job_id,
        "message": "Font generation started"
    }

def process_prompt_to_font(prompt, job_dir, output_dir, debug_dir, job_id):
    try:
        # Step 1: Improve prompt and generate base image
        output_dir_path = Path(output_dir)
        job_dir_path = Path(job_dir)
        better_prompt, prompt_message = generate_prompt(prompt)
        saved_prompt_path = job_dir_path / "better_prompt.txt"
        with open(saved_prompt_path, "w") as f:
            f.write(better_prompt)
        saved_prompt_message_path = job_dir_path / "prompt_message.txt"
        with open(saved_prompt_message_path, "w") as f:
            f.write(prompt_message)

        base_image_path = generate_base_image(better_prompt)
        
        # Save the generated image to job directory
        
        saved_image_path = job_dir_path / "base_image.png"
        shutil.copy(base_image_path, saved_image_path)
        
        # Step 2: Start font generation
        process_font(
            str(saved_image_path),
            output_dir,
            debug_dir,
            job_id
        )
    except Exception as e:
        print(f"Error processing prompt to font: {e}")
        import traceback
        traceback.print_exc()

@app.post("/generate-font")
async def generate_font(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create directories for this job
    job_dir = Path(f"uploads/{job_id}")
    output_dir = Path(f"output/{job_id}")
    debug_dir = Path(f"debug/{job_id}")
    
    os.makedirs(job_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(debug_dir, exist_ok=True)
    
    # Save the uploaded file
    file_extension = os.path.splitext(file.filename)[1]
    file_path = job_dir / f"base_image{file_extension}"
    print(f"file_path: {file_path}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process the font in the background
    background_tasks.add_task(
        process_font, 
        str(file_path), 
        str(output_dir), 
        str(debug_dir),
        job_id
    )
    
    return {"job_id": job_id, "message": "Font generation started"}

@app.get("/font-status/{job_id}")
async def font_status(job_id: str):
    output_dir = Path(f"output/{job_id}")
    job_dir = Path(f"uploads/{job_id}")
    base_image_path = job_dir / "base_image.png"
    better_prompt_path = job_dir / "better_prompt.txt"    
    missing_glyphs_path = output_dir / "missing_glyphs.json"
    fonts_dir = output_dir / "fonts"
    grid_glyphs_path = output_dir / "grid_glyphs.png"
    regen_status_path = output_dir / "regen_status.json"
    
    result = {
        "status": "processing",
        "info-message": "just got started",
        "available_formats": [],
    }
    
    # Check for regeneration status
    if regen_status_path.exists():
        try:
            with open(regen_status_path, "r") as f:
                regen_data = json.load(f)
                if regen_data.get("status") == "completed":
                    result["regeneration_status"] = "completed"
                    result["regeneration_time"] = regen_data.get("timestamp")
                    result["info-message"] = "Regeneration completed"
                else:
                    result["regeneration_status"] = "in_progress"
                    result["info-message"] = "Regeneration in progress"
        except:
            pass

    if better_prompt_path.exists():
        result["available_formats"].append("better-prompt")
        if "regeneration_status" not in result:
            result["info-message"] = "Prompt improved"

    if base_image_path.exists():
        result["available_formats"].append("base-image")
        if "regeneration_status" not in result:
            result["info-message"] = "Base image generated"

    if grid_glyphs_path.exists():
        result["available_formats"].append("grid-glyphs")
        if "regeneration_status" not in result:
            result["info-message"] = "glyphs split and put into grid"

    if missing_glyphs_path.exists():
        result["available_formats"].append("missing-glyphs")
        if "regeneration_status" not in result:
            result["info-message"] = "Glyphs detected"

    # Check for all weight variants (100-900)
    for weight in range(100, 1000, 100):
        ttf_path = fonts_dir / f"MyFont-{weight}.ttf"
        otf_path = fonts_dir / f"MyFont-{weight}.otf"
        woff2_path = fonts_dir / f"MyFont-{weight}.woff2"
        
        if ttf_path.exists():
            result["available_formats"].append(f"{weight}-ttf")
        if otf_path.exists():
            result["available_formats"].append(f"{weight}-otf")
        if woff2_path.exists():
            result["available_formats"].append(f"{weight}-woff2")
            # Mark as completed when we find a WOFF2 file or regeneration is complete
            if "regeneration_status" not in result or result["regeneration_status"] == "completed":
                result["status"] = "completed"
                result["info-message"] = "Font generated"
    
    return result

@app.get("/download-font/{job_id}/{format}")
async def download_font(job_id: str, format: str):
    output_dir = Path(f"output/{job_id}")
    fonts_dir = output_dir / "fonts"

    if format.lower() == "zipped-fonts":
        font_path = fonts_dir / "MyFont.zip"
        filename = "MyFont.zip"
        if not font_path.exists():
            return {"error": f"File {filename} not found. It may still be processing or failed to generate."}
        return FileResponse(path=str(font_path), filename=filename)

    if format.lower() == "missing-glyphs":
        font_path = output_dir / "missing_glyphs.json"
        filename = "missing_glyphs.json"
        if not font_path.exists():
            return {"error": f"File {filename} not found. It may still be processing or failed to generate."}
        return FileResponse(path=str(font_path), filename=filename)

    # Parse format string (e.g., "400-ttf", "700-otf", "900-woff2")
    try:
        weight, font_format = format.lower().split("-")
        weight = int(weight)
        if weight not in range(100, 1000, 100):
            return {"error": "Invalid weight. Must be between 100 and 900 in steps of 100"}
        if font_format not in ["ttf", "otf", "woff2"]:
            return {"error": "Invalid format. Use 'ttf', 'otf', or 'woff2'"}
        
        font_path = fonts_dir / f"MyFont-{weight}.{font_format}"
        filename = f"MyFont-{weight}.{font_format}"
    except ValueError:
        return {"error": "Invalid format. Use format like '400-ttf', '700-otf', or '900-woff2'"}
    
    # Check if the file exists before trying to serve it
    if not font_path or not font_path.exists():
        return {"error": f"File {filename} not found. It may still be processing or failed to generate."}
    
    return FileResponse(path=str(font_path), filename=filename)

@app.post("/regenerate-glyphs/{job_id}")
async def regenerate_glyphs(
    job_id: str, 
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    chars_to_regenerate: str = Form(...)
):
    """
    Regenerate specific glyphs in an existing font.
    
    - job_id: The ID of the existing font job
    - file: New image containing the glyphs to regenerate
    - chars_to_regenerate: Comma-separated list of characters to regenerate
    """
    # Create directories for this job if they don't exist
    job_dir = Path(f"uploads/{job_id}")
    output_dir = Path(f"output/{job_id}")
    debug_dir = Path(f"debug/{job_id}")
    
    os.makedirs(job_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(debug_dir, exist_ok=True)
    
    # Save the uploaded file with a different name to avoid conflicts
    file_path = job_dir / f"regenerate_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Parse the characters to regenerate
    chars_list = chars_to_regenerate.split(',')
    
    # Process the regeneration in the background
    background_tasks.add_task(
        process_glyph_regeneration,
        str(file_path),
        str(output_dir),
        str(debug_dir),
        job_id,
        chars_list
    )
    
    return {"job_id": job_id, "message": "Glyph regeneration started"}

def process_font(file_path, output_dir, debug_dir, job_id):
    try:
        # Step 1: Load and threshold image
        bitmap = load_and_threshold_image(file_path, debug_dir=debug_dir)
        print("bitmap loaded")
        # Step 2: Trace bitmap to SVG paths
        paths_data, filtered_bboxes = trace_bitmap_to_svg_paths(bitmap, debug_dir=debug_dir)
        print("paths_data, filtered_bboxes loaded")
        # Step 3: Merge glyph components
        merged_paths, merged_bboxes = merge_glyph_paths(paths_data, filtered_bboxes, debug_dir=debug_dir, debug=True)
        print("merged_paths, merged_bboxes loaded")
        # Align & scale glyphs
        transformed_bboxes, transformed_paths, ref_lines, scale = normalize_glyph_heights(merged_bboxes, merged_paths, output_dir, debug_dir=debug_dir)

        print(f"Merged {len(paths_data)} paths into {len(merged_paths)} glyphs")

        print(f"ref_lines: {ref_lines}")
        print(f"scale: {scale}")
        print(f"ref_lines type: {type(ref_lines)}")
        print(f"scale type: {type(scale)}")
        # save ref lines
        ref_lines_path = os.path.join(output_dir, "ref_lines.json")
        with open(ref_lines_path, "w") as f:
            json.dump(ref_lines, f)

        print("save is done")
        # Step 4: Create font from aligned glyphs
        create_font_from_glyphs(transformed_paths, transformed_bboxes, output_dir=output_dir, debug_dir=debug_dir)
    except Exception as e:
        print(f"Error processing font: {e}")
        # You could log this error or create an error file in the output directory

@app.post("/regenerate-missing-glyphs/{job_id}")
async def regenerate_missing_glyphs(
    job_id: str,
    background_tasks: BackgroundTasks,
    chars_to_regenerate: str = Form(None) 
):
    """
    Regenerate missing glyphs for an existing font using AI.
    
    - job_id: The ID of the existing font job
    - chars_to_regenerate: Optional comma-separated list of characters to regenerate
    """
    # Validate job exists
    job_dir = Path(f"uploads/{job_id}")
    output_dir = Path(f"output/{job_id}")
    debug_dir = Path(f"debug/{job_id}")
    
    if not job_dir.exists() or not output_dir.exists():
        return {"error": "Job not found"}
    
    # Mark regeneration as started
    with open(os.path.join(output_dir, "regen_status.json"), "w") as fh:
        json.dump({"status": "started", "timestamp": str(datetime.datetime.now())}, fh)

    # Get base image path
    base_image_path = job_dir / "base_image.png"
    if not base_image_path.exists():
        base_image_path = job_dir / "base_image.jpg"
        if not base_image_path.exists():
            return {"error": "No base image found for this font"}
    
    # Determine characters to regenerate
    if chars_to_regenerate:
        # Use characters from request
        chars_list = chars_to_regenerate.split(',')
    else:
        return {"error": "No missing glyphs found for this font"}
    
    # Start regeneration in background
    background_tasks.add_task(
        process_missing_glyph_regeneration,
        str(base_image_path),
        str(output_dir),
        str(debug_dir),
        job_id,
        chars_list
    )
    
    return {"job_id": job_id, "message": f"Missing glyph regeneration started for: {', '.join(chars_list)}"}

def process_glyph_regeneration(file_path, output_dir, debug_dir, job_id, chars_to_regenerate):
    try:
        # Step 1: Load and threshold image
        bitmap = load_and_threshold_image(file_path, debug_dir=debug_dir)
        
        # Step 2: Trace bitmap to SVG paths
        paths_data, filtered_bboxes = trace_bitmap_to_svg_paths(bitmap, debug_dir=debug_dir)
        
        # Step 3: Merge glyph paths
        merged_paths, merged_bboxes = merge_glyph_paths(paths_data, filtered_bboxes, debug_dir=debug_dir, debug=True)
        
        # Step 4: Align glyphs
        transformed_bboxes, transformed_paths, ref_lines, scale = normalize_glyph_heights(merged_bboxes, merged_paths, output_dir, debug_dir=debug_dir, cluster_centers_passed=True)

        
        # Step 5: Create a temporary directory for the new glyphs
        temp_dir = os.path.join(output_dir, "temp_glyphs")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Step 6: Build the standalone replacement font
        repl_font_path, char_map = build_replacement_font(
            transformed_paths,
            transformed_bboxes,
            chars_to_regenerate,
            temp_dir,
            debug_dir
        )
        
        # Step 7: Merge into the main font + redo tracking / kerning
        drop_in_replacement(output_dir, repl_font_path, char_map)
        
        # Step 8: Book-keeping
        with open(os.path.join(output_dir, "regenerated_glyphs.json"), "w") as fh:
            json.dump({
                "requested": chars_to_regenerate,
                "actually_present": chars_to_regenerate,   # all were forced in
            }, fh)
        
        # Mark regeneration as complete
        with open(os.path.join(output_dir, "regen_status.json"), "w") as fh:
            json.dump({"status": "completed", "timestamp": str(datetime.datetime.now())}, fh)
            
    except Exception as e:
        # Mark regeneration as failed
        with open(os.path.join(output_dir, "regen_status.json"), "w") as fh:
            json.dump({"status": "failed", "error": str(e), "timestamp": str(datetime.datetime.now())}, fh)
            
        print(f"Error during glyph regeneration: {e}")
        import traceback
        traceback.print_exc()
        # Save error information
        error_path = os.path.join(output_dir, "regeneration_error.json")
        with open(error_path, 'w') as f:
            json.dump({"error": str(e)}, f)

@app.post("/regenerate-missing-glyphs/{job_id}")
async def regenerate_missing_glyphs(
    job_id: str,
    background_tasks: BackgroundTasks,
    chars_to_regenerate: str = Form(None)  # Optional - can use missing_glyphs.json if not provided
):
    """
    Regenerate missing glyphs for an existing font using AI.
    
    - job_id: The ID of the existing font job
    - chars_to_regenerate: Optional comma-separated list of characters to regenerate
    """
    # Validate job exists
    job_dir = Path(f"uploads/{job_id}")
    output_dir = Path(f"output/{job_id}")
    debug_dir = Path(f"debug/{job_id}")
    
    if not job_dir.exists() or not output_dir.exists():
        return {"error": "Job not found"}
    
    # Get base image path
    base_image_path = job_dir / "base_image.png"
    
    # Determine characters to regenerate
    if chars_to_regenerate:
        # Use characters from request
        chars_list = chars_to_regenerate.split(',')
    else:
        # Use characters from missing_glyphs.json
        missing_glyphs_path = output_dir / "missing_glyphs.json"
        if not missing_glyphs_path.exists():
            return {"error": "No missing glyphs found for this font"}
        
        with open(missing_glyphs_path, "r") as f:
            chars_list = json.load(f)
    
    # Start regeneration in background
    background_tasks.add_task(
        process_missing_glyph_regeneration,
        str(base_image_path),
        str(output_dir),
        str(debug_dir),
        job_id,
        chars_list
    )
    
    return {"job_id": job_id, "message": f"Missing glyph regeneration started for: {', '.join(chars_list)}"}

def process_missing_glyph_regeneration(base_image_path, output_dir, debug_dir, job_id, chars_to_regenerate):
    try:
        # Generate new image with missing glyphs
        regen_image_path = generate_missing_glyphs_image(
            chars_to_regenerate,
            job_id,
            base_image_path
        )
        
        # Process the new image
        bitmap = load_and_threshold_image(regen_image_path, debug_dir=debug_dir)
        paths_data, filtered_bboxes = trace_bitmap_to_svg_paths(bitmap, debug_dir=debug_dir)
        merged_paths, merged_bboxes = merge_glyph_paths(paths_data, filtered_bboxes, debug_dir=debug_dir, debug=True)
        transformed_bboxes, transformed_paths, ref_lines, scale = normalize_glyph_heights(merged_bboxes, merged_paths, output_dir, debug_dir=debug_dir, cluster_centers_passed=True)

        
        # Create temporary directory for the new glyphs
        temp_dir = os.path.join(output_dir, "temp_glyphs")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Build replacement font with new glyphs
        repl_font_path, char_map = build_replacement_font(
            transformed_paths,
            transformed_bboxes,
            chars_to_regenerate,
            temp_dir,
            debug_dir
        )
        
        # Merge into main font
        drop_in_replacement(output_dir, repl_font_path, char_map)
        
        # Update status
        with open(os.path.join(output_dir, "regenerated_glyphs.json"), "w") as fh:
            json.dump({
                "requested": chars_to_regenerate,
                "regeneration_timestamp": str(datetime.datetime.now()),
                "status": "completed"
            }, fh)
            
    except Exception as e:
        print(f"Error during missing glyph regeneration: {e}")
        import traceback
        traceback.print_exc()
        error_path = os.path.join(output_dir, "regeneration_error.json")
        with open(error_path, 'w') as f:
            json.dump({"error": str(e)}, f)

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000))) 