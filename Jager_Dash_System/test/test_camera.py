import cv2

def init_camera():
    cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)

    if not cap.isOpened():
        print("Camera failed to open")
        exit()

    # Optimize performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FPS, 15)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return cap

if __name__ == "__main__":
    cap = init_camera()

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Frame not received")
            break

        cv2.imshow("Camera", frame)

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
