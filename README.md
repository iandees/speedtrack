# speedtrack
Python + OpenCV tool to count cars on the road in front of my house.

## Methodology

Capture a frame of RGB video from the webcam. Convert it to HSV and pick out only the Value channel to convert to grayscale. After converting to grayscale, apply a blur function and add the frame to the running average of the scene.

![](https://cloud.githubusercontent.com/assets/261584/15658331/2cd1615e-2689-11e6-8dcf-2cc9184a01f6.png)

I convert to HSV and pick out a single channel because the running average accumulator built in to OpenCV only works on a single channel. I converted to HSV because I wanted to see if comparing the Hue or Saturation channels would lead to better extraction of moving objects. This wasn't as successful as I thought it would be, so I went back to plain old Value channel.

![](https://cloud.githubusercontent.com/assets/261584/15658332/2cd8fc5c-2689-11e6-922f-e82422935774.png)

After using the frame to accumulate the average of the scene (hopefully capturing a good representation of the background without any moving stuff in it), take a difference of the current frame with the average. This generates a grayscale image that shows only the stuff that isn't in the background/average image.

![](https://cloud.githubusercontent.com/assets/261584/15658334/2cdeaada-2689-11e6-9fec-5a4824552f14.png)

Apply a threshold to the resulting grayscale image. This makes any pixel that has a value above a certain amount white and any pixel that has a value lower than the amount black. This generates an image with white "blobs".

![](https://cloud.githubusercontent.com/assets/261584/15658333/2cd9c9c0-2689-11e6-89e8-cd403a1ee097.png)

With the white blobs highlighted and more obvious, I use OpenCV's `cv2.findContours()` function to find the outline contours for the blobs in the image. In our case, we only care about the bounding rectangle and centroid of the blobs.

When I find these blob centroids, I search through the existing list of centroids I've seen to find possible matches by both distance and direction (if known). If a match is found, I connect this frame's blob with the matched blob and can use it to make a track across the scene. If no existing blob matches, then we add a new one for later frames to track.

Based on these existing centroids, I can count the number of vehicles that are going in either direction on my street and (with some calibration) get a reasonably accurate measure of the speed, too.

## Limitations

As you can see in the first image above, there are two trees blocking my view of the road. This means my camera only has a few hundred milliseconds to see any vehicle motion. Currently this is enough to track most of the cars, but I probably won't be able to get a reliable speed measurement.

Also, because the camera doesn't get to see much above the cars, when two cars approach each other and one crosses in front of the other the system counts them as a single blob and messes up the count.

## Prior Art and Helpful Information

- [`VideoSpeedTracker`](https://github.com/pfr/VideoSpeedTracker) was an inspiration for this project. More information about the problem they're trying to solve in Charlottesville can be found [on this adjacent GitHub page](http://eyetach.github.io/CharlottesvilleSpeeds/).
- Adrian's [pyimagesearch.com](http://pyimagesearch.com) and the [motion detection](http://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/) tutorials are a great walkthrough on getting started in this field and were what triggered me to use averaging to build a background.
- Kyle Hounslow has an excellent set of YouTube tutorials on OpenCV. His [tutorial on Method of Sequential Images](https://www.youtube.com/watch?v=X6rPdRZzgjg) was a big help in getting started.
- Claude Paeau's [YouTube video](https://www.youtube.com/watch?v=eRi50BbJUro) on motion tracking in his front yard was what got me started down this road. His code walkthrough helped me get started.
