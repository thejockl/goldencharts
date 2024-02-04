import os
import cv2

TARGET_SIZE = (2000, 2000)

home = GC.athlete()['home']
mediaDir = home + os.sep + 'media' + os.sep

imageFiles = [mediaDir + image for image in GC.getTag('Images').split() if os.path.isfile(mediaDir + image)]
for imageFile in imageFiles:
    image = cv2.imread(imageFile)
    height, width, _ = image.shape
    if width > TARGET_SIZE[0] or height > TARGET_SIZE[1]:
        imgAspect = width / height
        boxAspect = TARGET_SIZE[0] / TARGET_SIZE[1]
        if imgAspect < boxAspect:
            newHeight = TARGET_SIZE[1]
            newWidth = int(newHeight * imgAspect)
        else:
            newWidth = TARGET_SIZE[0]
            newHeight = int(newWidth / imgAspect)
        newShape = (newWidth, newHeight)
        image = cv2.resize(image, newShape, interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(imageFile, image)
