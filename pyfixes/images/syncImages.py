import datetime
import copy
import glob
import os
import shutil


PHOTOS_ROOT = # ADD THE ABSOLUTE PATH TO YOUR NON-GC PHOTO-STORE HERE
TARGET = GC.athlete()['home'] + os.sep + 'media'


def dateIndex(date):
    return (((((date.year - 1900) * 12 + date.month) * 31 + date.day) * 24 + date.hour) * 60 + date.minute) * 60 + date.second


def main():
    m = GC.activityMetrics()
    gcImages = m['Images'].split()
    gcStart = datetime.datetime.combine(m['date'], m['time'])
    gcEnd = gcStart + datetime.timedelta(seconds=m['Duration'])
    print(gcStart)
    print(gcEnd)

    d1 = gcStart
    d2 = gcEnd

    date1 = d1.replace(hour=0, minute=0, second=0)
    date2 = d2.replace(hour=0, minute=0, second=0)
    folderDate = datetime.datetime(d1.year, d1.month, 1)
    folderDates = [folderDate]
    print("Looking for all pictures between {} and {}".format(d1, d2))
    d = date1
    delta = datetime.timedelta(days=1)
    while d < date2:
        d += delta
        if d.month != folderDate.month:
            folderDate = datetime.datetime(d.year, d.month, 1)
            folderDates.append(folderDate)
    startDateIndex = dateIndex(d1)
    endDateIndex = dateIndex(d2)

    allFiles = []
    for folderDate in folderDates:
        path = "{basepath}{sep}{year:04d}{sep}{month:02d}{sep}*.jpg".format(basepath=PHOTOS_ROOT,
                                                                            sep=os.sep,
                                                                            year=folderDate.year,
                                                                            month=folderDate.month)
        allFiles.extend(glob.glob(path))

    newImages = copy.copy(gcImages)
    for candidateFile in allFiles:
        candidateFilename = os.path.basename(candidateFile)
        yearStr = candidateFilename[0:4]
        monthStr = candidateFilename[4:6]
        dayStr = candidateFilename[6:8]
        hourStr = candidateFilename[9:11]
        minuteStr = candidateFilename[11:13]
        secondStr = candidateFilename[13:15]
        fileDate = datetime.datetime(int(yearStr), int(monthStr), int(dayStr),
                                     int(hourStr), int(minuteStr), int(secondStr))
        fileDateIndex = dateIndex(fileDate)
        if fileDateIndex >= startDateIndex and fileDateIndex <= endDateIndex and candidateFilename not in newImages:
            try:
                print("Found image {} ({})".format(candidateFilename, candidateFile))
                if not os.path.isfile(TARGET + os.sep + candidateFilename):
                    print("File already exists, not copying")
                    shutil.copy2(candidateFile, TARGET)
                newImages.append(candidateFilename)
            except Exception as e:
                print("Failed to copy file " + candidateFilename + ": " + e)

    if newImages != gcImages:
        GC.setTag('Images', '\n'.join(newImages))
    else:
        print("No new images added")


if __name__ == "__main__":
    main()
