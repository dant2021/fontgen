import fontforge
import math

def get_aligned_distance(left_glyph, right_glyph, target_y=None):
    """
    Calculate distance between glyphs considering vertical alignment.
    If target_y is None, uses the middle y-coordinate of the smaller glyph.
    """
    # Get contours
    left_contours = left_glyph.layers[1]
    right_contours = right_glyph.layers[1]

    if not left_contours or not right_contours:
        return None

    min_distance = float('inf')

    # Iterate over points in contours
    for left_contour in left_contours:
        for left_point in left_contour:
            for right_contour in right_contours:
                for right_point in right_contour:
                    distance = (((right_point.x + left_glyph.width) - left_point.x)**2 + (right_point.y - left_point.y)**2)**0.5
                    min_distance = min(min_distance, distance)

    if min_distance == float('inf'):
        return None

    return min_distance

def optimize_kerning(font, target_spacing=0, debug=False):
    """
    Optimizes kerning for all glyph pairs considering vertical alignment.
    """
    glyphs = [g for g in font.glyphs() if g.isWorthOutputting()]
    if debug:
        print(f"Found {len(glyphs)} glyphs to process")
        if glyphs:
            # Print first glyph's point count for verification
            layer = glyphs[5].layers[1]
            point_count = sum(len(contour) for contour in layer)
            print(f"First glyph '{glyphs[5].glyphname}' has {point_count} points")
    
    total_pairs = len(glyphs) * len(glyphs)
    processed = 0
    skipped_no_points = 0
    skipped_no_alignment = 0
    
    kerning_values = []
    
    for left in glyphs:
        left_name = left.glyphname
        for right in glyphs:
            right_name = right.glyphname
            if left_name == right_name:
                continue
            
            distance = get_aligned_distance(left, right)
            if distance is None:
                skipped_no_points += 1
                continue
                
            kerning_value = target_spacing - distance
            kerning_values.append((left_name, right_name, kerning_value))

            processed += 1
            if debug and processed % 1000 == 0:
                print(f"Processed {processed}/{total_pairs} pairs...")
    
    if debug:
        print(f"Kerning optimization complete. Processed {processed} pairs.")
        print(f"Skipped {skipped_no_points} pairs with no points found")
        print(f"Skipped {skipped_no_alignment} pairs with no alignment points")

    count = 0
    lookup_name = "pair_kerning_lookup"
    subtable_name = "pair_kerning_subtable"
    font.addLookup(lookup_name, "gpos_pair", None, (("kern", (("latn", ("dflt")),)),))
    font.addLookupSubtable(lookup_name, subtable_name)
    for left_glyph_name, right_glyph_name, kerning_value in kerning_values:
        if left_glyph_name != '.notdef' or right_glyph_name != '.notdef':
            left_glyph = font[left_glyph_name]
            round_kerning_value = round(kerning_value)
            if abs(round_kerning_value) > 10:
                left_glyph.addPosSub(subtable_name, right_glyph_name, 
                0, 0, round_kerning_value, 0,     
                0, 0, 0, 0)  

                count += 1
    print(f"Total kerning pairs: {count}")

if __name__ == "__main__":
    font = fontforge.open("/root/font_gen/from_openai/font_generator/MyFont-Bold.otf")
    optimize_kerning(font, target_spacing=150, debug=True)
    font.generate("/root/font_gen/from_openai/font_generator/MyFont-Bold-kerned.otf")
