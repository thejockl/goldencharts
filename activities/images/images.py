import pathlib
import tempfile
import math
import os
import time
from jinja2 import Environment
from PIL import Image
from PIL.ExifTags import TAGS


PROD_MODE = True
DELETE_AFTER = 0.1
MAP_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

LEAFLET_CSS_TAG = """
<link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"
      integrity="sha512-h9FcoyWjHcOcmEVkxOfTLnmZFWIH0iZhZT1H2TbOq55xssQGEJHEaIm+PgoUaZbRvQTNTluNOEfb1ZRy6D3BOw=="
      crossorigin="anonymous"
      referrerpolicy="no-referrer" />
"""

LEAFLET_JS_TAG = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"
        integrity="sha512-puJW3E/qXDqYp9IfhAI54BJEaWIfloJ7JWs7OeD5i6ruC9JZL1gERT1wjtwXFlh7CjE7ZJ+/vcRZRkIYIb6p4g=="
        crossorigin="anonymous"
        referrerpolicy="no-referrer"></script>
"""

MARKERCLUSTER_CSS_TAG_1 = """
<link href='https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css' rel='stylesheet' />
"""

MARKERCLUSTER_CSS_TAG_2 = """
<link href='https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css' rel='stylesheet' />
"""

MARKERCLUSTER_JS_TAG = """
<script src='https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js'></script>
"""


def multilineStrip(ml):
    r = ""
    for line in ml.splitlines():
        st = line.strip()
        if len(st) > 0:
            if len(st) < len(line) and st[0] != "<":
                st = " " + st
            # Fake a newline since GoldenCheetah will become confused by

            r += st + """
