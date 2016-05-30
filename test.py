import cv2
import time
import uuid

#
# Tracks cars out my window using OpenCV.
#
# This works by keeping track of a running average for the scene and
# subtracting the average from the current frame to find the parts
# that are different/moving (like cars). The difference is processed
# to find the bounding box of these car-sized changes.
#
# Once the blobs are found, they are compared with previously-found
# blobs so that we can track the progress of blobs across the image.
# From those tracks we can compute speed and also count the number
# of cars crossing the field of view in each direction.
#

# The cutoff for threshold. A lower number means smaller changes between
# the average and current scene are more readily detected.
THRESHOLD_SENSITIVITY = 50
# Number of pixels in each direction to blur the difference between
# average and current scene. This helps make small differences larger
# and more detectable.
BLUR_SIZE = 40
# The number of square pixels a blob must be before we consider it a
# candidate for tracking.
BLOB_SIZE = 500
# The number of pixels wide a blob must be before we consider it a
# candidate for tracking.
BLOB_WIDTH = 60
# The weighting to apply to "this" frame when averaging. A higher number
# here means that the average scene will pick up changes more readily,
# thus making the difference between average and current scenes smaller.
DEFAULT_AVERAGE_WEIGHT = 0.04
# The maximum distance a blob centroid is allowed to move in order to
# consider it a match to a previous scene's blob.
BLOB_LOCKON_DISTANCE_PX = 80
# The number of seconds a blob is allowed to sit around without having
# any new blobs matching it.
BLOB_TRACK_TIMEOUT = 0.7
# The left and right X positions of the "poles". These are used to
# track the speed of a vehicle across the scene.
LEFT_POLE_PX = 320
RIGHT_POLE_PX = 500
# Constants for drawing on the frame.
LINE_THICKNESS = 1
CIRCLE_SIZE = 5
RESIZE_RATIO = 0.4

## Set up a video capture device (number for webcam, filename for video file input)
# vc = cv2.VideoCapture(0)
vc = cv2.VideoCapture('output.mp4')

def nothing(*args, **kwargs):
    " A helper function to use for OpenCV slider windows. "
    print args, kwargs

def get_frame():
    " Grabs a frame from the video capture and resizes it. "
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

# A variable to store the running average.
avg = None
# A list of "tracked blobs".
tracked_blobs = []

while True:
    # Grab the next frame from the camera or video file
    grabbed, frame = get_frame()

    if not grabbed:
        # If we fall into here it's because we ran out of frames
        # in the video file.
        break

    frame_time = time.time()

    # Convert the frame to Hue Saturation Value (HSV) color space.
    hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # Only use the Value channel of the frame.
    (_, _, grayFrame) = cv2.split(hsvFrame)
    # Apply a blur to the frame to smooth out any instantaneous changes
    # like leaves glinting in sun or birds flying around.
    grayFrame = cv2.GaussianBlur(grayFrame, (21, 21), 0)

    if avg is None:
        # Set up the average if this is the first time through.
        avg = grayFrame.copy().astype("float")
        continue

    # Build the average scene image by accumulating this frame
    # with the existing average.
    cv2.accumulateWeighted(grayFrame, avg, DEFAULT_AVERAGE_WEIGHT)
    cv2.imshow("average", cv2.convertScaleAbs(avg))

    # Compute the grayscale difference between the current grayscale frame and
    # the average of the scene.
    differenceFrame = cv2.absdiff(grayFrame, cv2.convertScaleAbs(avg))
    cv2.imshow("difference", differenceFrame)

    # Apply a threshold to the difference: any pixel value above the sensitivity
    # value will be set to 255 and any pixel value below will be set to 0.
    retval, thresholdImage = cv2.threshold(differenceFrame, THRESHOLD_SENSITIVITY, 255, cv2.THRESH_BINARY)
    thresholdImage = cv2.dilate(thresholdImage, None, iterations=2)
    cv2.imshow("threshold", thresholdImage)

    # Find contours aka blobs in the threshold image.
    contours, hierarchy = cv2.findContours(thresholdImage, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter out the blobs that are too small to be considered cars.
    blobs = filter(lambda c: cv2.contourArea(c) > BLOB_SIZE, contours)

    if blobs:
        for c in blobs:
            # Find the bounding rectangle and center for each blob
            (x, y, w, h) = cv2.boundingRect(c)
            center = (int(x + w/2), int(y + h/2))

            ## Optionally draw the rectangle around the blob on the frame that we'll show in a UI later
            # cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), LINE_THICKNESS)

            # Look for existing blobs that match this one
            closest_blob = None
            if tracked_blobs:
                # Sort the blobs we have seen in previous frames by pixel distance from this one
                closest_blobs = sorted(tracked_blobs, key=lambda b: cv2.norm(b['trail'][0], center))

                # Starting from the closest blob, make sure the blob in question is in the expected direction
                for close_blob in closest_blobs:
                    distance = cv2.norm(center, close_blob['trail'][0])

                    # Check if the distance is close enough to "lock on"
                    if distance < BLOB_LOCKON_DISTANCE_PX:
                        # If it's close enough, make sure the blob was moving in the expected direction
                        expected_dir = close_blob['dir']
                        if expected_dir == 'left' and close_blob['trail'][0][0] < center[0]:
                            continue
                        elif expected_dir == 'right' and close_blob['trail'][0][0] > center[0]:
                            continue
                        else:
                            closest_blob = close_blob
                            break

                if closest_blob:
                    # If we found a blob to attach this blob to, we should
                    # do some math to help us with speed detection
                    prev_center = closest_blob['trail'][0]
                    if center[0] < prev_center[0]:
                        # It's moving left
                        closest_blob['dir'] = 'left'
                        closest_blob['bumper_x'] = x
                    else:
                        # It's moving right
                        closest_blob['dir'] = 'right'
                        closest_blob['bumper_x'] = x + w

                    # ...and we should add this centroid to the trail of
                    # points that make up this blob's history.
                    closest_blob['trail'].insert(0, center)
                    closest_blob['last_seen'] = frame_time

            if not closest_blob:
                # If we didn't find a blob, let's make a new one and add it to the list
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
        # Prune out the blobs that haven't been seen in some amount of time
        for i in xrange(len(tracked_blobs) - 1, -1, -1):
            if frame_time - tracked_blobs[i]['last_seen'] > BLOB_TRACK_TIMEOUT:
                print "Removing expired track {}".format(tracked_blobs[i]['id'])
                del tracked_blobs[i]

    # Draw the fences
    # cv2.line(frame, (LEFT_POLE_PX, 0), (LEFT_POLE_PX, 700), (100, 100, 100), 2)
    # cv2.line(frame, (RIGHT_POLE_PX, 0), (RIGHT_POLE_PX, 700), (100, 100, 100), 2)

    # Draw information about the blobs on the screen
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

    # Show the image from the camera (along with all the lines and annotations)
    # in a window on the user's screen.
    cv2.imshow("preview", frame)

    key = cv2.waitKey(10)
    if key == 27: # exit on ESC
        break
