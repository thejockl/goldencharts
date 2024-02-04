import cv2
import os
import time


# Similarity is between -1..1 (different..similar)
THRESHOLD = 0.35


def isDuplicate(histImg1, histImg2):
    score = cv2.compareHist(histImg1, histImg2, cv2.HISTCMP_CORREL)
    return score > THRESHOLD


def getHistogram(imageFile):
    image = cv2.imread(imageFile)
    histImg = cv2.calcHist([image], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])
    histImg[255, 255, 255] = 0
    cv2.normalize(histImg, histImg, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    return histImg


start = time.time()
newImageTag = []
keepImages = []
removeImages = []
histograms = dict()

home = GC.athlete()['home']
mediaDir = home + os.sep + 'media' + os.sep
allFiles = [mediaDir + image for image in GC.getTag('Images').split() if os.path.isfile(mediaDir + image)]

for file in allFiles:
    if file not in histograms.keys():
        histograms[file] = getHistogram(file)

while len(allFiles) > 0:
    currentFile = allFiles.pop()
    if currentFile in removeImages or currentFile in keepImages:
        continue
    keepImages.append(currentFile)
    newImageTag.append(os.path.basename(currentFile))

    for compareFile in allFiles:
        if compareFile in removeImages or compareFile in keepImages:
            continue
        if isDuplicate(histograms.get(currentFile), histograms.get(compareFile)):
            removeImages.append(compareFile)

print("Keeping " + ", ".join(newImageTag))

for image in removeImages:
    print("Removing " + os.path.basename(image))
    os.remove(image)

if len(removeImages) > 0:
    GC.setTag('Images', '\n'.join(newImageTag))
end = time.time()
print("Finished in {:.2f} seconds".format(end - start))
