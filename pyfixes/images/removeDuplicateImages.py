import cv2
import os


def compareHistogram(if1, if2):
    image1 = cv2.imread(if1)
    image2 = cv2.imread(if2)
    histImg1 = cv2.calcHist([image1], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])
    histImg1[255, 255, 255] = 0
    cv2.normalize(histImg1, histImg1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    histImg2 = cv2.calcHist([image2], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])
    histImg2[255, 255, 255] = 0
    cv2.normalize(histImg2, histImg2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    return cv2.compareHist(histImg1, histImg2, cv2.HISTCMP_CORREL)


newImageTag = []
keepImages = []
removeImages = []

home = GC.athlete()['home']
mediaDir = home + os.sep + 'media' + os.sep
m = GC.activityMetrics()
print(m['Images'].split())
allFiles = [mediaDir + image for image in m['Images'].split() if os.path.isfile(mediaDir + image)]

while len(allFiles) > 0:
    currentFile = allFiles.pop()
    if currentFile in removeImages or currentFile in keepImages:
        continue
    keepImages.append(currentFile)
    newImageTag.append(os.path.basename(currentFile))
    print("--- Next file: " + os.path.basename(currentFile))

    for compareFile in allFiles:
        if compareFile in removeImages or compareFile in keepImages:
            continue
        histogramScore = compareHistogram(currentFile, compareFile)
        print("Similarities: {} <-> {} histogram = {}".format(os.path.basename(currentFile), os.path.basename(compareFile), round(histogramScore, 2)))
        if histogramScore >= 0.2:
            removeImages.append(compareFile)

for image in removeImages:
    print("Removing " + os.path.basename(image))
    os.remove(image)

if len(removeImages) > 0:
    GC.setTag('Images', '\n'.join(newImageTag))
