import cv2
import numpy as np

# ==========================================
# פרמטרי כיול והגדרות גלובליות
# ==========================================
CALIBRATION_X = 0
CALIBRATION_Y = 0
MATCH_THRESHOLD = 0.7
ROI_SIZE = 20


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


""""
# --- אזור האתחול של התוכנית ---
# טוענים את התבנית פעם אחת לזיכרון וממירים לאפור
template_img = cv2.imread(r)
if template_img is not None:
    TEMPLATE_GRAY = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
else:
    raise FileNotFoundError("לא ניתן למצוא את template_title.png")

# --- בתוך הלולאה שעוברת על הפריימים ---
# נניח ש- current_frame הוא התמונה ששלפת עכשיו (בפורמט BGR של OpenCV)
corner_position = detect_corner(current_frame, TEMPLATE_GRAY)

if corner_position:
    corner_x, corner_y = corner_position
    # עכשיו יש לך את ה-X וה-Y המדויקים, ואפשר להשתמש בהם!
else:
    pass # החלון לא זוהה בפריים הנוכחי


"""

import cv2

# --- טעינה ראשונית (מחוץ ללולאה - חשוב לביצועים) ---
template_img = cv2.imread(r".\template_title.png")
template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

# פתיחת הוידאו
cap = cv2.VideoCapture(r"C:\Users\TLP\Videos\2026-06-21 23-28-24.mp4")

while cap.isOpened():
    ret, current_frame = cap.read()
    if not ret:
        break

    # קריאה לפונקציית הזיהוי (כפי שהגדרנו)
    corner = detect_corner(current_frame, template_gray)

    if corner:
        x, y = corner
        print(f"Corner found at: X={x}, Y={y}")

        # סימון ויזואלי לבדיקה
        cv2.drawMarker(current_frame, (x, y), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
    else:
        print("Corner not detected in this frame.")

    # הצגת הפריים לבדיקה ויזואלית
    cv2.imshow('Detection Test', current_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()