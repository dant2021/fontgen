import json
import numpy as np
from line_detection import segment_text_lines
from visualization import visualize_lines
import pandas as pd
from scipy.signal import find_peaks
from scipy.stats import gaussian_kde
import re
import os
import matplotlib.pyplot as plt

def normalize_glyph_heights(filtered_bboxes, glyph_paths, output_dir, debug_dir=None, cluster_centers_passed=False):
    """
    Main normalization pipeline. Returns:
    - transformed_bboxes: Scaled and aligned bounding boxes
    - transformed_paths: Scaled and aligned SVG paths
    - reference_lines: Dictionary of reference heights
    - scale_factor: Calculated scaling factor
    """
    # ====================== 1. Line Segmentation ======================
    lines = segment_text_lines(filtered_bboxes, debug_dir, threshold=0.8)
    if debug_dir:
        visualize_lines(filtered_bboxes, lines, os.path.join(debug_dir, "1_initial_lines.png"))
    
    # ====================== 2. Reference Line Detection & alignment ======================
    adjustment_list = []
    descender_info = []  # Track which glyphs are descenders
    topline_info = []
    bottomline_info = []
    for line_idx, line in enumerate(lines):
        # Get all bboxes in this line
        line_bboxes = [filtered_bboxes[i] for i in line]

        # Calculate vertical features
        top = [bbox[2] for bbox in line_bboxes]  # y_min
        bottom = [bbox[3] for bbox in line_bboxes]  # y_max
        heights = [bottom[i] - top[i] for i in range(len(line_bboxes))]
        bottom_baseline = np.percentile(bottom, 20)

        # initialize the arrays
        line_descenders = [False] * len(line_bboxes)
        adjustment = [0] * len(line_bboxes)
        topline = [0] * len(line_bboxes)
        bottomline = [0] * len(line_bboxes)

        # calculate the topline and bottomline for each glyph
        for i in range(len(line_bboxes)):
            if bottom_baseline - bottom[i] < -heights[i] * 0.1:
                line_descenders[i] = True  # Mark this specific glyph as a descender
                adjustment[i] = bottom_baseline - bottom[i]

            else:
                adjustment[i] = 0

            bottomline[i] = bottom_baseline - bottom[i]
            topline[i] = bottom_baseline - top[i]

        # append the arrays to the lists
        adjustment_list.append(adjustment)
        descender_info.append(line_descenders)
        topline_info.append(topline)
        bottomline_info.append(bottomline)
    # Create a flat adjustment array
    flat_adjustments = [0] * len(filtered_bboxes)
    flat_descenders = [False] * len(filtered_bboxes)
    flat_topline = [0] * len(filtered_bboxes)
    flat_bottomline = [0] * len(filtered_bboxes)
    # Map line-specific adjustments to global indices
    for line_idx, line in enumerate(lines):
        for i, bbox_idx in enumerate(line):
            if i < len(adjustment_list[line_idx]):
                flat_adjustments[bbox_idx] = adjustment_list[line_idx][i]
                flat_descenders[bbox_idx] = descender_info[line_idx][i]  # Set the descender info too
                flat_topline[bbox_idx] = topline_info[line_idx][i]
                flat_bottomline[bbox_idx] = bottomline_info[line_idx][i]


    print(f"adjustment_list: {flat_adjustments}")
    print(f"topline_info: {flat_topline}")
    print(f"bottomline_info: {flat_bottomline}")
    
    
    print(f"adjustment_list: {flat_adjustments}")
    print(f"topline_info: {flat_topline}")
    print(f"bottomline_info: {flat_bottomline}")
    
    vertical_shift = [0] * len(filtered_bboxes)
    new_bboxes = []
    for i in range(len(filtered_bboxes)):
        x_min, x_max, y_min, y_max = filtered_bboxes[i]
        # Now use the flat array
        vertical_shift[i] = -y_max + flat_adjustments[i]
        new_bbox = (x_min, x_max, y_min + vertical_shift[i], y_max + vertical_shift[i])
        new_bboxes.append(new_bbox)

    # ====================== 3. Glyph Height Calculation and extrema detection ======================
    
    heights = [new_bboxes[i][3] - new_bboxes[i][2] for i in range(len(new_bboxes))]
    widths = [new_bboxes[i][1] - new_bboxes[i][0] for i in range(len(new_bboxes))]
    areas = [heights[i] * widths[i] for i in range(len(new_bboxes))]
    indices = [i for i in range(len(new_bboxes))]
    topline = [new_bboxes[i][2] - bottom_baseline for i in range(len(new_bboxes))]
    
    # Create a DataFrame with all your glyph data
    df = pd.DataFrame({
        "index": indices,
        "height": heights,
        "width": widths,
        "area": areas,
        "adjustment": flat_adjustments,
        "topline": flat_topline,
        "bottomline": flat_bottomline,
        "calculated_height": [h + a for h, a in zip(heights, flat_adjustments)],
        "is_descender": flat_descenders,
        
    })
    
    # Round all numeric columns to 2 decimal places
    df = df.round(2)
    
    # Statistical analysis with DataFrame methods
    print(f"heights: std={df['height'].std()}, mean={df['height'].mean()}")
    print(f"widths: std={df['width'].std()}, mean={df['width'].mean()}")
    print(f"areas: std={df['area'].std()}, mean={df['area'].mean()}")
    print(f"topline: std={df['topline'].std()}, mean={df['topline'].mean()}")
    print(f"bottomline: std={df['bottomline'].std()}, mean={df['bottomline'].mean()}")

    median_area = df['area'].median()
    median_height = df['height'].median()
    median_width = df['width'].median()
    
    print(f"median_area: {median_area}")
    print(f"median_height: {median_height}")
    print(f"median_width: {median_width}")

    # Define outlier criteria using pandas
    df['is_outlier'] = (
        (df['area'] > 2.5 * median_area) | 
        (df['height'] > 1.5 * median_height) | 
        (df['width'] > 2 * median_width)
    )
    
    df['is_punctuation'] = (
        ((df['area'] < 0.3 * median_area) | 
         (df['height'] < 0.3 * median_height) | 
         (df['width'] < 0.2 * median_width)) &
        (df['height'] <= 0.6 * median_height)
    )
    
    # Get indices lists if needed elsewhere
    outlier_indices = df[df['is_outlier']].index.tolist()
    punctuation_indices = df[df['is_punctuation']].index.tolist()
    
    print(f"outlier_indices: {outlier_indices}")
    print(f"punctuation_indices: {punctuation_indices}")
    decender_indices = df[df['is_descender']].index.tolist()
    print(f"decender_indices: {decender_indices}")

    # Mark outliers and punctuation in the DataFrame
    df["is_outlier"] = False
    df["is_punctuation"] = False
    
    df.loc[outlier_indices, "is_outlier"] = True
    df.loc[punctuation_indices, "is_punctuation"] = True

    # Sort the DataFrame by calculated_height
    df = df.sort_values(by="calculated_height")
    print(f"Sorted DataFrame: \n{df}")

    # ====================== 4. cluster heights ======================
    # here we will cluster the heights into 3 clusters, x height, cap height, decender heights
    # outliers and punctuation will be removed from the clustering
    # decenders will be handled seperately
    # we will use the kmeans algorithm to cluster the heights
    # important we want to keep outliers of the method as separate clusters that will be scaled linearly

    # Filter out outliers and punctuation for clustering
    clustering_df = df[~(df['is_punctuation'] | df['is_outlier'])]

    valid_heights = clustering_df['topline'].values

    # Generate KDE to smooth the histogram
    if len(valid_heights) > 3:  # Need sufficient data for KDE
        # Create density estimate
        kde = gaussian_kde(valid_heights, bw_method=0.25)
        x_grid = np.linspace(min(valid_heights), max(valid_heights), 100)
        density = kde(x_grid)
        
        # Find peaks in the density
        peaks, peak_prominence = find_peaks(density, prominence=0.001, distance=30)
        
        # If only one peak is detected, retry with softer parameters
        if len(peaks) <= 1:
            kde = gaussian_kde(valid_heights, bw_method=0.125)
            x_grid = np.linspace(min(valid_heights), max(valid_heights), 100)
            density = kde(x_grid)
            print("Only one peak detected, retrying with softer parameters")
            peaks, peak_prominence = find_peaks(density, prominence=0.0005, distance=30)
            
        peak_heights = x_grid[peaks]
        # Sort peaks by height
        peak_heights = np.sort(peak_heights)

        print(f"Detected peaks at heights: {peak_heights}")

        full_height = None
        cap_height = None
        x_height = None
        
        if len(peak_heights) == 0:
            print("Warning: No peaks detected, falling back to statistical means")
            x_height = np.percentile(valid_heights, 20)
            cap_height = np.percentile(valid_heights, 80)  # Estimate cap height
            full_height = 0

        # If we found enough peaks, use them directly
        elif len(peak_heights) == 1:
            print("Warning: Only one peak detected")
            x_height = 0
            cap_height = peak_heights[0]
            full_height = 0

        elif len(peak_heights) == 2:
            x_height = peak_heights[0]
            cap_height = peak_heights[1]
            full_height = 0

        elif len(peak_heights) >= 3:
            # Keep the 3 peaks with highest amplitude values
            peak_amplitudes = density[peaks]
            # Get indices of peaks sorted by amplitude (highest first)
            sorted_indices = np.argsort(peak_amplitudes)[::-1][:3]
            # Get the sorted peak heights (take only top 3)
            peak_heights = np.array(peak_heights)[sorted_indices]
            # Sort by height (ascending)
            peak_heights = np.sort(peak_heights)
            # Assign to typography lines
            x_height = peak_heights[0]
            cap_height = peak_heights[1]
            full_height = peak_heights[2]
        
        # Create cluster centers from the peaks
        cluster_centers = np.array([x_height, cap_height, full_height])
        punctuation_center = max(cluster_centers) * 0.2
        cluster_centers = np.append(cluster_centers, punctuation_center)
    else:
        print("Warning: Not enough characters to detect peaks")
        x_height = np.percentile(valid_heights, 20)
        cap_height = np.percentile(valid_heights, 80)  # Estimate cap height
        full_height = 0

    
    # Assign each glyph to nearest typographic line
    df['cluster'] = df['topline'].apply(
        lambda h: np.argmin(np.abs([h-cluster_centers[0], h-cluster_centers[1], h-cluster_centers[2], h-cluster_centers[3]]))
    )
    if punctuation_indices:
        df.loc[punctuation_indices, 'cluster'] = 3
    if outlier_indices:
        df.loc[outlier_indices, 'cluster'] = 4
    cluster_mapping = {
        'x_height_cluster': 0,
        'cap_height_cluster': 1,
        'full_height_cluster': 2,
        'punctuation_cluster': 3,
        'outlier_cluster': 4
    }
    print(f"Raw cluster centers: {[x_height, cap_height, full_height, punctuation_center]}")
    print(f"Final cluster centers: {cluster_centers}")
    cluster_centers = [cluster_centers[0], cluster_centers[1], cluster_centers[2], cluster_centers[3]]

    if cluster_centers_passed == False:
        # save cluster_centers
        with open(os.path.join(output_dir, "cluster_centers.json"), "w") as f:
            json.dump(cluster_centers, f)

    if cluster_centers_passed == True:
        # resize to cluster_centers_passed
        with open(os.path.join(output_dir, "cluster_centers.json"), "r") as f:
            cluster_centers_passed = json.load(f)
        cluster_centers = cluster_centers_passed

    # Create histogram with KDE and detected peaks
    if debug_dir:
        plt.figure(figsize=(10, 6))
        
        # Plot histogram
        plt.hist(df['topline'], bins=100, alpha=0.5, density=True)
        
        # Plot KDE
        if len(valid_heights) > 5:
            plt.plot(x_grid, density, 'r-', label='Density')
            plt.plot(peak_heights, kde(peak_heights), 'go', label='Peaks')
        
        # Plot cluster centers
        for i, center in enumerate(cluster_centers):
            plt.axvline(x=center, color=['r','g','b','y'][i], 
                       linestyle='--', 
                       label=f"{['X-height', 'Cap height', 'Descender', 'Punctuation'][i]}: {center:.2f}")
        
        plt.legend()
        plt.title('Glyph Height Distribution with Detected Typography Lines')
        plt.xlabel('Height')
        plt.ylabel('Density')
        plt.savefig(os.path.join(debug_dir, "2_height_analysis.png"))

    print(f"cluster_centers: {cluster_centers}")
    print("================================================")

    # ====================== 5. scale the glyphs ======================
    transformed_bboxes = []
    transformed_paths = []
    scale_factors = []
    for i in range(len(filtered_bboxes)):
        # Get current bbox and path
        bbox = filtered_bboxes[i]
        path = glyph_paths[i]
        
        # Get cluster assignment for this glyph
        cluster = df.loc[i, 'cluster']
        
        # Get target height based on cluster
        target_height = cluster_centers[min(cluster, len(cluster_centers)-1)]-flat_adjustments[i]
        index = i

        
        # Calculate scaling factor - how much we need to scale to reach target height
        current_height = flat_topline[i] - flat_bottomline[i]
        if current_height != 0 and target_height != 0:
            scale_factor = target_height / current_height
        else:
            scale_factor = 1.0

        x_min, x_max, y_min, y_max = bbox
        if target_height == cluster_centers[0]:
            vertical_shift =  - y_min + max(cluster_centers[0], cluster_centers[1], cluster_centers[2])-cluster_centers[0] # x height
        elif target_height == cluster_centers[1]:
            vertical_shift =  - y_min + max(cluster_centers[0], cluster_centers[1], cluster_centers[2])-cluster_centers[1] # cap height
        elif target_height == cluster_centers[2]:
            vertical_shift =  - y_min + max(cluster_centers[0], cluster_centers[1], cluster_centers[2])-cluster_centers[2] # full height - optional
        elif target_height == cluster_centers[3]:
            vertical_shift =  - y_min + max(cluster_centers[0], cluster_centers[1], cluster_centers[2])-cluster_centers[3] # punctuation

        # Transform the path using regex to modify coordinates
        coord_re = re.compile(r'([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?),([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)')
        
        # Define the transform function for scaling and shifting
        def transform_coords(match):
            x = float(match.group(1)) 
            y = float(match.group(2))
            
            # First apply vertical shift
            y += vertical_shift
            
            # Then apply scaling (x and y)
            x *= scale_factor
            y *= scale_factor

            return f"{x:.2f},{y:.2f}"
        
        # Apply the transformation to the path
        transformed_path = coord_re.sub(transform_coords, path)
        
        # Function to extract bounding box from an SVG path
        def bbox_from_path(path_str):
            # Extract all coordinate pairs
            matches = coord_re.findall(path_str)
            if not matches:
                return (0, 0, 0, 0)
                
            # Parse x,y values from matches
            coords = [(float(x), float(y)) for x, y in matches]
            
            # Find min/max values
            x_values = [x for x, y in coords]
            y_values = [y for x, y in coords]
            
            x_min = min(x_values)
            x_max = max(x_values)
            y_min = min(y_values)
            y_max = max(y_values)
            
            return (x_min, x_max, y_min, y_max)
        
        # Verify the transformation
        path_bbox = bbox_from_path(transformed_path)

        if scale_factor > 1.5 or scale_factor < 0.6:
            print(f"index: {index}")
            print(f"target_height: {target_height}")
            print("================================================")
            print(f"Warning: Scale factor is too large or too small for glyph {i}")
            print(f"current_height: {current_height}")
            print("================================================")
            print(f"scale_factor: {scale_factor}")
            top_line = flat_topline[i]
            bottom_line = flat_bottomline[i]
            print(f"top_line: {top_line}")
            print(f"bottom_line: {bottom_line}")
            print(f"current_height: {current_height}")
            print("================================================")
            print(f"scale_factor: {scale_factor}")
            print("================================================")
            print(f"Path transformed_bbox: {path_bbox}")
            print("================================================")

        scale_factors.append(scale_factor)
        transformed_bboxes.append(path_bbox)
        transformed_paths.append(transformed_path)
    
    # Create reference lines dictionary to return
    reference_lines = {
        "base_line": max(cluster_centers[0], cluster_centers[1], cluster_centers[2]),
        "x_height": max(cluster_centers[0], cluster_centers[1], cluster_centers[2]) - cluster_centers[0],
        "cap_height": max(cluster_centers[0], cluster_centers[1], cluster_centers[2]) - cluster_centers[1],
        "full_height": max(cluster_centers[0], cluster_centers[1], cluster_centers[2]) - cluster_centers[2],
        "punctuation_height": max(cluster_centers[0], cluster_centers[1], cluster_centers[2]) - cluster_centers[3]
    }
    
    # Use a representative scale factor for the return value
    avg_scale = np.mean([float(scale_factors[i]) for i in range(len(new_bboxes)) 
                         if not df.loc[i, 'is_outlier'] and not df.loc[i, 'is_punctuation']])
    
    print(f"avg_scale: {avg_scale}")
    print("================================================")

    # Before return statement:
    print(f"Final scale type: {type(avg_scale)}")

    # save svg
    if debug_dir:
        # Save all transformed paths in one svg file
        with open(os.path.join(debug_dir, "normalized_glyphs.svg"), "w") as f:
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" style="background-color:white">\n')
            for path in transformed_paths:
                f.write(f'<path d="{path}" fill="transparent" stroke="black" stroke-width="0.3"/>\n')
            f.write('</svg>')
        print(f"SVG file saved to {os.path.join(debug_dir, 'normalized_glyphs.svg')}")

    
    return transformed_bboxes, transformed_paths, reference_lines, avg_scale