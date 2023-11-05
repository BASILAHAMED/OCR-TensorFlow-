# import the necessary packages
from keras.models import load_model
from imutils.contours import sort_contours
import numpy as np
import argparse
import imutils
import cv2
import os

# Get the current directory
current_directory = os.path.dirname(os.path.abspath(__file__))

# Construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True,
	help="path to input image")
ap.add_argument("-m", "--model", type=str, default=os.path.join(current_directory, "handwriting.model"),
	help="path to trained handwriting recognition model")
args = vars(ap.parse_args())

# Load the handwriting OCR model
print("[INFO] loading handwriting OCR model...")
model = load_model(args["model"])

# Load the input image from disk, convert it to grayscale, and blur
# it to reduce noise
image = cv2.imread(args["image"])
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (5, 5), 0)

# Perform edge detection, find contours in the edge map, and sort the
# resulting contours from left-to-right
edged = cv2.Canny(blurred, 30, 150)
cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL,
	cv2.CHAIN_APPROX_SIMPLE)
cnts = imutils.grab_contours(cnts)
cnts = sort_contours(cnts, method="left-to-right")[0]

# Initialize the list of contour bounding boxes and associated
# characters that we'll be OCR'ing
chars = []

# Loop over the contours
for c in cnts:
	# Compute the bounding box of the contour
	(x, y, w, h) = cv2.boundingRect(c)

	# Filter out bounding boxes, ensuring they are neither too small
	# nor too large
	if (w >= 5 and w <= 150) and (h >= 15 and h <= 120):
		# Extract the character and threshold it to make the character
		# appear as *white* (foreground) on a *black* background, then
		# grab the width and height of the thresholded image
		roi = gray[y:y + h, x:x + w]
		thresh = cv2.threshold(roi, 0, 255,
			cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
		(tH, tW) = thresh.shape

		# If the width is greater than the height, resize along the
		# width dimension; otherwise, resize along the height
		if tW > tH:
			thresh = imutils.resize(thresh, width=32)
		else:
			thresh = imutils.resize(thresh, height=32)

		# Re-grab the image dimensions (now that it's been resized)
		# and then determine how much we need to pad the width and
		# height such that our image will be 32x32
		(tH, tW) = thresh.shape
		dX = int(max(0, 32 - tW) / 2.0)
		dY = int(max(0, 32 - tH) / 2.0)

		# Pad the image and force 32x32 dimensions
		padded = cv2.copyMakeBorder(thresh, top=dY, bottom=dY,
			left=dX, right=dX, borderType=cv2.BORDER_CONSTANT,
			value=(0, 0, 0))
		padded = cv2.resize(padded, (32, 32))

		# Prepare the padded image for classification via our
		# handwriting OCR model
		padded = padded.astype("float32") / 255.0
		padded = np.expand_dims(padded, axis=-1)

		# Update our list of characters that will be OCR'd
		chars.append((padded, (x, y, w, h)))

# Extract the bounding box locations and padded characters
boxes = [b[1] for b in chars]
chars = np.array([c[0] for c in chars], dtype="float32")

# OCR the characters using our handwriting recognition model
preds = model.predict(chars)

# Define the list of label names
labelNames = "0123456789"
labelNames += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
labelNames = [l for l in labelNames]

# Loop over the predictions and bounding box locations together
for (pred, (x, y, w, h)) in zip(preds, boxes):
	# Find the index of the label with the largest corresponding
	# probability, then extract the probability and label
	i = np.argmax(pred)
	prob = pred[i]
	label = labelNames[i]

	# Draw the prediction on the image
	print("[TEXT] {} - {:.2f}%".format(label, prob * 100))
	cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
	cv2.putText(image, label, (x - 10, y - 10),
	     
		cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
	
# Save the output image to a file
output_path = os.path.join(current_directory, "output.jpg")
cv2.imwrite(output_path, image)
print("[INFO] Output image saved to:", output_path)

# Show the image
cv2.imshow("Image", image)
cv2.waitKey(0)
