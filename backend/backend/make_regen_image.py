#!/usr/bin/env python3
import fontforge
import os
import argparse
from PIL import Image, ImageDraw, ImageFont
import string

def generate_glyph_images(font_path, output_dir="glyph_images", forced_missing_glyphs=None, image_size=100, max_width=1000, max_height=1000):
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Generating glyph images for {font_path}")
    font = fontforge.open(font_path)
    
    # Expanded character set with additional symbols
    expected_chars = list(
        string.ascii_letters + string.digits + string.punctuation
    )
    print(expected_chars)
    # Collect metrics for proper sizing
    font_em = font.em
    missing_chars = set(expected_chars)
    
    # Add forced missing glyphs to the missing set
    if forced_missing_glyphs:
        # Make sure any forced missing glyphs are in the expected chars
        for char in forced_missing_glyphs:
            if char not in expected_chars:
                expected_chars.append(char)
        # Add all forced missing glyphs to missing_chars
        missing_chars.update(forced_missing_glyphs)
        
    char_to_image = {}
    
    # Create temporary directory for processing
    temp_dir = os.path.join(output_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Collect all glyph images in memory
    for glyph in font.glyphs():
        if glyph.isWorthOutputting() and glyph.unicode > 31:
            try:
                char = chr(glyph.unicode)
                # Only remove from missing_chars if it's not in forced_missing_glyphs
                if char in missing_chars and (not forced_missing_glyphs or char not in forced_missing_glyphs):
                    missing_chars.remove(char)
                
                # Skip if this is a forced missing glyph
                if forced_missing_glyphs and char in forced_missing_glyphs:
                    continue
                    
                # Export with transparent background
                temp_file = os.path.join(temp_dir, f"temp_U+{glyph.unicode:04X}.png")
                glyph.export(temp_file, 
                           pixelsize=image_size,
                           background=0,  # Transparent background
                           flags=('antialias', 'dontcorrect'))
                
                # Open image and ensure transparency
                img = Image.open(temp_file).convert("RGBA")
                
                # Remove white pixels (only keep non-white areas)
                datas = img.getdata()
                new_data = []
                for item in datas:
                    # Change white (and near-white) pixels to transparent
                    if item[0] > 240 and item[1] > 240 and item[2] > 240:
                        new_data.append((0, 0, 0, 0))
                    else:
                        new_data.append(item)
                img.putdata(new_data)
                
                char_to_image[char] = img

            except Exception as e:
                print(f"Error exporting glyph U+{glyph.unicode:04X}: {str(e)}")

    # Create missing character markers with X and character label
    for char in missing_chars:
        img = Image.new('RGBA', (image_size, image_size), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        # Dotted border
        dash_length = 4
        for i in range(0, image_size, dash_length*2):
            draw.line([(i, 0), (i+dash_length, 0)], fill=(255,0,0,255), width=2)
            draw.line([(i, image_size-1), (i+dash_length, image_size-1)], fill=(255,0,0,255), width=2)
            draw.line([(0, i), (0, i+dash_length)], fill=(255,0,0,255), width=2)
            draw.line([(image_size-1, i), (image_size-1, i+dash_length)], fill=(255,0,0,255), width=2)
        
        # Red X
        draw.line([(10, 10), (image_size-10, image_size-10)], fill=(255,0,0,255), width=3)
        draw.line([(image_size-10, 10), (10, image_size-10)], fill=(255,0,0,255), width=3)
        
        # Missing character text with fallback
        font_size = 80

        font = ImageFont.load_default(font_size)
 
        
        # Center text both vertically and horizontally
        text_x = image_size // 2
        text_y = image_size // 2
        draw.text((text_x, text_y), char, fill=(255,0,0,255), 
                anchor="mm", font=font, stroke_width=2, stroke_fill=(0,0,0,255))
        
        char_to_image[char] = img
    
    print(f"\nMissing characters needing regeneration ({len(missing_chars)}):")
    print(' '.join([f"[{c}]" for c in sorted(missing_chars)]) + '\n')

    # Get images in expected order
    images = [char_to_image[char] for char in expected_chars if char in char_to_image]
    
    # Clean up temporary directory
    for file in os.listdir(temp_dir):
        try:
            os.remove(os.path.join(temp_dir, file))
        except:
            pass
    try:
        os.rmdir(temp_dir)
    except:
        pass

    if not images:
        print("No glyphs found to export")
        return

    # Calculate grid dimensions
    columns = max(1, max_width // image_size)
    rows = (len(images) + columns - 1) // columns  # Ceiling division
    
    # Adjust dimensions to fit height constraint
    if rows * image_size > max_height:
        # Recalculate to fit within height constraint
        rows = max(1, max_height // image_size)
        columns = (len(images) + rows - 1) // rows  # Ceiling division
        
    composite_width = min(columns * image_size, max_width)
    composite_height = min(rows * image_size, max_height)

    # Calculate actual grid dimensions based on final composite size
    actual_columns = composite_width // image_size
    actual_rows = composite_height // image_size

    # Create composite image with transparent background
    composite = Image.new('RGBA', (composite_width, composite_height), (255,255,255,255))
    
    # Paste glyphs into grid
    for i, img in enumerate(images):
        if i >= actual_columns * actual_rows:
            break
        
        row = i // actual_columns
        col = i % actual_columns
        x = col * image_size
        y = row * image_size
        
        # Paste with full transparency
        composite.alpha_composite(img, dest=(x, y + (image_size - img.height)//2))

    # Save final image
    output_path = os.path.join(output_dir, "missing_glyphs.png")
    composite.save(output_path)
    print(f"Saved composite image to {output_path}")

    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate composite glyph image from a font file')
    parser.add_argument('font_path', help='Path to the font file')
    parser.add_argument('-o', '--output', default="glyph_images", help='Output directory')
    parser.add_argument('-s', '--size', type=int, default=100, 
                       help='Size of each glyph image in pixels')
    parser.add_argument('-w', '--width', type=int, default=1024,
                       help='Maximum width of composite image')
    parser.add_argument('-ht', '--height', type=int, default=1024,
                       help='Target maximum height of composite image')
    
    args = parser.parse_args()
    
    generate_glyph_images(args.font_path, args.output, args.size, args.width, args.height)
