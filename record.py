import cv2
#
# Records a webcam feed to an MP4 file using OpenCV.
#
# This is handy to record input for other CV programs without
# worrying too much about variable lighting conditions.
#

# Opens the default webcam device
vc = cv2.VideoCapture(0)

def get_frame():
    """ Helper function to grab a frame from the webcam, scale it, and return. """
    rval, frame = vc.read()
    # (h, w) = frame.shape[:2]
    # frame = cv2.resize(frame, (int(w * RESIZE_RATIO), int(h * RESIZE_RATIO)), interpolation=cv2.INTER_CUBIC)
    return rval, frame

# Grab a single frame from the camera. `grabbed` will be false
# if something failed, `frame` is an array of data containing
# the image.
grabbed, frame = get_frame()

# Specify the output encoding for the saved file
fourcc = cv2.cv.CV_FOURCC(*'mp4v')
# Get the size of the frame from the camera
(h, w) = frame.shape[:2]
# Build a video writer that writes to a file name with the specified
# output encoding, framerate, and size
writer = cv2.VideoWriter('output.mp4', fourcc, 40.0, (w, h))

while True:
    # Continuously grab a frame and write it to the outputter
    grabbed, frame = get_frame()
    writer.write(frame)

# Ideally we would listen for a signal and clean up the
# camera and writer here, but it seems to work without.
