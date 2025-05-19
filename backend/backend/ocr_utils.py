import os
import re
import cairosvg
import xml.etree.ElementTree as ET
import base64
from openai import OpenAI
import shutil
import cairosvg
import numpy as np

def filter_noise_glyphs(glyphs_dir, min_size_ratio=0.25):
    """Filter out noise glyphs that are significantly smaller than the average glyph."""
    # Get list of all SVG files
    svg_files = sorted(f for f in os.listdir(glyphs_dir) if f.endswith('.svg'))
    
    # Calculate size of each glyph
    glyph_sizes = {}
    
    for svg_filename in svg_files:
        # Extract glyph index
        base_name = os.path.splitext(svg_filename)[0]
        if base_name.startswith('glyph_'):
            try:
                idx = int(base_name.split('_')[1])
            except ValueError:
                continue
        else:
            try:
                idx = int(base_name)
            except ValueError:
                continue
        
        svg_path = os.path.join(glyphs_dir, svg_filename)
        
        # Parse SVG
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            path_elem = root.find('.//{http://www.w3.org/2000/svg}path')
            if path_elem is None:
                continue
                
            d = path_elem.attrib['d']
            coords = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", d)))
            
            if len(coords) < 4:
                continue
                
            xs = coords[::2]
            ys = coords[1::2]
            
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            area = width * height
            
            glyph_sizes[idx] = area
            
        except Exception as e:
            print(f"Error processing {svg_filename}: {e}")
    
    # Calculate average size
    if not glyph_sizes:
        return [], []
        
    avg_size = sum(glyph_sizes.values()) / len(glyph_sizes)
    
    # Filter glyphs based on size
    keep_glyphs = [idx for idx, size in glyph_sizes.items() if size >= min_size_ratio * avg_size]
    noise_glyphs = [idx for idx, size in glyph_sizes.items() if size < min_size_ratio * avg_size]
    
    print(f"Keeping {len(keep_glyphs)} glyphs, filtering out {len(noise_glyphs)} noise glyphs")
    
    return keep_glyphs, noise_glyphs

