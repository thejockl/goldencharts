import os

home = GC.athlete()['home']
mediaDir = home + os.sep + 'media' + os.sep

images = GC.getTag('Images').split()
deduplicated = []
[deduplicated.append(image) for image in images if image not in deduplicated]
newImages = [image for image in deduplicated if os.path.isfile(mediaDir + image)]
newImages = newImages.sort()

if images != newImages:
    GC.setTag('Images', '\n'.join(newImages))
