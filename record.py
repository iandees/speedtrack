import cv2

vc = cv2.VideoCapture(0)

def get_frame():
    rval, frame = vc.read()
    # (h, w) = frame.shape[:2]
    # frame = cv2.resize(frame, (int(w * RESIZE_RATIO), int(h * RESIZE_RATIO)), interpolation=cv2.INTER_CUBIC)
    return rval, frame

grabbed, frame = get_frame()

fourcc = cv2.cv.CV_FOURCC(*'mp4v')
(h, w) = frame.shape[:2]
writer = cv2.VideoWriter('output.mp4', fourcc, 40.0, (w, h))

while True:
    # grabbed, frame = vc.read()
    grabbed, frame = get_frame()
    writer.write(frame)
    # cv2.imshow("live", frame)
