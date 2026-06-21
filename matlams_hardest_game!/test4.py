import cv2
import numpy as np
import get_image


# ========================================================
# CONFIGURATION
# ========================================================

VIDEO_FILE = "vid25.mp4"
TEMPLATE_PATH = r".\template_title.png"

RELATIVE_START_X = 1024 - 173  # 851
RELATIVE_START_Y = 10

CALIBRATION_X = 0
CALIBRATION_Y = 0
MATCH_THRESHOLD = 0.7
ROI_SIZE = 20

# 160-bit mode
FRAME_ROWS = 5
FRAME_COLS = 32
BATCH_SIZE = FRAME_ROWS * FRAME_COLS  # 160

SEARCH_WIDTH = 235
SEARCH_HEIGHT = 33

ROI_MARGIN_X = 10
ROI_MARGIN_Y = 10

DISPLAY_ZOOM = 4

# Faint red pixel detection.
# OpenCV images are BGR, so this means:
# B = 0..5, G = 0..5, R = 8..25
LOWER_RED_BIT = np.array([0, 0, 8], dtype=np.uint8)
UPPER_RED_BIT = np.array([5, 5, 25], dtype=np.uint8)

all_batches = []


# ========================================================
# LOAD TEMPLATE
# ========================================================

template_img = cv2.imread(TEMPLATE_PATH)

if template_img is None:
    raise FileNotFoundError(f"Could not load template image: {TEMPLATE_PATH}")

template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)


# ========================================================
# WINDOW / CORNER DETECTION
# ========================================================

def detect_corner(frame, template_gray):
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    res = cv2.matchTemplate(gray_frame, template_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    if max_val < MATCH_THRESHOLD:
        return None

    t_h, _ = template_gray.shape

    coarse_x = max_loc[0]
    coarse_y = max_loc[1] + t_h

    roi_start_y = max(0, coarse_y - ROI_SIZE)
    roi_end_y = min(frame.shape[0], coarse_y + ROI_SIZE)
    roi_start_x = max(0, coarse_x - ROI_SIZE)
    roi_end_x = min(frame.shape[1], coarse_x + ROI_SIZE)

    corner_roi = frame[roi_start_y:roi_end_y, roi_start_x:roi_end_x]

    if corner_roi.size == 0:
        return None

    gray_roi = cv2.cvtColor(corner_roi, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray_roi, 50, 150)

    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        20,
        minLineLength=10,
        maxLineGap=5
    )

    precise_local_x = coarse_x - roi_start_x
    precise_local_y = coarse_y - roi_start_y

    if lines is not None:
        horiz_lines = []
        vert_lines = []

        for line in lines:
            x1, y1, x2, y2 = line[0]

            if abs(y1 - y2) < 3:
                horiz_lines.append((x1, y1, x2, y2))

            elif abs(x1 - x2) < 3:
                vert_lines.append((x1, y1, x2, y2))

        if horiz_lines:
            horiz_lines.sort(
                key=lambda l: abs(l[1] - corner_roi.shape[0] / 2)
            )
            precise_local_y = horiz_lines[0][1]

        if vert_lines:
            vert_lines.sort(
                key=lambda l: abs(l[0] - corner_roi.shape[1] / 2)
            )
            precise_local_x = vert_lines[0][0]

    final_x = int(precise_local_x + roi_start_x + CALIBRATION_X)
    final_y = int(precise_local_y + roi_start_y + CALIBRATION_Y)

    return final_x, final_y


# ========================================================
# BIT EXTRACTION + RED READ-POINT OVERLAY
# ========================================================

def extract_bit_matrix(mask, roi_display=None, rows=FRAME_ROWS, cols=FRAME_COLS):
    """
    Reads the bit grid from mask.

    If roi_display is supplied, it draws:
    - gray cell boundaries
    - little red squares at the exact read centers
    - green outline on cells decoded as 1
    """
    height, width = mask.shape
    matrix = []

    cell_h = height / rows
    cell_w = width / cols

    for r in range(rows):
        for c in range(cols):
            x1 = int(round(c * cell_w))
            x2 = int(round((c + 1) * cell_w))
            y1 = int(round(r * cell_h))
            y2 = int(round((r + 1) * cell_h))

            x1 = max(0, min(width - 1, x1))
            x2 = max(x1 + 1, min(width, x2))
            y1 = max(0, min(height - 1, y1))
            y2 = max(y1 + 1, min(height, y2))

            cell = mask[y1:y2, x1:x2]

            bit_is_on = np.sum(cell > 0) > (cell.size * 0.2)
            matrix.append(1 if bit_is_on else 0)

            if roi_display is not None:
                # Gray border around the sampled cell
                cv2.rectangle(
                    roi_display,
                    (x1, y1),
                    (x2 - 1, y2 - 1),
                    (80, 80, 80),
                    1
                )

                # Red square at the exact center where this cell is read
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                half = 2

                cv2.rectangle(
                    roi_display,
                    (cx - half, cy - half),
                    (cx + half, cy + half),
                    (0, 0, 255),
                    -1
                )

                # Green border if decoded as 1
                if bit_is_on:
                    cv2.rectangle(
                        roi_display,
                        (x1, y1),
                        (x2 - 1, y2 - 1),
                        (0, 255, 0),
                        1
                    )

    return matrix


