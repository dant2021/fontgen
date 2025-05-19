import os
import json
import fontforge
from lxml import etree
from ocr_utils import extract_chars
from adjust_kerning import optimize_kerning
from adjust_weight import create_all_variants
from adjust_tracking import tracking_font

def create_font_from_glyphs(aligned_paths, aligned_bboxes, output_dir, debug_dir=None):
    # Save merged SVG
    svg_content = '<svg xmlns="http://www.w3.org/2000/svg">\n'
    for aligned_path in aligned_paths:
        svg_content += f'<path d="{aligned_path}" fill="black" fill-rule="evenodd" />\n'
    svg_content += '</svg>'

    svg_path = os.path.join(output_dir, "font.svg")
    with open(svg_path, "w") as f:
        f.write(svg_content)

    # Extract glyphs
    glyphs_dir = os.path.join(output_dir, "glyphs")
    os.makedirs(glyphs_dir, exist_ok=True)

    tree = etree.fromstring(svg_content.encode())
    paths = tree.findall(".//{http://www.w3.org/2000/svg}path")

    for i, path in enumerate(paths):
        glyph_svg = f"""<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" 
  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="http://www.w3.org/2000/svg" version="1.1">
<path d="{path.get('d')}" fill="black" fill-rule="evenodd" />
</svg>"""
        glyph_path = os.path.join(glyphs_dir, f"glyph_{i}.svg")
        with open(glyph_path, "w") as f:
            f.write(glyph_svg)

    # Use OCR to identify characters
    map_clusters_to_chars = extract_chars(glyphs_dir)
    
    # Use the filtered glyphs directory for font generation
    filtered_dir = os.path.join(output_dir, "filtered_glyphs")
    os.makedirs(filtered_dir, exist_ok=True)  # Make sure this directory exists
    
    # Create font
    font = fontforge.font()
    font.familyname = "MyFont"
    font.fontname = "MyFont"
    font.fullname = "MyFont"
    font.ascent = 800
    font.descent = 200
    font.em = 1000

    # Track which characters were successfully processed
    processed_chars = set()
    
    # Import glyphs and analyze bounding boxes
    char_bboxes = {}
    for char in map_clusters_to_chars.values():
        # Look for both upper and lower case versions
        case_indicator = "upper" if char.isupper() else "lower"
        svg_file = os.path.join(filtered_dir, f"{char}_{case_indicator}.svg")
        if not os.path.exists(svg_file):
            continue
        # Create glyph with proper Unicode code point
        glyph = font.createChar(ord(char))
        glyph.importOutlines(svg_file)
        glyph.correctDirection()
        glyph.removeOverlap()
        #glyph.simplify()
        bbox = glyph.boundingBox()
        char_bboxes[char] = bbox
        processed_chars.add(char)

    # Determine missing glyphs
    standard_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:!?@#$%&"
    missing_glyphs = [char for char in standard_chars if char not in processed_chars]
    
    # Save missing glyphs to a JSON file

    missing_glyphs_path = os.path.join(output_dir, "missing_glyphs.json")
    with open(missing_glyphs_path, 'w') as f:
        json.dump(missing_glyphs, f)

    # Compute descender threshold
    bottoms = [bbox[1] for bbox in char_bboxes.values()]
    sorted_bottoms = sorted(bottoms)
    if len(sorted_bottoms) >= 4:
        q1 = sorted_bottoms[len(sorted_bottoms) // 4]
        q3 = sorted_bottoms[3 * len(sorted_bottoms) // 4]
        iqr = q3 - q1
        descender_threshold = q1 - 1.5 * iqr
    else:
        avg_bottom = sum(bottoms) / len(bottoms)
        max_height = max(bbox[3] - bbox[1] for bbox in char_bboxes.values())
        descender_threshold = avg_bottom - 0.25 * max_height

    descender_chars = [c for c, bbox in char_bboxes.items() if bbox[1] < descender_threshold]

    # Scale and align glyphs
    max_height = max(bbox[3] - bbox[1] for bbox in char_bboxes.values())
    scale_factor = 800 / max_height

    for char, bbox in char_bboxes.items():
        glyph = font[ord(char)]
        glyph.transform((scale_factor, 0, 0, scale_factor, 0, 0))
        bbox = glyph.boundingBox()

        if char in descender_chars:
            avg_bottom = sum(bbox[1] for bbox in char_bboxes.values()) / len(char_bboxes)
            adjustment = (bbox[1] - avg_bottom*scale_factor)*1.25
            y_shift = - bbox[1] + adjustment
        else:
            y_shift = 0 - bbox[1] 
        
        x_shift = - bbox[0]
        #x_shift = target_spacing/2 - bbox[0]
        glyph.transform((1, 0, 0, 1, x_shift, y_shift))

        glyph.width = int((bbox[2] - bbox[0]))
        glyph.autoHint()

    # Adjust tracking
    font, target_spacing = tracking_font(font, map_clusters_to_chars)
    # Adjust kerning
    optimize_kerning(font, target_spacing)

    # Save font
    font.generate(os.path.join(output_dir, "MyFont.otf"))
    print("Font generated at", output_dir)

    # weight variants
    create_all_variants(os.path.join(output_dir, "MyFont.otf"), output_dir+"/fonts", bold_delta=32, light_delta=-32, regular=0)

    print("Font generation completed")