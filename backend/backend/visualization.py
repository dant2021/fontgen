import os
import numpy as np
import cv2
import matplotlib.pyplot as plt

def visualize_lines(bboxes, lines, output_path):
    """Visualize text lines for debugging."""
    canvas_width = 1024
    canvas_height = 1024
    canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255

    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255),
        (128, 0, 0), (0, 128, 0), (0, 0, 128)
    ]

    for line_idx, line in enumerate(lines):
        color = colors[line_idx % len(colors)]
        for bbox_idx in line:
            bbox = bboxes[bbox_idx]
            xmin, xmax, ymin, ymax = bbox
            cv2.rectangle(canvas, (int(xmin), int(ymin)), (int(xmax), int(ymax)), color, 2)
            cv2.putText(canvas, str(bbox_idx), (int(xmin), int(ymin) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    cv2.imwrite(output_path, canvas)


def visualize_merges(bboxes, merge_details, output_path):
    """Visualize which components were merged and why."""
    canvas_width = 1024
    canvas_height = 1024
    canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255

    # Draw all bboxes in gray
    for i, bbox in enumerate(bboxes):
        xmin, xmax, ymin, ymax = bbox
        cv2.rectangle(canvas, (int(xmin), int(ymin)), (int(xmax), int(ymax)), (200, 200, 200), 1)
        cv2.putText(canvas, str(i), (int(xmin), int(ymin) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Draw merge connections
    for merge in merge_details:
        primary_bbox = merge['primary_bbox']
        secondary_bbox = merge['secondary_bbox']

        primary_center = (
            int((primary_bbox[0] + primary_bbox[1]) / 2),
            int((primary_bbox[2] + primary_bbox[3]) / 2)
        )
        secondary_center = (
            int((secondary_bbox[0] + secondary_bbox[1]) / 2),
            int((secondary_bbox[2] + secondary_bbox[3]) / 2)
        )

        color = (0, 0, 255) if merge['reason'] == 'containment' else (0, 255, 0)
        cv2.line(canvas, primary_center, secondary_center, color, 2)

        cv2.rectangle(canvas, (int(primary_bbox[0]), int(primary_bbox[2])),
                      (int(primary_bbox[1]), int(primary_bbox[3])), color, 2)
        cv2.rectangle(canvas, (int(secondary_bbox[0]), int(secondary_bbox[2])),
                      (int(secondary_bbox[1]), int(secondary_bbox[3])), color, 2)

        cv2.putText(canvas, f"{merge['primary']}",
                    (int(primary_bbox[0]), int(primary_bbox[2]) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        cv2.putText(canvas, f"{merge['secondary']}",
                    (int(secondary_bbox[0]), int(secondary_bbox[2]) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        mid_x = (primary_center[0] + secondary_center[0]) // 2
        mid_y = (primary_center[1] + secondary_center[1]) // 2
        cv2.putText(canvas, merge['reason'], (mid_x, mid_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    cv2.imwrite(output_path, canvas)


def visualize_merged_bboxes(merged_bboxes, output_path):
    """Visualize the final merged bounding boxes."""
    canvas_width = 1024
    canvas_height = 1024
    canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255

    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255),
        (128, 0, 0), (0, 128, 0), (0, 0, 128)
    ]

    for i, bbox in enumerate(merged_bboxes):
        color = colors[i % len(colors)]
        xmin, xmax, ymin, ymax = bbox
        cv2.rectangle(canvas, (int(xmin), int(ymin)), (int(xmax), int(ymax)), color, 2)
        cv2.putText(canvas, str(i), (int(xmin), int(ymin) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    cv2.imwrite(output_path, canvas)