def extract_chars(glyphs_dir, api_key=None):
    """Extract characters from glyphs using a vision model."""
    # Get API key from environment variable if not provided
    if not api_key:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        print(f"Retrieved API key from environment: {'Found key' if api_key else 'No key found'}")
        if not api_key:
            print("Error: OPENROUTER_API_KEY environment variable not set")
            return {}
    
    # Initialize OpenAI client
    try:
        print("Initializing OpenAI client...")
        # Create a clean dictionary of kwargs to avoid any unexpected parameters
        client_kwargs = {
            "api_key": api_key,
            "base_url": "https://openrouter.ai/api/v1"
        }
        client = OpenAI(**client_kwargs)
        print("OpenAI client initialized successfully")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return {}
    
    # Create output directory
    output_dir = os.path.dirname(glyphs_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Filter out noise glyphs
    keep_glyphs, noise_glyphs = filter_noise_glyphs(glyphs_dir)
    if not keep_glyphs:
        print("No valid glyphs found after filtering")
        return {}
    
    # Create a mapping from original glyph indices to new sequential indices
    original_to_new = {orig_idx: new_idx for new_idx, orig_idx in enumerate(sorted(keep_glyphs))}
    new_to_original = {new_idx: orig_idx for orig_idx, new_idx in original_to_new.items()}
    
    # Save the mapping for later use
    with open(os.path.join(output_dir, "glyph_mapping.txt"), "w") as f:
        f.write("New_Index\tOriginal_Index\n")
        for new_idx, orig_idx in new_to_original.items():
            f.write(f"{new_idx}\t{orig_idx}\n")
    
    # Create a directory for filtered glyphs with new sequential numbering
    filtered_dir = os.path.join(output_dir, "filtered_glyphs")
    os.makedirs(filtered_dir, exist_ok=True)
    
    # Copy kept glyphs to filtered directory with new sequential numbering
    for orig_idx in keep_glyphs:
        new_idx = original_to_new[orig_idx]
        orig_path = os.path.join(glyphs_dir, f"glyph_{orig_idx}.svg")
        new_path = os.path.join(filtered_dir, f"glyph_{new_idx}.svg")
        if os.path.exists(orig_path):
            shutil.copy2(orig_path, new_path)
    
    # Analyze glyph bounding boxes using the new indices
    glyph_bboxes = {}
    for new_idx, orig_idx in new_to_original.items():
        svg_path = os.path.join(filtered_dir, f"glyph_{new_idx}.svg")
        if not os.path.exists(svg_path):
            continue
            
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            path_elem = root.find('.//{http://www.w3.org/2000/svg}path')
            if path_elem is None:
                continue
                
            d = path_elem.get('d')
            coords = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", d)))
            
            if len(coords) < 4:
                continue
                
            xs = coords[::2]
            ys = coords[1::2]
            
            bbox = (min(xs), min(ys), max(xs), max(ys))
            glyph_bboxes[new_idx] = bbox
            
        except Exception as e:
            print(f"Error processing {svg_path}: {e}")
    
    # Compute descender threshold
    bottoms = [bbox[1] for bbox in glyph_bboxes.values()]
    sorted_bottoms = sorted(bottoms)
    if len(sorted_bottoms) >= 4:
        q1 = sorted_bottoms[len(sorted_bottoms) // 4]
        q3 = sorted_bottoms[3 * len(sorted_bottoms) // 4]
        iqr = q3 - q1
        descender_threshold = q1 - 1.5 * iqr
    else:
        avg_bottom = sum(bottoms) / len(bottoms)
        max_height = max(bbox[3] - bbox[1] for bbox in glyph_bboxes.values())
        descender_threshold = avg_bottom - 0.25 * max_height
    
    descender_glyphs = [idx for idx, bbox in glyph_bboxes.items() if bbox[1] < descender_threshold]
    
    # Calculate overall metrics for proper scaling
    max_height = max(bbox[3] - bbox[1] for bbox in glyph_bboxes.values())
    avg_bottom = sum(bottoms) / len(bottoms)
    
    # Create a grid layout with proper scaling
    grid_size = min(10, int(len(glyph_bboxes)**0.5) + 1)
    cell_size = 120  # Slightly larger cells for better visibility
    grid_width = grid_size * cell_size
    grid_height = ((len(glyph_bboxes) - 1) // grid_size + 1) * cell_size
    
    # Create SVG for grid layout
    grid_svg = ET.Element('svg', {
        'xmlns': 'http://www.w3.org/2000/svg',
        'width': str(grid_width),
        'height': str(grid_height)
    })
    
    # Add white background
    ET.SubElement(grid_svg, 'rect', {
        'width': '100%', 'height': '100%', 'fill': 'white'
    })
    
    # Add glyphs to grid with proper scaling and descender handling
    for i, new_idx in enumerate(sorted(glyph_bboxes.keys())):
        svg_path = os.path.join(filtered_dir, f"glyph_{new_idx}.svg")
        if not os.path.exists(svg_path):
            continue
            
        # Get bbox and calculate position
        bbox = glyph_bboxes[new_idx]
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        
        # Calculate cell position
        row = i // grid_size
        col = i % grid_size
        cell_x = col * cell_size
        cell_y = row * cell_size
        
        # Calculate scale to fit in cell (preserving aspect ratio)
        scale = 0.5
        
        # Center in cell
        center_x = cell_x + cell_size / 2
        center_y = cell_y + cell_size / 2
        
        # Create group for this glyph
        g_elem = ET.SubElement(grid_svg, 'g')
        
        # Add cell border
        ET.SubElement(g_elem, 'rect', {
            'x': str(cell_x), 'y': str(cell_y),
            'width': str(cell_size), 'height': str(cell_size),
            'fill': 'none', 'stroke': '#eee', 'stroke-width': '1'
        })
        
        # Parse SVG to get path data
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            path_elem = root.find('.//{http://www.w3.org/2000/svg}path')
            if path_elem is None:
                continue
                
            d = path_elem.get('d')
            
            # Handle descenders - adjust vertical position
            glyph_center_x = (bbox[0] + bbox[2]) / 2
            glyph_center_y = (bbox[1] + bbox[3]) / 2
            
            translate_x = center_x - glyph_center_x * scale
            
            # Apply special handling for descenders
            if new_idx in descender_glyphs:
                # Move descenders down slightly to make them more visible
                adjustment = (bbox[1] - avg_bottom) * 0.5
                translate_y = center_y - (glyph_center_y + adjustment) * scale
            else:
                translate_y = center_y - glyph_center_y * scale
            
            # Add glyph path with proper transformation
            ET.SubElement(g_elem, 'path', {
                'd': d,
                'transform': f'translate({translate_x},{translate_y}) scale({scale})',
                'fill': 'black'
            })
            
            # Add index label (using new sequential index)
            ET.SubElement(g_elem, 'text', {
                'x': str(cell_x + cell_size / 2),
                'y': str(cell_y + cell_size - 10),
                'text-anchor': 'middle',
                'font-size': '12',
                'fill': 'blue'
            }).text = str(new_idx)
            
            # Add descender indicator if applicable
            if new_idx in descender_glyphs:
                ET.SubElement(g_elem, 'circle', {
                    'cx': str(cell_x + 10),
                    'cy': str(cell_y + 10),
                    'r': '4',
                    'fill': 'red'
                })
            
        except Exception as e:
            print(f"Error processing {svg_path}: {e}")
    
    print(f"does it fail here?")
    # Save grid SVG and convert to PNG
    grid_svg_path = os.path.join(output_dir, "grid_glyphs.svg")
    
    # Add absolute path debugging
    ET.ElementTree(grid_svg).write(grid_svg_path)

    grid_png_path = os.path.join(output_dir, "grid_glyphs.png")

    cairosvg.svg2png(url=grid_svg_path, write_to=grid_png_path, scale=2)

    # Encode the grid image
    with open(grid_png_path, "rb") as image_file:
        grid_encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
    print(grid_png_path)
    
    # Update the grid prompt to be more specific about the grid layout
    grid_prompt = f"""
    This image shows character glyphs from a font arranged in a grid, with **{grid_size} glyphs per row**.
    Please create a mapping between character and position.
    Please identify each character. Provide your answer in this format:
    ```
    Position: Character
    0: A
    1: B
    2: C
    ...
    ```
    There are exactly {grid_size} glyphs per row, positions go 0–{grid_size-1}, {grid_size}–{2*grid_size-1}, {2*grid_size}–{3*grid_size-1}, etc.
    Be sure to identify ALL characters. If you're unsure about a character, make your best guess.
    """
    
    # Call the vision model API
    print(f"Calling vision model API to identify characters...")
    char_map = {}
    char_occurrences = {}  # Track occurrences of each character
    
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://font-generator.com",
                "X-Title": "Font Generator",
            },
            model="qwen/qwen2.5-vl-72b-instruct:free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": grid_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{grid_encoded_image}"}}
                    ]
                }
            ]
        )
        print(completion)
        response = completion.choices[0].message.content
        print("\nVision model response:")
        print(response)

        # Parse character identifications
        for line in response.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('Position'):
                parts = line.split(':')
                if len(parts) == 2:
                    pos_str = parts[0].strip()
                    char_str = parts[1].strip()

                    try:
                        pos = int(pos_str)
                        char = char_str[0] if char_str else ''
                        
                        # Check if character is in the Latin alphabet or is a digit
                        if char and char.lower() in 'abcdefghijklmnopqrstuvwxyz1234567890?!$&/#%@.,':
                            # Track this character occurrence
                            if char not in char_occurrences:
                                char_occurrences[char] = []
                            char_occurrences[char].append((pos, char))
                            
                            # Store in char_map (we'll resolve duplicates later)
                            char_map[pos] = char
                    except ValueError:
                        continue

        print(char_map)
        print(char_occurrences)
        # Add this before the sorting:
        print("Keys in char_map:", [type(k).__name__ + ":" + str(k) for k in char_map.keys()])

    
    
    except Exception as e:
        print(f"Error during character identification: {e}")

    # ---------------------------------------------------------------------
    # 4.  Resolve duplicates
    # ---------------------------------------------------------------------
    def _bbox_area(pos):
        """Return the area of the glyph bbox, 0 if unknown."""
        if pos not in glyph_bboxes:
            return 0
        xmin, xmax, ymin, ymax = glyph_bboxes[pos]
        return (xmax - xmin) * (ymax - ymin)


    letters = {c.lower() for c in char_occurrences if c.isalpha()}

    # First pass: Find unambiguous case pairs using y-min
    case_pairs = {}
    for base in letters:
        # Look for uppercase (ymin=0) and lowercase (ymin>0) regardless of initial labels
        all_upper = [pos for pos in glyph_bboxes if glyph_bboxes[pos][1] == 0 and pos in char_map and char_map[pos].lower() == base]
        all_lower = [pos for pos in glyph_bboxes if glyph_bboxes[pos][1] > 0 and pos in char_map and char_map[pos].lower() == base]
        
        if all_upper and all_lower:
            # Select best pair based on height difference
            best_upper = max(all_upper, key=lambda p: glyph_bboxes[p][3] - glyph_bboxes[p][1])
            best_lower = max(all_lower, key=lambda p: glyph_bboxes[p][3] - glyph_bboxes[p][1])
            case_pairs[base] = (best_lower, best_upper)

    # Apply case pairs and remove duplicates
    for base, (lower_pos, upper_pos) in case_pairs.items():
        # Clear existing mappings
        for pos in list(char_map.keys()):
            if char_map[pos].lower() == base and pos not in {lower_pos, upper_pos}:
                del char_map[pos]
        # Set confirmed pair
        char_map[lower_pos] = base
        char_map[upper_pos] = base.upper()

    # Then proceed with original resolution logic for remaining characters
    for base in letters:
        if base in case_pairs:
            continue  # Already handled
        lower_occ = char_occurrences.get(base, [])
        upper_occ = char_occurrences.get(base.upper(), [])

        # First try: separate by y-min (uppercase ymin=0, lowercase ymin>0)
        real_upper = [pos for pos, _ in upper_occ if glyph_bboxes[pos][1] == 0]
        real_lower = [pos for pos, _ in lower_occ if glyph_bboxes[pos][1] > 0]
        
        if real_upper and real_lower:
            # Get largest of each type
            best_upper = max(real_upper, key=lambda p: glyph_bboxes[p][3] - glyph_bboxes[p][1])
            best_lower = max(real_lower, key=lambda p: glyph_bboxes[p][3] - glyph_bboxes[p][1])
        else:
            pass

        print(f"\nAnalyzing base character: {base}")
        print(f"Lowercase occurrences ({len(lower_occ)}):")
        for pos, _ in lower_occ:
            if pos in glyph_bboxes:
                ymin = glyph_bboxes[pos][1]
                height = glyph_bboxes[pos][3] - ymin
                print(f"  Position {pos}: ymin={ymin:.2f}, height={height:.2f}")
                
        print(f"Uppercase occurrences ({len(upper_occ)}):")
        for pos, _ in upper_occ:
            if pos in glyph_bboxes:
                ymin = glyph_bboxes[pos][1]
                height = glyph_bboxes[pos][3] - ymin
                print(f"  Position {pos}: ymin={ymin:.2f}, height={height:.2f}")

        # -------------------------------------------------- both cases found
        if lower_occ and upper_occ:
            best_lower = max(lower_occ, key=lambda t: _bbox_area(t[0]))[0]
            best_upper = max(upper_occ, key=lambda t: _bbox_area(t[0]))[0]

            # keep one of each
            char_map[best_lower] = base
            char_map[best_upper] = base.upper()

            # delete the extras
            for pos, _ in lower_occ:
                if pos != best_lower and pos in char_map:
                    del char_map[pos]
            for pos, _ in upper_occ:
                if pos != best_upper and pos in char_map:
                    del char_map[pos]
            continue

        # -------------------------------------------------- only LOWER found
        if lower_occ:
            ranked = sorted(lower_occ, key=lambda t: _bbox_area(t[0]), reverse=True)
            if len(ranked) >= 2:
                pos_upper = ranked[0][0]         # biggest  → UPPER
                pos_lower = ranked[1][0]         # next     → lower
                char_map[pos_upper] = base.upper()
                char_map[pos_lower] = base
                for pos, _ in ranked[2:]:
                    if pos in char_map:
                        del char_map[pos]
            else:                                # single lower, keep as is
                pos_lower = ranked[0][0]
                char_map[pos_lower] = base
            continue

        # -------------------------------------------------- only UPPER found
        if upper_occ:
            ranked = sorted(upper_occ, key=lambda t: _bbox_area(t[0]), reverse=True)
            if len(ranked) >= 2:
                pos_upper = ranked[0][0]         # biggest  → UPPER
                pos_lower = ranked[-1][0]        # smallest → lower
                char_map[pos_upper] = base.upper()
                char_map[pos_lower] = base
                for pos, _ in ranked[1:-1]:
                    if pos in char_map:
                        del char_map[pos]
            else:                                # single upper, keep as is
                pos_upper = ranked[0][0]
                char_map[pos_upper] = base.upper()
            continue
    
    # ---------------------------------------------------------------------
    # 5.  Handle non‑letter duplicates (digits, punctuation)
    # ---------------------------------------------------------------------
    for char, occs in list(char_occurrences.items()):
        if char.isalpha() or len(occs) <= 1:
            continue
        # keep only the glyph with the largest area
        best_pos = max(occs, key=lambda t: _bbox_area(t[0]))[0]
        char_map[best_pos] = char
        for pos, _ in occs:
            if pos != best_pos and pos in char_map:
                del char_map[pos]
    
    # Save the final mapping to a file
    output_file = os.path.join(output_dir, "character_mapping.txt")
    with open(output_file, "w") as f:
        f.write("Position\tCharacter\n")
        for pos in sorted(char_map.keys(), key=lambda x: str(x)):
            f.write(f"{pos}\t{char_map[pos]}\n")
       
    # Rename SVG files to match characters for font_generation.py
    for new_idx, char in char_map.items():
        old_path = os.path.join(filtered_dir, f"glyph_{new_idx}.svg")
        if os.path.exists(old_path):
            # Add case indicator to filename to handle case-sensitive filesystems
            case_indicator = "upper" if char.isupper() else "lower"
            new_path = os.path.join(filtered_dir, f"{char}_{case_indicator}.svg")
            shutil.copy2(old_path, new_path)
    
    return char_map
