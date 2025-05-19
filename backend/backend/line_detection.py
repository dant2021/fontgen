import numpy as np
import cv2
import os

from visualization import visualize_lines

def segment_text_lines(filtered_bboxes, debug_dir=None, threshold=0.4):
    """
    Group bounding boxes into lines based on vertical positions.
    Returns a list of lists of indices.
    """
    # Sort by vertical center
    centers = [(i, (bbox[2] + bbox[3]) / 2) for i, bbox in enumerate(filtered_bboxes)]
    centers.sort(key=lambda x: x[1])


    height_list = [bbox[3] - bbox[2] for bbox in filtered_bboxes]
    avg_height = sum(height_list) / len(height_list)
    threshold = threshold * avg_height  # vertical distance threshold, adjust as needed
    print(f"threshold: {threshold}")

    lines = []
    current_line = []
    #threshold = 20  # vertical distance threshold, adjust as needed

    for idx, y_center in centers:
        if not current_line:
            current_line.append(idx)
            last_y = y_center
        elif abs(y_center - last_y) < threshold:
            current_line.append(idx)
            last_y = (last_y + y_center) / 2
        else:
            lines.append(current_line)
            current_line = [idx]
            last_y = y_center

    if current_line:
        lines.append(current_line)

    # Optional: save debug visualization
    if debug_dir:
        visualize_lines(filtered_bboxes, lines, os.path.join(debug_dir, "text_lines.png"))

    print("lines: ", lines)
    print("filtered_bboxes: ", filtered_bboxes[0])
    print("centers: ", centers[0])
    print("filtered_bboxes[0][2] = y min: ", filtered_bboxes[0][2])
    print("filtered_bboxes[0][3] = y max: ", filtered_bboxes[0][3])

    return lines
