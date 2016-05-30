import cv2
import time
import uuid

BLUR_SIZE = 40
THRESHOLD_SENSITIVITY = 50
LINE_THICKNESS = 1
CIRCLE_SIZE = 5
BLOB_SIZE = 500
BLOB_WIDTH = 60
RESIZE_RATIO = 0.4
DEFAULT_AVERAGE_WEIGHT = 0.04
BLOB_TRACK_TIMEOUT = 0.7
BLOB_LOCKON_DISTANCE_PX = 80
LEFT_POLE_PX = 320
RIGHT_POLE_PX = 500

# vc = cv2.VideoCapture(0)
vc = cv2.VideoCapture('output.mp4')

def nothing(*args, **kwargs):
    print args, kwargs

def get_frame():
    rval, frame = vc.read()
    if rval:
        (h, w) = frame.shape[:2]
        frame = cv2.resize(frame, (int(w * RESIZE_RATIO), int(h * RESIZE_RATIO)), interpolation=cv2.INTER_CUBIC)
    return rval, frame

from itertools import tee, izip
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

# cv2.namedWindow("preview")
# cv2.cv.SetMouseCallback("preview", nothing)

grabbed, frame = get_frame()
avg = None
tracked_blobs = []

hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
(_, _, grayFrame1) = cv2.split(hsvFrame)
start_time = time.time()
while True:
    grabbed, frame = get_frame()

    if not grabbed:
        break

    frame_time = time.time()

    # grayFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    (_, _, grayFrame) = cv2.split(hsvFrame)
    grayFrame = cv2.GaussianBlur(grayFrame, (21, 21), 0)

    if avg is None:
        avg = grayFrame.copy().astype("float")
        continue

    cv2.accumulateWeighted(grayFrame, avg, DEFAULT_AVERAGE_WEIGHT)
    cv2.imshow("average", cv2.convertScaleAbs(avg))

    differenceFrame = cv2.absdiff(grayFrame, cv2.convertScaleAbs(avg))
    cv2.imshow("difference", differenceFrame)

    retval, thresholdImage = cv2.threshold(differenceFrame, THRESHOLD_SENSITIVITY, 255, cv2.THRESH_BINARY)
    thresholdImage = cv2.dilate(thresholdImage, None, iterations=2)
    cv2.imshow("threshold", thresholdImage)

    contours, hierarchy = cv2.findContours(thresholdImage, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    blobs = []
    for c in contours:
        # (x, y, w, h) = cv2.boundingRect(c)
        found_area = cv2.contourArea(c)
        if found_area > BLOB_SIZE:
            blobs.append(c)

    if len(blobs):
        for c in blobs:
            (x, y, w, h) = cv2.boundingRect(c)
            center = (int(x + w/2), int(y + h/2))

            # cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), LINE_THICKNESS)

            # Look for existing blobs that match this one
            closest_blob = None
            if tracked_blobs:
                # Sort the blobs we have seen in previous frames by distance from this one
                closest_blobs = sorted(tracked_blobs, key=lambda b: cv2.norm(b['trail'][0], center))

                # Starting from the closest blob, make sure the blob in question is in the expected direction
                for close_blob in closest_blobs:
                    distance = cv2.norm(center, close_blob['trail'][0])

                    if distance < BLOB_LOCKON_DISTANCE_PX:
                        expected_dir = close_blob['dir']
                        if expected_dir == 'left' and close_blob['trail'][0][0] < center[0]:
                            continue
                        elif expected_dir == 'right' and close_blob['trail'][0][0] > center[0]:
                            continue
                        else:
                            closest_blob = close_blob
                            break

                # print "Closest blob %s" % (closest_blob,)

                if closest_blob:
                    prev_center = closest_blob['trail'][0]
                    if center[0] < prev_center[0]:
                        # It's moving left
                        closest_blob['dir'] = 'left'
                        closest_blob['bumper_x'] = x
                        # print "Blob {} is moving left.".format(closest_blob['id'])
                    else:
                        # It's moving right
                        closest_blob['dir'] = 'right'
                        closest_blob['bumper_x'] = x + w
                        # print "Blob {} is moving right.".format(closest_blob['id'])

                    closest_blob['trail'].insert(0, center)
                    closest_blob['last_seen'] = frame_time

            if not closest_blob:
                b = dict(
                    id=str(uuid.uuid4())[:8],
                    first_seen=frame_time,
                    last_seen=frame_time,
                    dir=None,
                    bumper_x=None,
                    trail=[center],
                )
                tracked_blobs.append(b)

    if tracked_blobs:
        for i in xrange(len(tracked_blobs) - 1, -1, -1):
            if frame_time - tracked_blobs[i]['last_seen'] > BLOB_TRACK_TIMEOUT:
                print "Removing expired track {}".format(tracked_blobs[i]['id'])
                del tracked_blobs[i]

    # Draw the fences
    # cv2.line(frame, (LEFT_POLE_PX, 0), (LEFT_POLE_PX, 700), (100, 100, 100), 2)
    # cv2.line(frame, (RIGHT_POLE_PX, 0), (RIGHT_POLE_PX, 700), (100, 100, 100), 2)

    for blob in tracked_blobs:
        for (a, b) in pairwise(blob['trail']):
            cv2.circle(frame, a, 3, (255, 0, 0), LINE_THICKNESS)

            if blob['dir'] == 'left':
                cv2.line(frame, a, b, (255, 255, 0), LINE_THICKNESS)
            else:
                cv2.line(frame, a, b, (0, 255, 255), LINE_THICKNESS)

            bumper_x = blob['bumper_x']
            if bumper_x:
                cv2.line(frame, (bumper_x, 100), (bumper_x, 500), (255, 0, 255), 3)

            # cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), LINE_THICKNESS)
            # cv2.circle(frame, center, 10, (0, 255, 0), LINE_THICKNESS)

    cv2.imshow("preview", frame)

    grayFrame1 = grayFrame

    key = cv2.waitKey(10)
    if key == 27: # exit on ESC
        break
