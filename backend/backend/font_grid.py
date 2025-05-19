import os
import math
from PIL import Image, ImageDraw, ImageFont
import cairosvg
from io import BytesIO

# Configuration
GRID_WIDTH = 1024
CELL_SIZE = 78  # 1024px / 13 columns
GLYPH_SCALE = 0.8  # Use 80% of cell space
BACKGROUND_COLOR = "#FFFFFF"
TEXT_COLOR = "#000000"
CATEGORY_SPACING = 20
FONT_PATH = "arial.ttf"  # Fallback font for error messages

def generate_font_grid(svg_dir, output_path):
    # Organize glyphs into categories
    categories = {
        "uppercase": [],
        "lowercase": [],
        "numbers": [],
        "symbols": []
    }

    # Load and categorize SVG files
    for filename in os.listdir(svg_dir):
        if not filename.endswith(".svg"):
            continue
        
        char_code = os.path.splitext(filename)[0]
        category = determine_category(char_code)
        if category:
            categories[category].append((char_code, filename))

    # Sort characters appropriately
    categories["uppercase"].sort(key=lambda x: x[0])
    categories["lowercase"].sort(key=lambda x: x[0])
    categories["numbers"].sort(key=lambda x: x[0])
    categories["symbols"].sort(key=symbol_sort_key)

    # Create image canvas
    total_rows = calculate_total_rows(categories)
    image_height = (total_rows * CELL_SIZE) + ((total_rows - 1) * CATEGORY_SPACING)
    grid_image = Image.new("RGB", (GRID_WIDTH, image_height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(grid_image)

    y_offset = 0
    for category, chars in categories.items():
        if not chars:
            continue
            
        # Split into rows of 13 characters
        for i in range(0, len(chars), 13):
            row_chars = chars[i:i+13]
            x_offset = 0
            
            for char_code, filename in row_chars:
                try:
                    # Render SVG with Cairo
                    svg_path = os.path.join(svg_dir, filename)
                    png_buffer = BytesIO()
                    cairosvg.svg2png(url=svg_path, write_to=png_buffer,
                                    output_width=CELL_SIZE*GLYPH_SCALE,
                                    output_height=CELL_SIZE*GLYPH_SCALE)
                    
                    glyph = Image.open(png_buffer).convert("RGBA")
                    paste_position = (
                        x_offset + int((CELL_SIZE - glyph.width)/2),
                        y_offset + int((CELL_SIZE - glyph.height)/2)
                    )
                    grid_image.paste(glyph, paste_position, glyph)
                except Exception as e:
                    # Create error placeholder
                    error_placeholder = create_error_placeholder(char_code)
                    grid_image.paste(error_placeholder, (x_offset, y_offset))
                
                x_offset += CELL_SIZE
            
            y_offset += CELL_SIZE + CATEGORY_SPACING

    grid_image.save(output_path, "PNG", dpi=(300, 300))

def determine_category(char_code):
    if char_code.isupper():
        return "uppercase"
    if char_code.islower():
        return "lowercase"
    if char_code.isdigit():
        return "numbers"
    return "symbols"

def symbol_sort_key(item):
    symbol_order = ["!", "?", "@", "#", "$", "%", "&", ",", ".", ":"]
    return symbol_order.index(item[0]) if item[0] in symbol_order else len(symbol_order)

def create_error_placeholder(char_code):
    img = Image.new("RGB", (CELL_SIZE, CELL_SIZE), "#FF0000")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, 12)
    except IOError:
        font = ImageFont.load_default()
    
    text_width, text_height = draw.textsize(char_code, font=font)
    position = (
        (CELL_SIZE - text_width) // 2,
        (CELL_SIZE - text_height) // 2
    )
    draw.text(position, char_code, fill=TEXT_COLOR, font=font)
    return img

def calculate_total_rows(categories):
    rows = 0
    for category, chars in categories.items():
        rows += math.ceil(len(chars) / 13)
    return rows 