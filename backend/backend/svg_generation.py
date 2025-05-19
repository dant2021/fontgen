import potrace
from utils import get_path_bbox, filter_large_bboxes
from glyph_segmentation import merge_glyph_paths
import os

def trace_bitmap_to_svg_paths(bitmap, debug_dir=None):
    bmp = potrace.Bitmap(bitmap)
    path = bmp.trace()

    # Add paths to SVG
    paths_data = []
    for curve in path:
        path_d = f'M{curve.start_point[0]},{curve.start_point[1]} '
        for segment in curve:
            if segment.is_corner:
                c_x, c_y = segment.c
                end_x, end_y = segment.end_point
                path_d += f"L{c_x},{c_y} L{end_x},{end_y} "
            else:
                c1_x, c1_y = segment.c1
                c2_x, c2_y = segment.c2
                end_x, end_y = segment.end_point
                path_d += f"C{c1_x},{c1_y} {c2_x},{c2_y} {end_x},{end_y} "
        path_d += 'Z'
        paths_data.append(path_d)

    bboxes = [get_path_bbox(path_d) for path_d in paths_data]
    filtered_bboxes = filter_large_bboxes(bboxes)

    merged_paths, merged_bboxes = merge_glyph_paths(paths_data, filtered_bboxes, debug_dir=debug_dir, debug=True)

    if debug_dir:
        # Save raw SVG for debugging
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg">\n'
        for path_d in merged_paths:
            svg_content += f'<path d="{path_d}" fill="black" fill-rule="evenodd" />\n'
        svg_content += '</svg>'
        with open(os.path.join(debug_dir, "traced.svg"), "w") as f:
            f.write(svg_content)

    return merged_paths, merged_bboxes
