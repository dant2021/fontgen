import os

from visualization import visualize_merges, visualize_merged_bboxes
from line_detection import segment_text_lines

def is_partially_contained(bbox_inner, bbox_outer, threshold=0.6):
    """
    Check if bbox_inner is partially contained within bbox_outer.
    
    Args:
        bbox_inner: The potentially contained bbox (x_min, x_max, y_min, y_max)
        bbox_outer: The containing bbox (x_min, x_max, y_min, y_max)
        threshold: Minimum overlap ratio required (0.0 to 1.0)
    
    Returns:
        bool: True if bbox_inner is at least threshold% contained in bbox_outer
    """
    # Calculate the area of bbox_inner
    inner_width = bbox_inner[1] - bbox_inner[0]
    inner_height = bbox_inner[3] - bbox_inner[2]
    inner_area = inner_width * inner_height
    
    if inner_area == 0:
        return False
    
    # Calculate the intersection area
    x_overlap = max(0, min(bbox_inner[1], bbox_outer[1]) - max(bbox_inner[0], bbox_outer[0]))
    y_overlap = max(0, min(bbox_inner[3], bbox_outer[3]) - max(bbox_inner[2], bbox_outer[2]))
    intersection_area = x_overlap * y_overlap
    
    # Calculate the overlap ratio
    overlap_ratio = intersection_area / inner_area
    
    return overlap_ratio >= threshold

def merge_glyph_paths(paths_data, filtered_bboxes, debug_dir=None, debug=False):
    bbox_to_path = {i: paths_data[i] for i in range(len(paths_data))}
    processed = set()
    merged_paths = []
    merged_bboxes = []
    merge_details = []

    # --------- GLOBAL CONTAINMENT MERGE ---------
    for i in range(len(filtered_bboxes)):
        if i in processed:
            continue
        current_bbox = filtered_bboxes[i]
        current_glyph_path = bbox_to_path[i]
        components_to_merge = []

        for j in range(len(filtered_bboxes)):
            if j == i or j in processed:
                continue
            bbox_j = filtered_bboxes[j]

            # If bbox_j is fully inside bbox_i
            if (bbox_j[0] >= current_bbox[0] and bbox_j[1] <= current_bbox[1] and
                bbox_j[2] >= current_bbox[2] and bbox_j[3] <= current_bbox[3]):
                if debug:
                    print(f"Containment detected: bbox {j} inside bbox {i}")
                components_to_merge.append(j)
                merge_details.append({
                    'primary': i,
                    'secondary': j,
                    'reason': 'containment',
                    'primary_bbox': current_bbox,
                    'secondary_bbox': bbox_j
                })

            # If bbox_j is over 60% inside bbox_i
            elif is_partially_contained(bbox_j, current_bbox, threshold=0.4):
                if debug:
                    print(f"Partial containment detected: bbox {j} partially inside bbox {i}")
                components_to_merge.append(j)
                merge_details.append({
                    'primary': i,
                    'secondary': j,
                    'reason': 'partial_containment',
                    'primary_bbox': current_bbox,
                    'secondary_bbox': bbox_j
                })

        # Merge contained components
        for j in components_to_merge:
            current_glyph_path += " " + bbox_to_path[j]
            processed.add(j)
            current_bbox = (
                min(current_bbox[0], filtered_bboxes[j][0]),
                max(current_bbox[1], filtered_bboxes[j][1]),
                min(current_bbox[2], filtered_bboxes[j][2]),
                max(current_bbox[3], filtered_bboxes[j][3])
            )

        merged_paths.append(current_glyph_path)
        merged_bboxes.append(current_bbox)
        processed.add(i)

    # --------- DOT/ACCENT & SPECIAL CHAR MERGE BASED ON BBOX PROXIMITY ---------
    # Compute average glyph height
    heights = [bbox[3] - bbox[2] for bbox in merged_bboxes]
    max_height = sorted(heights)[int(len(heights) * 0.8)]
    print(f"max_height: {max_height}")
    # Classify small glyphs (potential dots/accents/special char parts)
    small_indices = [i for i, bbox in enumerate(merged_bboxes) if (bbox[3] - bbox[2]) < 0.4 * max_height]
    # Classify base glyphs (largest unmerged glyphs)
    base_indices = [i for i in range(len(merged_bboxes)) if i not in small_indices]

    # Optionally visualize for debugging
    if debug:
        print(f"Small glyphs (potential dots/accents): {small_indices}")
        print(f"Base glyphs: {base_indices}")

    # Track which small glyphs have been merged
    merged_small = set()
    for small_idx in small_indices:
        if small_idx in merged_small:
            continue
        small_bbox = merged_bboxes[small_idx]
        small_center_x = (small_bbox[0] + small_bbox[1]) / 2
        small_top = small_bbox[2]
        small_bottom = small_bbox[3]

        best_base = None
        min_dist = float('inf')
        for base_idx in base_indices:
            base_bbox = merged_bboxes[base_idx]
            base_center_x = (base_bbox[0] + base_bbox[1]) / 2
            base_top = base_bbox[2]
            base_bottom = base_bbox[3]

            # Only consider base glyphs below the small glyph
            vertical_dist = min(abs(small_bottom - base_top), abs(small_top - base_bottom))  # positive if small is above base 
            horizontal_dist = abs(small_center_x - base_center_x)

            if 0 < vertical_dist <= 0.2 * max_height and horizontal_dist <= 0.2 * max_height:
                dist = (vertical_dist ** 2 + horizontal_dist ** 2) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    best_base = base_idx

                print(f"Checking small {small_idx} (bbox={small_bbox}) with base {base_idx} (bbox={base_bbox}): "
                      f"vertical_dist={vertical_dist:.2f}, horizontal_dist={horizontal_dist:.2f}")

        if best_base is not None:
            # Merge small glyph with base glyph
            merged_paths[best_base] += " " + merged_paths[small_idx]
            merged_bboxes[best_base] = (
                min(merged_bboxes[best_base][0], small_bbox[0]),
                max(merged_bboxes[best_base][1], small_bbox[1]),
                min(merged_bboxes[best_base][2], small_bbox[2]),
                max(merged_bboxes[best_base][3], small_bbox[3])
            )
            merged_small.add(small_idx)
            if debug:
                print(f"Merged small glyph {small_idx} into base glyph {best_base}")

    # Remove merged small glyphs from merged_paths and merged_bboxes
    merged_paths = [p for i, p in enumerate(merged_paths) if i not in merged_small]
    merged_bboxes = [b for i, b in enumerate(merged_bboxes) if i not in merged_small]

    # After proximity-based merging
    lines = segment_text_lines(merged_bboxes, debug_dir=debug_dir)

    #todo: check if any glyphs have been merged and split them at the thinnest part of the glyph

    # Flatten the lines to get the correct order
    ordered_indices = [i for line in lines for i in line]
    final_paths = [merged_paths[i] for i in ordered_indices]
    final_bboxes = [merged_bboxes[i] for i in ordered_indices]

    if debug:
        print(f"Final merged glyph count: {len(final_paths)}")
        if debug_dir:
            visualize_merges(filtered_bboxes, merge_details, os.path.join(debug_dir, "merge_visualization.png"))
            visualize_merged_bboxes(final_bboxes, os.path.join(debug_dir, "merged_bboxes.png"))
    
    return final_paths, final_bboxes