"""
    return r


def getDefaultTemplate():
    return multilineStrip("""<!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        """ + LEAFLET_CSS_TAG + """
        """ + MARKERCLUSTER_CSS_TAG_1 + """
        """ + MARKERCLUSTER_CSS_TAG_2 + """
        <title>Images</title>
        <style>
          :root {
            --colBg: #e0e0e0;
            --colBgHover: #d0d0d0;
            --padHorizontal: 2em;
            --padVertical: 1em;
          }
          body {
              margin: 0;
              padding: 0;
              font-family: sans-serif;
          }
          #map {
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            z-index: 0;
          }
          img.previewPlain {
            width: 200px;
            cursor: pointer;
            border-radius: 10px;
          }
          img.preview {
            height: 200px;
            cursor: pointer;
            border-radius: 10px;
            box-shadow: 0px 0px 20px rgba(0, 0, 0, 0.6);
          }
          .fullscreen-gallery {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            justify-content: center;
            align-items: center;
            z-index: 1;
          }
          .fullscreen-gallery-padding {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow-y: auto;
          }
          .fullscreen-gallery-flex {
            display: flex;
            top: 0;
            left: 0;
            justify-content: center;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
            padding-top: 40px;
            padding-left: 5%;
            padding-right: 5%;
            padding-bottom: 40px;
          }
          .fullscreen-image {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            justify-content: center;
            align-items: center;
            z-index: 1;
          }
          .fullscreen-image img {
            max-width: 90%;
            max-height: 90%;
            margin: auto;
            display: block;
            border-radius: 10px;
            box-shadow: 0px 0px 20px rgba(0, 0, 0, 0.6);
          }
          button.map-button {
            position: absolute;
            z-index: 1000;
            padding: 10px;
            top: 10px;
            left: 50px;
            background-color: #ffffff;
            border-radius: 4px;
            border: 2px solid rgba(0, 0, 0, 0.3);
          }
        </style>
      </head>
      <body>
        <div id="map">
          <button class="map-button" onclick="openImage({{ images | length }}, event);">Gallery</button>
        </div>
        <div class="fullscreen-image" id="fullscreenImage" onclick="closeFullscreen();">
          <img id="fullscreenImageImg" src="" onclick="nextImage(event);" />
        </div>
        <div class="fullscreen-gallery" id="fullscreenGallery" onclick="closeFullscreen();">
          <div class="fullscreen-gallery-padding">
            <div class="fullscreen-gallery-flex">
            {%- for image in images %}
              <img class="preview" src="{{ image[0] }}" onclick="openImage({{ loop.index - 1}}, event);"></img>
            {% endfor -%}
            </div>
          </div>
        </div>
        """ + LEAFLET_JS_TAG + """
        """ + MARKERCLUSTER_JS_TAG + """
        <script>
          var map = L.map('map');
          L.tileLayer('""" + MAP_URL + """', {
            maxZoom: 19,
            attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          }).addTo(map);

          var track = L.polyline([
          {%- for point in track -%}
            [{{ point[0] }},{{ point[1] }}],
          {%- endfor -%}
          ]).addTo(map);

          const markers = L.markerClusterGroup();
          const images = [
          {%- for image in images -%}
            ["{{ image[0] }}", {{ image[1] }}, {{ image[2] }}],
          {%- endfor -%}
          ];
          images.forEach((item, idx) => {
            if (item[1] < 999 && item[2] < 999) {
              var marker = L.marker(new L.LatLng(item[1], item[2]));
              markers.addLayer(marker);
              item.push(marker);
              marker.bindPopup(`<img class='previewPlain' src='${item[0]}' id='markerImg' onclick='openImage(${idx}, event);'/>`);
              marker.on('popupopen', function(event) {
                openPopupIdx = idx;
                map.keyboard.disable();
              });
              marker.on('popupclose', function(event) {
                openPopupIdx = -1;
                map.keyboard.enable();
              });
            } else {
              item.push(null);
            }
          });
          images.push([null, null, null, null]);
          map.addLayer(markers);
          var openPageIdx = -1;
          var openPopupIdx = -1;

          var group = L.featureGroup([track, markers]);
          map.fitBounds(group.getBounds());

          const fullscreenImageDiv = document.getElementById('fullscreenImage');
          const fullscreenImageImg = document.getElementById('fullscreenImageImg');
          const fullscreenGalleryDiv = document.getElementById('fullscreenGallery');
          document.addEventListener('keydown', handleKeypress);
          function handleKeypress(event) {
            if (openPageIdx != -1) {
              event.preventDefault();
              if (   event.key == "Escape"
                  || event.key == ".") {
                closeFullscreen();
              } else if (   event.key == " "
                         || event.key == "Enter"
                         || event.key == "ArrowRight"
                         || event.key == "ArrowDown"
                         || event.key == "l"
                         || event.key == "j") {
                nextImage();
              } else if (   event.key == "ArrowLeft"
                         || event.key == "ArrowUp"
                         || event.key == "h"
                         || event.key == "k") {
                prevImage();
              }
            } else if (openPopupIdx != -1) {
              event.preventDefault();
              if (   event.key == "Escape"
                  || event.key == ".") {
                if (openPopupIdx > -1) {
                    images[openPopupIdx][3].closePopup();
                }
              } else if (   event.key == "ArrowRight"
                         || event.key == "ArrowDown"
                         || event.key == "l"
                         || event.key == "j") {
                nextPopup();
              } else if (   event.key == "ArrowLeft"
                         || event.key == "ArrowUp"
                         || event.key == "h"
                         || event.key == "k") {
                prevPopup();
              } else if (   event.key == "Enter"
                         || event.key == " ") {
                openImage(openPopupIdx, event);
              }
            } else {
              if (   event.key == "Escape"
                  || event.key == "Enter"
                  || event.key == " ") {
                openImage({{ images | length }}, event);
              }
            }
          }
          function nextPopup() {
            if (openPopupIdx < 0) {
              return;
            }
            var upcomingIdx = openPopupIdx;
            do {
              upcomingIdx = (parseInt(upcomingIdx) + 1) % images.length;
            } while (images[upcomingIdx][3] == null && openPopupIdx != upcomingIdx);
            openPopup(upcomingIdx);
          }
          function prevPopup() {
            if (openPopupIdx < 0) {
              return;
            }
            var upcomingIdx = openPopupIdx;
            do {
              if (upcomingIdx > 0) {
                upcomingIdx = parseInt(upcomingIdx) - 1;
              } else {
                upcomingIdx = images.length - 1;
              }
            } while (images[upcomingIdx][3] == null && openPopupIdx != upcomingIdx);
            openPopup(upcomingIdx);
          }
          function openPopup(idx) {
            if (idx < 0 || images[idx][3] == null || openPopupIdx == idx) {
                return;
            }
            var cluster = markers.getVisibleParent(images[idx][3]);
            if (cluster instanceof L.MarkerCluster) {
              cluster.spiderfy();
            }
            images[idx][3].openPopup();
          }
          function nextImage(event = null) {
            openImage((parseInt(openPageIdx) + 1) % images.length, event);
          }
          function prevImage(event = null) {
            if (openPageIdx > 0) {
              openImage(parseInt(openPageIdx) - 1, event);
            } else {
              openImage(images.length - 1, event);
            }
          }
          function openImage(idx, event = null) {
            images.forEach((item, idx) => {
              if (item[3] != null) {
                  item[3].closePopup();
              }
            });
            openPageIdx = idx;
            if (images[idx][0] != null) {
              fullscreenImageImg.src = images[idx][0];
              fullscreenImageDiv.style.display = 'flex';
              fullscreenGalleryDiv.style.display = 'none';
            } else {
              fullscreenImageImg.src = "";
              fullscreenImageDiv.style.display = 'none';
              fullscreenGalleryDiv.style.display = 'flex';
              fullscreenGalleryDiv.scrollTo(0, 0);
            }
            if (images[idx][3] != null) {
              map.setView(images[idx][3].getLatLng());
              var cluster = markers.getVisibleParent(images[idx][3]);
              if (cluster instanceof L.MarkerCluster) {
                cluster.spiderfy();
              }
              images[idx][3].openPopup();
            } else {
              map.fitBounds(group.getBounds());
            }
            map.keyboard.disable();
            if (event != null) {
                event.stopPropagation();
            }
          }
          function closeFullscreen() {
            fullscreenImageDiv.style.display = 'none';
            fullscreenGalleryDiv.style.display = 'none';
            openPageIdx = -1;
            if (openPopupIdx == -1) {
                map.keyboard.enable();
            }
          }
        </script>
      </body>
    </html>""")


def getEmptyTemplate():
    return multilineStrip("""<!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Images</title>
        <style>
          :root {
            --colBg: #e0e0e0;
            --colBgHover: #d0d0d0;
            --padHorizontal: 2em;
            --padVertical: 1em;
          }
          body {
              margin: 0;
              padding: 0;
              font-family: sans-serif;
          }
        </style>
      </head>
      <body>
        <center>
          <h1>No images found for this activity</h1>
          Images can be added by dragging them to the activity
        </center>
      </body>
    </html>""")


def decimalCoords(coords, ref):
    decimalDegrees = float(coords[0]) + float(coords[1]) / 60 + float(coords[2]) / 3600
    if ref == "S" or ref == 'W':
        decimalDegrees = -1 * decimalDegrees
    return decimalDegrees


GPSINFO_TAG = next(
    tag for tag, name in TAGS.items() if name == "GPSInfo"
)

home = GC.athlete()['home']
mediaDir = home + os.sep + 'media' + os.sep
imageFiles = []
for imageName in GC.getTag('Images').split():
    imageFile = mediaDir + imageName
    try:
        image = Image.open(imageFile)
        exif = image.getexif()
        if exif:
            gpsinfo = exif.get_ifd(GPSINFO_TAG)
            imageFiles.append((imageFile,
                               decimalCoords(gpsinfo[2], gpsinfo[1]),
                               decimalCoords(gpsinfo[4], gpsinfo[3])))
        else:
            imageFiles.append((imageFile, 1000, 1000))
    except KeyError:
        imageFiles.append((imageFile, 1000, 1000))
    except IOError:
        print("Cannot read exif info from image '%s'" % imageFile)

if PROD_MODE:
    outFile = tempfile.NamedTemporaryFile(mode="w+t", prefix="GC_", suffix=".html", delete=False)
else:
    outFile = open("/tmp/dev.html", "w")
outPath = pathlib.Path(outFile.name)

track = []
lats = GC.series(GC.SERIES_LAT)
lons = GC.series(GC.SERIES_LON)
maxI = len(lats)
for i in range(maxI):
    lat = lats[i]
    lon = lons[i]
    if math.isclose(lat, 0) and math.isclose(lon, 0):
        continue
    track.append([lat, lon])

env = Environment()
env.trim_blocks = True
env.lstrip_blocks = True
if len(imageFiles) > 0:
    template = env.from_string(getDefaultTemplate())
    template.stream(images=imageFiles, track=track).dump(outFile.name)
else:
    template = env.from_string(getEmptyTemplate())
    template.stream().dump(outFile.name)
GC.webpage(outPath.as_uri())
if PROD_MODE:
    time.sleep(DELETE_AFTER)
    outPath.unlink()