# ========================================================
# MAIN VIDEO SCANNER
# ========================================================

def scan_video_with_dynamic_origin(video_path, start_x, start_y):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error: Could not open video at {video_path}. Check the file name and path.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        fps = 30

    start_frame = int(2 * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    frame_count = start_frame

    origin_x = None
    origin_y = None

    roi_buffer = []

    print("Starting video scan...")

    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            print("Reached the end of the video or video could not be read.")
            break

        corner = detect_corner(frame, template_gray)

        if corner is not None:
            origin_x, origin_y = corner

            cv2.drawMarker(
                frame,
                (origin_x, origin_y),
                (0, 255, 0),
                cv2.MARKER_CROSS,
                20,
                2
            )
        else:
            print(f"Frame {frame_count}: corner not detected.")

        # Do not try to calculate coordinates if no origin has been found yet.
        if origin_x is None or origin_y is None:
            cv2.imshow("Detection Test", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            frame_count += 1
            continue

        data_abs_x = origin_x + start_x
        data_abs_y = origin_y + start_y

        roi_y_start = data_abs_y - ROI_MARGIN_Y
        roi_y_end = data_abs_y + SEARCH_HEIGHT

        roi_x_start = data_abs_x - ROI_MARGIN_X
        roi_x_end = data_abs_x + SEARCH_WIDTH

        frame_height, frame_width, _ = frame.shape

        roi_y_start = max(0, roi_y_start)
        roi_y_end = min(frame_height, roi_y_end)

        roi_x_start = max(0, roi_x_start)
        roi_x_end = min(frame_width, roi_x_end)

        if roi_y_end <= roi_y_start or roi_x_end <= roi_x_start:
            print(f"Frame {frame_count}: invalid ROI.")
            frame_count += 1
            continue

        # Draw purple rectangle around the whole searched ROI on the main video.
        cv2.rectangle(
            frame,
            (roi_x_start, roi_y_start),
            (roi_x_end, roi_y_end),
            (255, 0, 255),
            2
        )

        cv2.imshow("Detection Test", frame)

        roi = frame[roi_y_start:roi_y_end, roi_x_start:roi_x_end]

        roi_buffer.append(roi)

        if len(roi_buffer) == 3:
            shapes = [r.shape for r in roi_buffer]

            if len(set(shapes)) != 1:
                roi_buffer.clear()
                frame_count += 1
                continue

            avg_roi = np.mean(roi_buffer, axis=0).astype(np.uint8)

            mask = cv2.inRange(avg_roi, LOWER_RED_BIT, UPPER_RED_BIT)

            roi_display = avg_roi.copy()

            binary_matrix = extract_bit_matrix(
                mask,
                roi_display=roi_display,
                rows=FRAME_ROWS,
                cols=FRAME_COLS
            )

            if len(binary_matrix) == BATCH_SIZE:
                all_batches.append(binary_matrix)
            else:
                print(
                    f"Bad batch length: expected {BATCH_SIZE}, got {len(binary_matrix)}"
                )

            on_count = sum(binary_matrix)

            if on_count > 0:
                print(
                    f"Frames {frame_count - 2} to {frame_count}: "
                    f"detected {on_count} active bits."
                )

            roi_display_big = cv2.resize(
                roi_display,
                None,
                fx=DISPLAY_ZOOM,
                fy=DISPLAY_ZOOM,
                interpolation=cv2.INTER_NEAREST
            )

            mask_big = cv2.resize(
                mask,
                None,
                fx=DISPLAY_ZOOM,
                fy=DISPLAY_ZOOM,
                interpolation=cv2.INTER_NEAREST
            )

            cv2.imshow("Target Data Region With Read Points", roi_display_big)
            cv2.imshow("Red Mask View", mask_big)

            roi_buffer.clear()

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()


# ========================================================
# RUN
# ========================================================

scan_video_with_dynamic_origin(
    VIDEO_FILE,
    RELATIVE_START_X,
    RELATIVE_START_Y
)

print(f"Collected {len(all_batches)} batches.")

get_image.get_output_from_bits(all_batches)