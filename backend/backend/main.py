import os
import numpy as np
import json
from image_processing import load_and_threshold_image
from svg_generation import trace_bitmap_to_svg_paths
from glyph_segmentation import merge_glyph_paths
from font_generation import create_font_from_glyphs
#from glyph_alignment import align_glyphs
from font_normalization import normalize_glyph_heights

def main():
    input_image_path = "data/need_speed.png"
    #input_image_path = "uploads/playful_font/base_image.png"
    #input_image_path = "uploads/elegant_font/regenerated_glyphs.png"
    debug_dir = "debug"
    os.makedirs(debug_dir, exist_ok=True)
    os.makedirs("output", exist_ok=True)

    # Step 1: Load and threshold image
    bitmap = load_and_threshold_image(input_image_path, debug_dir=debug_dir)

    # Step 2: Trace bitmap to SVG paths
    paths_data, filtered_bboxes = trace_bitmap_to_svg_paths(bitmap, debug_dir=debug_dir)

    # Step 3: Merge glyph components
    merged_paths, merged_bboxes = merge_glyph_paths(paths_data, filtered_bboxes, debug_dir=debug_dir, debug=True)

    # Align glyphs closer to origin
    #aligned_paths, aligned_bboxes = align_glyphs(merged_paths, merged_bboxes)
    # Example usage:
    transformed_bboxes, transformed_paths, ref_lines, scale = normalize_glyph_heights(
    merged_bboxes,
    merged_paths,
    debug_dir=debug_dir)

    print(f"Merged {len(paths_data)} paths into {len(merged_paths)} glyphs")
    # save ref lines
    with open("output/ref_lines.json", "w") as f:
        json.dump(ref_lines, f)


    # Step 4: Create font from aligned glyphs
    create_font_from_glyphs(transformed_paths, transformed_bboxes, output_dir="output", debug_dir=debug_dir)
    #create_font_from_glyphs(aligned_paths, aligned_bboxes, output_dir="output", debug_dir=debug_dir)

if __name__ == "__main__":
    main()