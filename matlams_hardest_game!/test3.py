import cv2
import numpy as np
import os

CALIBRATION_X = 0
CALIBRATION_Y = 0
MATCH_THRESHOLD = 0.7
ROI_SIZE = 20
template_img = cv2.imread(r".\template_title.png")
#current_dir = os.path.dirname(os.path.abspath(__file__))
#template_path = os.path.join(current_dir, 'template_title.png')
#template_img = cv2.imread(template_path)

template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)


def detect_corner(frame, template_gray):
    """
    מקבלת פריים בודד (BGR) ותבנית טעונה מראש (Grayscale),
    ומחזירה את קואורדינטות ה-(X, Y) המדויקות של הפינה.
    אם לא נמצאה התאמה, מחזירה None.
    """
    # המרת הפריים לגווני אפור עבור התאמת התבנית
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # שלב 1: מציאת מיקום גס באמצעות התאמת תבנית
    res = cv2.matchTemplate(gray_frame, template_gray, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    # אם הביטחון בזיהוי נמוך מהסף, כנראה שהחלון לא במסך
    if max_val < MATCH_THRESHOLD:
        return None

    t_h, t_w = template_gray.shape
    coarse_x = max_loc[0]
    coarse_y = max_loc[1] + t_h  # יורדים לתחתית שורת הכותרת

    # שלב 2: הגדרת אזור חיפוש מקומי (ROI) סביב הפינה המשוערת
    roi_start_y = max(0, coarse_y - ROI_SIZE)
    roi_end_y = min(frame.shape[0], coarse_y + ROI_SIZE)
    roi_start_x = max(0, coarse_x - ROI_SIZE)
    roi_end_x = min(frame.shape[1], coarse_x + ROI_SIZE)

    corner_roi = frame[roi_start_y:roi_end_y, roi_start_x:roi_end_x]
    gray_roi = cv2.cvtColor(corner_roi, cv2.COLOR_BGR2GRAY)

    # שלב 3: זיהוי קווים מדויק בתוך ה-ROI
    edges = cv2.Canny(gray_roi, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 20, minLineLength=10, maxLineGap=5)

    # ברירת מחדל: המיקום הגס (ביחס ל-ROI)
    precise_local_x = coarse_x - roi_start_x
    precise_local_y = coarse_y - roi_start_y

    if lines is not None:
        horiz_lines = []
        vert_lines = []

        # הפרדת קווים אופקיים ואנכיים
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y1 - y2) < 3:
                horiz_lines.append((x1, y1, x2, y2))
            elif abs(x1 - x2) < 3:
                vert_lines.append((x1, y1, x2, y2))

        # מציאת הקו הקרוב ביותר למרכז האזור שחיפשנו
        if horiz_lines:
            horiz_lines.sort(key=lambda l: abs(l[1] - corner_roi.shape[0] / 2))
            precise_local_y = horiz_lines[0][1]

        if vert_lines:
            vert_lines.sort(key=lambda l: abs(l[0] - corner_roi.shape[1] / 2))
            precise_local_x = vert_lines[0][0]

    # שלב 4: חישוב הקואורדינטות הסופיות ביחס לפריים המקורי + כיול
    final_x = int(precise_local_x + roi_start_x + CALIBRATION_X)
    final_y = int(precise_local_y + roi_start_y + CALIBRATION_Y)

    return (final_x, final_y)




def extract_bit_matrix(mask, rows=5, cols=32):
    """
    ממיר את ה-mask למטריצה של ביטים.
    הנחת עבודה: ה-mask הוא תמונה בינארית (0 או 255).
    """
    height, width = mask.shape
    matrix = np.zeros((rows, cols), dtype=int)

    # גודל כל תא בפיקסלים
    cell_h = height // rows
    cell_w = width // cols

    for r in range(rows):
        for c in range(cols):
            # הגדרת אזור העניין (התא) בתוך ה-mask
            y1, y2 = r * cell_h, (r + 1) * cell_h
            x1, x2 = c * cell_w, (c + 1) * cell_w

            # בדיקת האזור: אם יש מספיק פיקסלים לבנים (למשל יותר מ-20% מהתא)
            cell = mask[y1:y2, x1:x2]
            if np.sum(cell > 0) > (cell.size * 0.2):
                matrix[r, c] = 1

    return matrix


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

        corner = detect_corner(frame, template_gray)

        if corner:
            origin_x, origin_y = corner


            # סימון ויזואלי לבדיקה
            cv2.drawMarker(frame, (origin_x, origin_y), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
        else:
            print("Corner not detected in this frame.")

        # הצגת הפריים לבדיקה ויזואלית
        cv2.imshow('Detection Test', frame)

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

            #cv2.imshow("Target Data Region (Averaged)", roi_display)
            cv2.imshow("Red Mask View (Averaged)", mask)
            binary_matrix = extract_bit_matrix(mask, rows=5, cols=35)
            print(binary_matrix)

            #grid = extract_bit_matrix(mask)
            #print("!\n")
            #print(grid)
            #print("!\n")

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
VIDEO_FILE = "vid15.mp4"
RELATIVE_START_X = 1024 - 180
RELATIVE_START_Y = 0

scan_video_with_dynamic_origin(VIDEO_FILE, RELATIVE_START_X, RELATIVE_START_Y)



