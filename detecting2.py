import cv2
import numpy as np
import csv


# ============================================================
# HARDCODED PATHS
# ============================================================

VIDEO_PATH = r"C:\Users\TLP\Desktop\recording.mp4"
REFERENCE_IMAGE_PATH = r"C:\Users\TLP\Desktop\reference.png"

OUTPUT_VIDEO_PATH = r"C:\Users\TLP\Desktop\annotated_detection.mp4"
OUTPUT_CSV_PATH = r"C:\Users\TLP\Desktop\detections.csv"


# ============================================================
# SETTINGS
# ============================================================

# This is the position of the word PLAY inside the reference screenshot only.
# It is NOT the location of the game in the screen recording.
#
# Format:
# x, y, width, height
PLAY_CROP_IN_REFERENCE = (575, 370, 145, 60)

# If detections are missed, lower this to 0.35 or 0.40.
# If false detections happen, raise this to 0.60.
MATCH_THRESHOLD = 0.45

# Allows the game window to appear at a different size in the recording.
MIN_SCALE = 0.55
MAX_SCALE = 1.70
SCALE_STEP = 0.05

# 1 = process every frame.
# 2 = process every second frame, faster but less exact.
PROCESS_EVERY_N_FRAMES = 1

# In your reference screenshot, the purple game canvas starts below the title bar.
# Approximate y-position of the canvas inside the reference image.
CANVAS_TOP_IN_REFERENCE = 38


# ============================================================
# IMAGE PROCESSING
# ============================================================

