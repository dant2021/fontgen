from svgpathtools import parse_path

def get_path_bbox(path_d, transform=None):
    """Returns the bounding box (xmin, xmax, ymin, ymax) of an SVG path string."""
    try:
        path = parse_path(path_d)
        if not path:
            return None

        all_points = []
        for seg in path:
            all_points.append(seg.start)
            all_points.append(seg.end)
            if hasattr(seg, 'control1'):
                all_points.append(seg.control1)
            if hasattr(seg, 'control2'):
                all_points.append(seg.control2)

        # Apply translation if present
        if transform and 'translate' in transform:
            tx, ty = map(float, transform.split('translate(')[1].split(')')[0].split(','))
            all_points = [complex(p.real + tx, p.imag + ty) for p in all_points]

        x_coords = [p.real for p in all_points]
        y_coords = [p.imag for p in all_points]

        xmin = min(x_coords)
        xmax = max(x_coords)
        ymin = min(y_coords)
        ymax = max(y_coords)

        return (xmin, xmax, ymin, ymax)
    except Exception:
        return None


def filter_large_bboxes(bboxes, max_width=2000, max_height=2000):
    """
    Filter out bounding boxes that are too large (likely background or noise).
    """
    filtered = []
    for bbox in bboxes:
        xmin, xmax, ymin, ymax = bbox
        width = xmax - xmin
        height = ymax - ymin
        if width < max_width and height < max_height:
            filtered.append(bbox)
    return filtered
