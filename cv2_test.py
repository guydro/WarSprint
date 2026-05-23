import cv2
from PIL import Image, ImageFont, ImageDraw, ImageOps
import numpy as np

def test_camera(cap):
    key = "N"

    while key not in [121, 89, 232]:
        if not cap.isOpened():
            return "Failed, cannot open camera."

        ret, frame = cap.read()

        if not ret:
            return "Failed, cannot grab frame."

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        image = ImageOps.expand(image, border=(0, 100, 0, 0), fill=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("FONTS/arial.ttf", 30)
        text1 = "לחצו Y אם אתם מרוצים מהתמונה, ו-N אחרת."
        text2 = "לאחר שאתם מאשרים, תכתבו את השם שלכם בקונסולה."
        draw.text((0, 0), text1[::-1]+"\n"+text2[::-1], (0, 0, 0), font=font)
        drawn_frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        cv2.imshow("OpenCV Image", drawn_frame)
        key = cv2.waitKey(0)  # waits indefinitely until a key is pressed
        cv2.destroyAllWindows()

    cv2.imwrite(f"./images/{input("Please enter your name, after that please make a push and make sure it was uploaded to github: ")}.png", frame)



cap = cv2.VideoCapture(0)
test_camera(cap)
cap.release()