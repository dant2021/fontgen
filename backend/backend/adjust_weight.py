import fontforge
import os
import shutil
import zipfile
from adjust_tracking import tracking_font

def create_weight_variant(base_font_path, output_dir, variant_name, weight_delta, counter_type="retain"):
    # Open the base font
    base_font = fontforge.open(base_font_path)
    
    # Modify the base font
    base_font.fontname = base_font.fontname + f"-{variant_name}"
    base_font.fullname = base_font.fullname + f" {variant_name}"
    base_font.weight = variant_name
    
    # Select all glyphs
    base_font.selection.all()
    
    # Adjust the stroke weight
    base_font.changeWeight(weight_delta, "LCG", 0, 0, counter_type)
    base_font, target_spacing = tracking_font(base_font, modified_spacing=abs(weight_delta))

    print(f"target_spacing: {target_spacing}")
    # Generate the variant font files
    os.makedirs(output_dir, exist_ok=True)
    base_font.generate(os.path.join(output_dir, f"MyFont-{variant_name}.ttf"))
    base_font.generate(os.path.join(output_dir, f"MyFont-{variant_name}.otf"))
    base_font.generate(os.path.join(output_dir, f"MyFont-{variant_name}.woff2"))
    base_font.close()

def create_all_variants(base_font_path, output_dir, bold_delta=32, light_delta=-32, regular=0):
    """
    Create all weight variants from 100 to 900.
    
    Args:
        base_font_path: Path to the base font file
        output_dir: Directory to save the variants
        bold_delta: Weight delta for bold variant (default 32)
        light_delta: Weight delta for light variant (default -32)
    """
    # Standard weight values from 100 to 900
    weights = range(100, 1000, 100)
    
    # Create a single zip file
    zip_file = os.path.join(output_dir, "MyFont.zip")
    
    for weight in weights:
        # Calculate the interpolation factor (0.0 to 1.0)
        factor = (weight - 100) / 800.0  # 800 is the range between 100 and 900
        
        # Interpolate between light and bold deltas
        weight_delta = light_delta + (bold_delta - light_delta) * factor
        weight_delta = weight_delta + regular
        weight_delta = round(weight_delta)
        print(f"weight_delta: {weight_delta}")

        if weight_delta == 0:
            # For weight_delta 0, we need to properly generate each format
            base_font = fontforge.open(base_font_path)
            base_font.fontname = base_font.fontname + f"-{weight}"
            base_font.fullname = base_font.fullname + f" {weight}"
            base_font.weight = str(weight)
            
            # Generate all formats
            base_font.generate(os.path.join(output_dir, f"MyFont-{weight}.ttf"))
            base_font.generate(os.path.join(output_dir, f"MyFont-{weight}.otf"))
            base_font.generate(os.path.join(output_dir, f"MyFont-{weight}.woff2"))
            base_font.close()
        else:
            # Create the weight variant
            create_weight_variant(base_font_path, output_dir, str(weight), weight_delta)
    
    # Add all files to a single zip file
    with zipfile.ZipFile(zip_file, 'w') as zipf:
        for weight in weights:
            for ext in ["ttf", "otf", "woff2"]:
                font_file = os.path.join(output_dir, f"MyFont-{weight}.{ext}")
                if os.path.exists(font_file):
                    zipf.write(font_file, arcname=os.path.basename(font_file))

if __name__ == "__main__":
    # Example usage
    base_font = "output/MyFont.otf"
    output_dir = "output"
    
    # Create all weight variants
    create_all_variants(base_font, output_dir)