def play_text_shape_mask(bgr):
    """
    Makes a mask based on edges/shapes, not color.

    This is useful because the PLAY background may be white, green, or dark.
    We are matching the shape of the letters instead of the button color.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Reduce video compression noise.
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Detect edges of letters.
    edges = cv2.Canny(gray, 50, 150)

    # Make strokes slightly thicker.
    kernel = np.ones((2, 2), dtype=np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)

    return edges


def detect_play_anywhere(frame, play_template):
    """
    Searches the whole video frame for the PLAY text.
    """
    frame_mask = play_text_shape_mask(frame)
    template_mask_original = play_text_shape_mask(play_template)

    best_detection = None

    scale = MIN_SCALE

    while scale <= MAX_SCALE + 1e-9:
        template_w = int(template_mask_original.shape[1] * scale)
        template_h = int(template_mask_original.shape[0] * scale)

        if template_w < 10 or template_h < 10:
            scale += SCALE_STEP
            continue

        if template_w >= frame.shape[1] or template_h >= frame.shape[0]:
            scale += SCALE_STEP
            continue

        template_mask = cv2.resize(
            template_mask_original,
            (template_w, template_h),
            interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
        )

        result = cv2.matchTemplate(
            frame_mask,
            template_mask,
            cv2.TM_CCOEFF_NORMED,
        )

        _, score, _, top_left = cv2.minMaxLoc(result)

        if best_detection is None or score > best_detection["score"]:
            x, y = top_left

            best_detection = {
                "score": float(score),
                "scale": float(scale),
                "play_rect": (x, y, template_w, template_h),
            }

        scale += SCALE_STEP

    return best_detection


def estimate_game_window_from_play(play_detection, reference_shape):
    """
    Once PLAY is found in the video, estimate the whole game window.

    This works because we know where PLAY is located inside the reference image.
    """
    ref_h, ref_w = reference_shape[:2]

    ref_play_x, ref_play_y, ref_play_w, ref_play_h = PLAY_CROP_IN_REFERENCE

    detected_play_x, detected_play_y, detected_play_w, detected_play_h = play_detection["play_rect"]
    scale = play_detection["scale"]

    window_x = int(round(detected_play_x - ref_play_x * scale))
    window_y = int(round(detected_play_y - ref_play_y * scale))
    window_w = int(round(ref_w * scale))
    window_h = int(round(ref_h * scale))

    return window_x, window_y, window_w, window_h


def estimate_game_canvas_from_window(window_rect, reference_shape):
    """
    Estimates the actual game canvas, excluding the title bar.
    """
    window_x, window_y, window_w, window_h = window_rect

    ref_h = reference_shape[0]
    canvas_top_ratio = CANVAS_TOP_IN_REFERENCE / ref_h

    title_bar_h = int(round(window_h * canvas_top_ratio))

    canvas_x = window_x
    canvas_y = window_y + title_bar_h
    canvas_w = window_w
    canvas_h = window_h - title_bar_h

    return canvas_x, canvas_y, canvas_w, canvas_h


def clamp_rect(rect, frame_shape):
    """
    Prevents rectangles from going outside the video frame.
    """
    x, y, w, h = rect
    frame_h, frame_w = frame_shape[:2]

    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(frame_w, x + w)
    y2 = min(frame_h, y + h)

    return x1, y1, max(0, x2 - x1), max(0, y2 - y1)


def draw_rect(frame, rect, label, color):
    x, y, w, h = rect

    cv2.rectangle(
        frame,
        (x, y),
        (x + w, y + h),
        color,
        2,
    )

    cv2.putText(
        frame,
        label,
        (x, max(25, y - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        color,
        2,
        cv2.LINE_AA,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    reference = cv2.imread(REFERENCE_IMAGE_PATH)

    if reference is None:
        raise FileNotFoundError(f"Could not read reference image: {REFERENCE_IMAGE_PATH}")

    ref_x, ref_y, ref_w, ref_h = PLAY_CROP_IN_REFERENCE
    play_template = reference[ref_y:ref_y + ref_h, ref_x:ref_x + ref_w]

    if play_template.size == 0:
        raise ValueError("PLAY_CROP_IN_REFERENCE is invalid. Check the crop values.")

    cap = cv2.VideoCapture(VIDEO_PATH)

    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {VIDEO_PATH}")

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        fps = 30

    video_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    video_writer = cv2.VideoWriter(
        OUTPUT_VIDEO_PATH,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (video_w, video_h),
    )

    detections = []
    last_good_detection = None

    frame_index = 0

    while True:
        ok, frame = cap.read()

        if not ok:
            break

        if frame_index % PROCESS_EVERY_N_FRAMES == 0:
            detection = detect_play_anywhere(frame, play_template)

            if detection is not None and detection["score"] >= MATCH_THRESHOLD:
                window_rect = estimate_game_window_from_play(
                    detection,
                    reference.shape,
                )

                canvas_rect = estimate_game_canvas_from_window(
                    window_rect,
                    reference.shape,
                )

                window_rect = clamp_rect(window_rect, frame.shape)
                canvas_rect = clamp_rect(canvas_rect, frame.shape)

                detection["window_rect"] = window_rect
                detection["canvas_rect"] = canvas_rect

                last_good_detection = detection

                px, py, pw, ph = detection["play_rect"]
                wx, wy, ww, wh = window_rect
                cx, cy, cw, ch = canvas_rect

                detections.append({
                    "frame": frame_index,
                    "time_sec": frame_index / fps,
                    "score": detection["score"],
                    "scale": detection["scale"],

                    "play_x": px,
                    "play_y": py,
                    "play_w": pw,
                    "play_h": ph,

                    "window_x": wx,
                    "window_y": wy,
                    "window_w": ww,
                    "window_h": wh,

                    "canvas_x": cx,
                    "canvas_y": cy,
                    "canvas_w": cw,
                    "canvas_h": ch,
                })

        if last_good_detection is not None:
            draw_rect(
                frame,
                last_good_detection["play_rect"],
                "PLAY",
                (0, 255, 255),
            )

            draw_rect(
                frame,
                last_good_detection["window_rect"],
                "GAME WINDOW",
                (0, 255, 0),
            )

            draw_rect(
                frame,
                last_good_detection["canvas_rect"],
                "GAME CANVAS",
                (255, 0, 0),
            )

            cv2.putText(
                frame,
                f"score={last_good_detection['score']:.3f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        video_writer.write(frame)
        frame_index += 1

    cap.release()
    video_writer.release()

    with open(OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "frame",
            "time_sec",
            "score",
            "scale",

            "play_x",
            "play_y",
            "play_w",
            "play_h",

            "window_x",
            "window_y",
            "window_w",
            "window_h",

            "canvas_x",
            "canvas_y",
            "canvas_w",
            "canvas_h",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(detections)

    print("Done.")
    print(f"Saved annotated video to: {OUTPUT_VIDEO_PATH}")
    print(f"Saved detections CSV to: {OUTPUT_CSV_PATH}")
    print(f"Number of detections: {len(detections)}")


if __name__ == "__main__":
    main()