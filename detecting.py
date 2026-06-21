import cv2
import numpy as np

# =========================================================================
# הגדרות נתיבים, קבצים ופרמטרים של המשחק
# =========================================================================
VIDEO_PATH = r"C:\Users\TLP\Videos\2026-06-21 21-30-50.mp4"

TEMPLATE_MENU_PATH = r"C:\Users\TLP\Videos\template_menu.png"
TEMPLATE_DEATHS_PATH = r"C:\Users\TLP\Videos\template_deaths.png"
TEMPLATE_TITLE_PATH = r"C:\Users\TLP\Videos\template_title.png"

# מידות הווידאו והמשחק
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
SCREEN_WIDTH = 1278  # הותאם ל-1280
SCREEN_HEIGHT = 800  # הותאם ל-800
TOP_BAR_H = 40

THRESHOLD = 0.75

# טעינת התבניות
template_menu = cv2.imread(TEMPLATE_MENU_PATH, cv2.IMREAD_GRAYSCALE)
template_deaths = cv2.imread(TEMPLATE_DEATHS_PATH, cv2.IMREAD_GRAYSCALE)
template_title = cv2.imread(TEMPLATE_TITLE_PATH, cv2.IMREAD_GRAYSCALE)

# =========================================================================
# הגדרות קיזוזים (Offsets) - כאן מכיילים את הדיוק!
# המספרים האלו מציינים: כמה פיקסלים התבנית שגזרת רחוקה מהפינה השמאלית-עליונה של הקנבס (הפס השחור)
# =========================================================================
# אם הריבוע הירוק סוטה ימינה, הקטן את ערך ה-X. אם סוטה למטה, הקטן את ערך ה-Y.
OFFSET_MENU_X = 16
OFFSET_MENU_Y = 10  # (mid=20, פחות חצי גובה הטקסט)

OFFSET_DEATHS_X = 1130  # בערך המרחק מהקצה השמאלי עד למילה DEATHS (תלוי איך גזרת)
OFFSET_DEATHS_Y = 10

# הכותרת של החלון בדרך כלל נמצאת בערך 31-35 פיקסלים מעל הקנבס, וקצת שמאלה.
# לכן ה-Y פה הוא שלילי (כי הכותרת מעל הפס השחור).
OFFSET_TITLE_X = -8
OFFSET_TITLE_Y = -31


def match_element(frame_gray, template):
    if template is None:
        return None, 0
    res = cv2.matchTemplate(frame_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val >= THRESHOLD:
        return max_loc, max_val
    return None, max_val


# =========================================================================
# פונקציית הזיהוי
# מחזירה את הפינה השמאלית-עליונה של הפס השחור של המשחק
# =========================================================================
def detect_location(frame):
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 1. ניסיון זיהוי לפי הכותרת
    if template_title is not None:
        loc, score = match_element(frame_gray, template_title)
        if loc:
            window_x = loc[0] - OFFSET_TITLE_X
            window_y = loc[1] - OFFSET_TITLE_Y
            return window_x, window_y, "TITLE", score

    # 2. ניסיון זיהוי לפי MENU
    if template_menu is not None:
        loc, score = match_element(frame_gray, template_menu)
        if loc:
            window_x = loc[0] - OFFSET_MENU_X
            window_y = loc[1] - OFFSET_MENU_Y
            return window_x, window_y, "MENU", score

    # 3. ניסיון זיהוי לפי DEATHS
    if template_deaths is not None:
        loc, score = match_element(frame_gray, template_deaths)
        if loc:
            window_x = loc[0] - OFFSET_DEATHS_X
            window_y = loc[1] - OFFSET_DEATHS_Y
            return window_x, window_y, "DEATHS", score

    return None, None, "", 0


# =========================================================================
# הלולאה הראשית
# =========================================================================
if __name__ == "__main__":
    cap = cv2.VideoCapture(VIDEO_PATH)

    if not cap.isOpened():
        print(f"Error: Could not open video file at {VIDEO_PATH}")
    else:
        print("Starting detection loop. Press 'q' to exit.")

        # יצירת חלון בגודל מותאם אישית שיהיה נוח לראות על המסך
        cv2.namedWindow("Game Detection System", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Game Detection System", 1400, 900)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT))

            window_x, window_y, method, score = detect_location(frame)

            if window_x is not None and window_y is not None:
                # הריבוע הירוק יעטוף בדיוק את הקנבס עצמו
                cv2.rectangle(frame, (int(window_x), int(window_y)),
                              (int(window_x + SCREEN_WIDTH), int(window_y + SCREEN_HEIGHT)),
                              (0, 255, 0), 2)

                # פס למעלה שידגיש את הבר השחור בלבד (לבדיקה חזותית)
                cv2.rectangle(frame, (int(window_x), int(window_y)),
                              (int(window_x + SCREEN_WIDTH), int(window_y + TOP_BAR_H)),
                              (255, 0, 0), 1)

                text_to_display = f"Top-Left (Canvas): ({int(window_x)}, {int(window_y)}) | Method: {method} (Score: {score:.2f})"
                cv2.putText(frame, text_to_display,
                            (int(window_x), int(window_y) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "Game Window Not Found", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow("Game Detection System", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()