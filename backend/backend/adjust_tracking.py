import fontforge

def tracking_font(font, map_clusters_to_chars=None, modified_spacing=None):
    widths = []
    if map_clusters_to_chars is None:
        # Process all glyphs that have outlines and are not special glyphs
        chars = []
        for glyph in font.glyphs():
            if glyph.isWorthOutputting() and glyph.unicode != -1:
                try:
                    char = chr(glyph.unicode)
                    chars.append(char)
                except ValueError:
                    pass
    else:
        chars = map_clusters_to_chars.values()
    
    for char in chars:
        try:
            glyph = font[ord(char)]
            bbox = glyph.boundingBox()
            widths.append(bbox[2] - bbox[0])
        except (KeyError, TypeError):
            # Handle cases where character is not found or invalid
            pass
    
    if widths:
        avg_width = sum(widths) / len(widths)
        print(f"avg_width: {avg_width}")
        target_spacing = avg_width / 5 
        if modified_spacing is not None:
            target_spacing = target_spacing + modified_spacing
        for char in chars:
            try:
                glyph = font[ord(char)]
                bbox = glyph.boundingBox()
                glyph.width = int((bbox[2] - bbox[0]) + target_spacing)
                x_shift = target_spacing/2 - bbox[0]
                glyph.transform((1, 0, 0, 1, x_shift, 0))
                glyph.autoHint()
            except (KeyError, TypeError):
                # Handle cases where character is not found or invalid
                pass

    return font, target_spacing    
