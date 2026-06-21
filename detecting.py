import cv2
import numpy as np

# =========================================================================
# שלב 1: הגדרות נתיבים, קבצים ופרמטרים של המשחק
# =========================================================================
# הכנס כאן את הנתיב לקובץ הווידאו שלך
VIDEO_PATH = r"C:\Users\TLP\Videos\2026-06-21 20-49-41.mp4"

# נתיבים לתמונות הטמפלייט (החלקים שנגזור לצורך זיהוי)
TEMPLATE_MENU_PATH = r"C:\Users\TLP\Videos\template_title.png"
TEMPLATE_DEATHS_PATH = r"C:\Users\TLP\Videos\template_title.png"
TEMPLATE_TITLE_PATH = r"C:\Users\TLP\Videos\template_menu.png"

# מימדי המשחק המקוריים (לפי ה-Config של המשחק שלך, שנה במידת הצורך)
SCREEN_WIDTH = 800  # דוגמה, שנה לרוחב האמיתי של המשחק בקוד
SCREEN_HEIGHT = 600  # דוגמה, שנה לגובה האמיתי של המשחק בקוד
TOP_BAR_H = 40  # גובה הבר העליון (HUD)

# סף רגישות לזיהוי (בין 0 ל-1). 0.8 זו נקודת התחלה טובה
THRESHOLD = 0.8

# =========================================================================
# טעינת הטמפלייטים במצב גווני אפור (Grayscale)
# =========================================================================
template_menu = cv2.imread(TEMPLATE_MENU_PATH, cv2.IMREAD_GRAYSCALE)
template_deaths = cv2.imread(TEMPLATE_DEATHS_PATH, cv2.IMREAD_GRAYSCALE)
template_title = cv2.imread(TEMPLATE_TITLE_PATH, cv2.IMREAD_GRAYSCALE)

def resize_to_fit(img, max_width=1280, max_height=720):
    h, w = img.shape[:2]

    scale = min(max_width / w, max_height / h, 1.0)

    new_w = int(w * scale)
    new_h = int(h * scale)

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized

# פונקציית עזר לביצוע התאמת תבנית (Template Matching)
def match_element(frame_gray, template):
    if template is None:
        return None, 0
    w, h = template.shape[::-1]
    res = cv2.matchTemplate(frame_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val >= THRESHOLD:
        return max_loc, max_val  # נקודת הפינה השמאלית-עליונה של האלמנט שנמצא
    return None, max_val


# =========================================================================
# שלב 2: לולאת הרצה וסריקה תמידית על סרטון הווידאו
# =========================================================================
cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print(f"Error: Could not open video file at {VIDEO_PATH}")
    print("Please make sure the path is correct and templates are created.")

print("Starting detection loop. Press 'q' to exit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("End of video or cannot read frame.")
        break

    # המרה לגווני אפור לצורך זיהוי מהיר ומדויק יותר
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    window_detected = False
    window_x, window_y = 0, 0
    detection_method = ""

    # ---------------------------------------------------------------------
    # אופן זיהוי 1: לפי כיתוב הטקסט "MENU"
    # ---------------------------------------------------------------------
    if not window_detected and template_menu is not None:
        loc, score = match_element(frame_gray, template_menu)
        if loc:
            # לפי קוד המשחק: midleft=(16, mid). הטקסט מתחיל ב-X=16
            window_x = loc[0] - 16
            # מציאת ה-Y ביחס לגובה הבר העליון
            window_y = loc[1] - (TOP_BAR_H // 2 - template_menu.shape[0] // 2)
            detection_method = f"MENU (Score: {score:.2f})"
            window_detected = True

    # ---------------------------------------------------------------------
    # אופן זיהוי 2: לפי כיתוב הטקסט "DEATHS"
    # ---------------------------------------------------------------------
    if not window_detected and template_deaths is not None:
        loc, score = match_element(frame_gray, template_deaths)
        if loc:
            # לפי קוד המשחק: midright=(SCREEN_WIDTH - 16, mid)
            # לכן הפינה הימנית של הטקסט היא ב-SCREEN_WIDTH - 16
            # הפינה השמאלית שזיהינו (loc[0]) פלוס רוחב הטמפלייט שווה לימין הטקסט
            text_right_x = loc[0] + template_deaths.shape[1]
            window_x = text_right_x - (SCREEN_WIDTH - 16)
            window_y = loc[1] - (TOP_BAR_H // 2 - template_deaths.shape[0] // 2)
            detection_method = f"DEATHS (Score: {score:.2f})"
            window_detected = True

    # ---------------------------------------------------------------------
    # אופן זיהוי 3: לפי שם החלון "The Matlam's Hardest Game" (בר הכותרת של Windows)
    # ---------------------------------------------------------------------
    if not window_detected and template_title is not None:
        loc, score = match_element(frame_gray, template_title)
        if loc:
            # בר הכותרת נמצא מעל תוכן המשחק. נצטרך להתאים את האופסט (Offset)
            # בהתאם למקום המדויק ממנו גזרת את הטמפלייט של הכותרת.
            window_x = loc[0] - 10  # דוגמה לאופסט שמאלי מהאייקון/טקסט
            window_y = loc[1]  # הפינה העליונה של חלון ה-OS
            detection_method = f"Window Title (Score: {score:.2f})"
            window_detected = True

    # ---------------------------------------------------------------------
    # ציור התוצאה על המסך במידה ונמצא מיקום
    # ---------------------------------------------------------------------
    if window_detected:
        # ציור מלבן מסביב לכל גבולות המשחק המשוערים
        cv2.rectangle(frame, (int(window_x), int(window_y)),
                      (int(window_x + SCREEN_WIDTH), int(window_y + SCREEN_HEIGHT)),
                      (0, 255, 0), 2)

        # כתיבת שיטת הזיהוי הנוכחית מעל המלבן
        cv2.putText(frame, f"Detected via: {detection_method}",
                    (int(window_x), int(window_y) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "Game Window Not Found", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    display_frame = resize_to_fit(frame, max_width=1280, max_height=720)

    cv2.imshow("Game Detection System", display_frame)

    print("original:", frame.shape, "display:", display_frame.shape)

    # יציאה בלחיצה על המקש 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()