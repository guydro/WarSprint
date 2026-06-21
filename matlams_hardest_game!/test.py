import cv2
import numpy as np


def find_red_origin(frame):
    """
    Scans the frame for the 8x8 red calibration square to set the (0,0) origin.
    Uses HSV color space to bypass OBS H.264 color smearing.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # In HSV, red wraps around the 0-180 hue spectrum. We need two masks.
    # Lower bound red
    lower_red_1 = np.array([0, 100, 100])
    upper_red_1 = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red_1, upper_red_1)

    # Upper bound red
    lower_red_2 = np.array([160, 100, 100])
    upper_red_2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red_2, upper_red_2)

    # Combine masks
    red_mask = mask1 + mask2

    # Find contours of the red objects
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        # Look for a small square roughly the size of our 8x8 marker.
        # We allow a range (4 to 15) because OBS compression will blur its edges.
        if 4 <= w <= 15 and 4 <= h <= 15:
            return x, y  # Return the top-left corner as the absolute origin

    return None, None


def scan_video_with_dynamic_origin(video_path, start_x, start_y):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video at {video_path}. Check the file name and path.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)

    start_frame = int(1*fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    frame_count = start_frame
    origin_x, origin_y = None, None

    # [THE FIX] Track if the window was ever actually created
    search_window_created = False

    print("Starting video scan...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Reached the end of the video or video could not be read.")
            break

        # 1. FIND THE ORIGIN
        if origin_x is None or origin_y is None:
            origin_x, origin_y = find_red_origin(frame)
            if origin_x is not None:
                print(f"[+] Origin Calibration Locked at Absolute Coords: X={origin_x}, Y={origin_y}")

                # Only destroy if it exists
                if search_window_created:
                    cv2.destroyWindow("Searching for Red Square...")

                # [TACTICAL ADDITION] Show you exactly what it locked onto!
                verify_img = frame.copy()
                cv2.rectangle(verify_img, (origin_x, origin_y), (origin_x + 15, origin_y + 15), (0, 255, 255), 2)
                cv2.putText(verify_img, "ORIGIN FOUND HERE", (origin_x + 20, origin_y + 15), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 255, 255), 2)

                cv2.namedWindow("Origin Verification", cv2.WINDOW_NORMAL)
                cv2.setWindowProperty("Origin Verification", cv2.WND_PROP_TOPMOST, 1)
                cv2.imshow("Origin Verification", verify_img)
                print(">>> Press ANY KEY on the image window to continue scanning... <<<")
                cv2.waitKey(0)  # Pauses the script indefinitely until you press a key
                cv2.destroyWindow("Origin Verification")

            else:
                cv2.namedWindow("Searching for Red Square...", cv2.WINDOW_NORMAL)
                cv2.setWindowProperty("Searching for Red Square...", cv2.WND_PROP_TOPMOST, 1)
                cv2.imshow("Searching for Red Square...", frame)
                search_window_created = True
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                frame_count += 1
                continue

        # 2. CALCULATE ABSOLUTE COORDINATES FOR YOUR DATA
        data_abs_x = origin_x + start_x
        data_abs_y = origin_y + start_y

        roi_y_start = data_abs_y - 10
        roi_y_end = data_abs_y + 40
        roi_x_start = data_abs_x - 10
        roi_x_end = data_abs_x + 500

        height, width, _ = frame.shape
        roi_y_start, roi_y_end = max(0, roi_y_start), min(height, roi_y_end)
        roi_x_start, roi_x_end = max(0, roi_x_start), min(width, roi_x_end)

        roi = frame[roi_y_start:roi_y_end, roi_x_start:roi_x_end]

        # 3. SCAN FOR GRAY DATA PIXELS
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        lower_bound = 10
        upper_bound = 45
        mask = cv2.inRange(gray_roi, lower_bound, upper_bound)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        roi_display = roi.copy()
        data_found = False

        if contours:
            for contour in contours:
                cx, cy, cw, ch = cv2.boundingRect(contour)
                if cw >= 1 and ch >= 1:
                    cv2.rectangle(roi_display, (cx, cy), (cx + cw, cy + ch), (0, 255, 0), 1)
                    data_found = True

        # Always show the tracking window once the origin is found
        cv2.imshow("Target Data Region", roi_display)

        if data_found:
            print(f"Data detected at Frame {frame_count}")

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()


# ========================================================
# CONFIGURATION
# ========================================================
# Replace with your actual video filename
VIDEO_FILE = "vid3.mp4"

# Set your relative coordinates from Pygame here!
# For example, if your payload was drawn at:
# x = C.SCREEN_WIDTH - 200
# y = C.TOP_BAR_H // 2
# Note: Assuming 1920x1080 game config, C.SCREEN_WIDTH is 1920, so x = 1720.

RELATIVE_START_X = 1720
RELATIVE_START_Y = 20

scan_video_with_dynamic_origin(VIDEO_FILE, RELATIVE_START_X, RELATIVE_START_Y)