import cv2
import numpy as np


def find_red_origin(frame):
    """
    Scans the frame for the 8x8 red calibration square to set the (0,0) origin.
    Uses HSV color space to bypass OBS H.264 color smearing.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower_red_1 = np.array([0, 100, 100])
    upper_red_1 = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red_1, upper_red_1)

    lower_red_2 = np.array([160, 100, 100])
    upper_red_2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red_2, upper_red_2)

    red_mask = mask1 + mask2

    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if 4 <= w <= 15 and 4 <= h <= 15:
            return x, y

    return None, None


def scan_video_with_dynamic_origin(video_path, start_x, start_y):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video at {video_path}. Check the file name and path.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)

    start_frame = int(2 * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    frame_count = start_frame
    origin_x, origin_y = None, None

    search_window_created = False

    # --- TEMPORAL BUFFER DECLARED HERE ---
    roi_buffer = []

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

                if search_window_created:
                    cv2.destroyWindow("Searching for Red Square...")

                verify_img = frame.copy()
                cv2.rectangle(verify_img, (origin_x, origin_y), (origin_x + 15, origin_y + 15), (0, 255, 255), 2)
                cv2.putText(verify_img, "ORIGIN FOUND HERE", (origin_x + 20, origin_y + 15), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 255, 255), 2)

                cv2.namedWindow("Origin Verification", cv2.WINDOW_NORMAL)
                cv2.setWindowProperty("Origin Verification", cv2.WND_PROP_TOPMOST, 1)
                cv2.imshow("Origin Verification", verify_img)
                print(">>> Press ANY KEY on the image window to continue scanning... <<<")
                cv2.waitKey(0)
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

        SEARCH_WIDTH = 250
        SEARCH_HEIGHT = 50

        roi_y_start = data_abs_y - 10
        roi_y_end = data_abs_y + SEARCH_HEIGHT
        roi_x_start = data_abs_x - 10
        roi_x_end = data_abs_x + SEARCH_WIDTH

        height, width, _ = frame.shape
        roi_y_start, roi_y_end = max(0, roi_y_start), min(height, roi_y_end)
        roi_x_start, roi_x_end = max(0, roi_x_start), min(width, roi_x_end)

        roi = frame[roi_y_start:roi_y_end, roi_x_start:roi_x_end]

        # --- 3. THE 3-FRAME BUFFER LOGIC ---
        roi_buffer.append(roi)

        # Only process when we have exactly 3 frames collected
        if len(roi_buffer) == 3:
            # Average the 3 frames to smooth out compression artifacts
            avg_roi = np.mean(roi_buffer, axis=0).astype(np.uint8)

            # We scan the AVERAGED image for our faint red pixels
            lower_bound = np.array([0, 0, 8], dtype=np.uint8)
            upper_bound = np.array([5, 5, 25], dtype=np.uint8)

            mask = cv2.inRange(avg_roi, lower_bound, upper_bound)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            roi_display = avg_roi.copy()
            data_found = False
            on_bits_detected = []

            if contours:
                for contour in contours:
                    cx, cy, cw, ch = cv2.boundingRect(contour)
                    # Increased filter size since bits are now 3x3
                    if cw >= 2 and ch >= 2:
                        cv2.rectangle(roi_display, (cx, cy), (cx + cw, cy + ch), (0, 255, 0), 1)
                        center_x = cx + (cw // 2)
                        center_y = cy + (ch // 2)
                        on_bits_detected.append((center_x, center_y))
                        data_found = True

            cv2.imshow("Target Data Region (Averaged)", roi_display)
            cv2.imshow("Red Mask View (Averaged)", mask)

            if data_found:
                print(f"Frames {frame_count - 2} to {frame_count}: Detected {len(on_bits_detected)} active RED bits.")

            # Clear the buffer so we can grab the next fresh batch of 3 frames
            roi_buffer.clear()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()


# ========================================================
# CONFIGURATION
# ========================================================
VIDEO_FILE = "vid14.mp4"
RELATIVE_START_X = 1024 - 180
RELATIVE_START_Y = 0

scan_video_with_dynamic_origin(VIDEO_FILE, RELATIVE_START_X, RELATIVE_START_Y)