import math
import time
import pathlib
import tempfile
from jinja2.filters import pass_environment
from jinja2 import Environment
from datetime import date, datetime


PROD_MODE = True
DELETE_AFTER = 0.1

DATE_FORMAT = "%d.%m.%Y"

HIGH_SPEED_ABS = 70
HIGH_SPEED_REL = 50

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

SIDEBAR_CSS_TAG = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/sidebar-v2@0.4.0/css/leaflet-sidebar.min.css">
"""

SIDEBAR_JS_TAG = """
<script src="https://cdn.jsdelivr.net/npm/sidebar-v2@0.4.0/js/leaflet-sidebar.min.js"></script>
"""

FONTAWESOME_CSS_TAG = """
<link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css"
      integrity="sha512-Evv84Mr4kqVGRNSgIGL/F/aIDqQb7xQ2vcrdIwxfjThSH8CSR7PBEakCr51Ck+w+/U6swU2Im1vVX0SVk9ABhg=="
      crossorigin="anonymous"
      referrerpolicy="no-referrer" />
"""


@pass_environment
def format_date(environment, value, attribute=None):
    if isinstance(value, str):
        when = date.fromisoformat(value)
        return when.strftime(DATE_FORMAT)
    elif isinstance(value, datetime) or isinstance(value, date):
        return value.strftime(DATE_FORMAT)


def multilineStrip(ml):
    r = ""
    for line in ml.splitlines():
        st = line.strip()
        if len(st) > 0:
            if len(st) < len(line) and st[0] != "<":
                st = " " + st
            # Fake a newline since GoldenCheetah will become confused by \n
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
        """ + SIDEBAR_CSS_TAG + """
        """ + FONTAWESOME_CSS_TAG + """
        <title>Vehicles</title>
        <style>
          :root {
            --colBg: #e0e0e0;
            --colBgHover: #d0d0d0;
            --padHorizontal: 2em;
            --padVertical: 1em;
          }
          body { margin: 0; padding: 0; font-family: sans-serif; }
          #map { position: absolute; top: 0; right: 0; bottom: 0; left: 0; }
          input[type="button"] {
            width: 100%;
            border: none;
            padding: var(--padVertical) var(--padHorizontal);
            background-color: var(--colBg);
            text-align: center;
            text-decoration: none;
            display: inline-block;
          }
          input[type="button"]:hover {
            background-color: var(--colBgHover);
          }
        </style>
      </head>
      <body>
        <div id="sidebar" class="sidebar collapsed">
          <div class="sidebar-tabs">
            <ul role="tablist">
              <li><a href="#home" role="tab"><i class="fa fa-bars"></i></a></li>
            </ul>
          </div>

          <div class="sidebar-content">
            <div class="sidebar-pane" id="home">
              <h1 class="sidebar-header">
                Vehicles
                <span class="sidebar-close"><i class="fa fa-caret-left"></i></span>
              </h1>

              <p>
                <b>Rides</b><br/>
                Total number of Vehicles: <b>{{ stats.count }}</b><br/>
              </p>
              <p>
                <b>Speed Classifications</b><br/>
                Vehicles at high relative Speed: <b>{{ stats.countFastRel }}</b><br/>
                Vehicles at high absolute Speed: <b>{{ stats.countFastAbs }}</b><br/>
                Vehicles at moderate relative Speed: <b>{{ stats.countModerateRel }}</b><br/>
                Vehicles at moderate absolute Speed: <b>{{ stats.countModerateAbs }}</b><br/>
              </p>
              <p>
                <b>Highest Speeds</b><br/>
                Relative: <b>{{ stats.highestRel }} km/h</b><br/>
                Absolute: <b>{{ stats.highestAbs }} km/h</b><br/>
              </p>
              <p>
                <b>Lowest Speeds</b><br/>
                Relative: <b>{{ stats.lowestRel }} km/h</b><br/>
                Absolute: <b>{{ stats.lowestAbs }} km/h</b><br/>
              </p>
              <p>
                <b>Average Speeds</b><br/>
                Relative: <b>{{ '%.1f' | format(stats.averageRel) }} km/h</b><br/>
                Absolute: <b>{{ '%.1f' | format(stats.averageAbs) }} km/h</b><br/>
              </p>
              <hr/>
              <p>
                <input type="button" id="zoomfit" value="Zoom to Fit">
              </p>
            </div>
          </div>
        </div>

        <div id="map" class="sidebar-map"></div>
        """ + LEAFLET_JS_TAG + """
        """ + MARKERCLUSTER_JS_TAG + """
        """ + SIDEBAR_JS_TAG + """
        <script>
          var orangeIcon = new L.Icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-orange.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
          });
          var redIcon = new L.Icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
          });

          var map = L.map('map');
          L.tileLayer('""" + MAP_URL + """', {
              maxZoom: 19,
              attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          }).addTo(map);

          var sidebar = L.control.sidebar('sidebar').addTo(map);

          var track = L.polyline([
          {%- for point in track -%}
            [{{ point[0] }},{{ point[1] }}],
          {%- endfor -%}
          ]).addTo(map);

          const markers = L.markerClusterGroup();
          const vehicles = [
          {%- for vehicle in vehicles -%}
            [{{ vehicle[0] }},{{ vehicle[1] }},{{ vehicle[2] }},{{ vehicle[3] }}],
          {%- endfor -%}
          ];
          for (const vehicle of vehicles) {
            var marker = L.marker(new L.LatLng(vehicle[0], vehicle[1]));
            if (vehicle[2] >= {{ fastLimit }}) {
                marker.setIcon(redIcon);
            } else {
                marker.setIcon(orangeIcon);
            }
            marker.bindPopup(  '<b>Passing speed</b><br/>'
                             + 'Relative: <b>' + vehicle[2] + ' km/h</b><br>'
                             + 'Absolute: <b>' + vehicle[3] + ' km/h</b>');
            markers.addLayer(marker);
          }
          map.addLayer(markers);

          var group = L.featureGroup([track, markers]);
          map.fitBounds(group.getBounds());

          document.getElementById('zoomfit').addEventListener('click', (event) => {
            map.fitBounds(group.getBounds());
          });
        </script>
      </body>
    </html>""")


def getEmptyTemplate():
    return multilineStrip("""<!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Vehicles</title>
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
          <h1>No vehicles found in activity</h1>
        </center>
      </body>
    </html>""")


def getActivityVehicles(activity):
    vehicles = []
    track = []
    stats = {
        'count': 0,
        'countFastAbs': 0,
        'countFastRel': 0,
        'countModerateAbs': 0,
        'countModerateRel': 0,
        'lowestAbs': 10000,
        'lowestRel': 10000,
        'highestAbs': 0,
        'highestRel': 0,
        'averageAbs': 0,
        'averageRel': 0
    }

    try:
        lats = GC.series(GC.SERIES_LAT, activity=activity)
        lons = GC.series(GC.SERIES_LON, activity=activity)
        radarCurrent = GC.xdata("DEVELOPER", "radar_current", activity=activity)
        radarPassingSpeed = GC.xdata("DEVELOPER", "passing_speed", activity=activity)
        radarPassingSpeedAbs = GC.xdata("DEVELOPER", "passing_speedabs", activity=activity)

        lens = [len(lats),
                len(lons),
                len(radarCurrent),
                len(radarPassingSpeed),
                len(radarPassingSpeedAbs)]
        maxI = min(lens)

        lastCurrent = 0
        vehicleCount = 0
        for i in range(maxI):
            lat = lats[i]
            lon = lons[i]
            if math.isclose(lat, 0) and math.isclose(lon, 0):
                continue
            track.append([lat, lon])
            if i < maxI - 1 and lastCurrent < radarCurrent[i + 1]:
                vehicles.append([lat, lon, radarPassingSpeed[i], radarPassingSpeedAbs[i]])
                lastCurrent = int(radarCurrent[i + 1])
                vehicleCount += 1
                if radarPassingSpeedAbs[i] >= HIGH_SPEED_ABS:
                    stats['countFastAbs'] += 1
                else:
                    stats['countModerateAbs'] += 1
                if radarPassingSpeed[i] >= HIGH_SPEED_REL:
                    stats['countFastRel'] += 1
                else:
                    stats['countModerateRel'] += 1
                stats['averageAbs'] += radarPassingSpeedAbs[i]
                stats['averageRel'] += radarPassingSpeed[i]
                stats['lowestAbs'] = min(radarPassingSpeedAbs[i], stats['lowestAbs'])
                stats['lowestRel'] = min(radarPassingSpeed[i], stats['lowestRel'])
                stats['highestAbs'] = max(radarPassingSpeedAbs[i], stats['highestAbs'])
                stats['highestRel'] = max(radarPassingSpeed[i], stats['highestRel'])
        stats['count'] = vehicleCount
        if vehicleCount > 0:
            stats['averageAbs'] /= vehicleCount
            stats['averageRel'] /= vehicleCount
    finally:
        if stats['count'] == 0:
            stats['lowestAbs'] = 0
            stats['lowestRel'] = 0
        return (vehicles, track, stats)


(vehicles, track, stats) = getActivityVehicles(None)

outFile = tempfile.NamedTemporaryFile(mode="w+t", prefix="GC_", suffix=".html", delete=False)
outPath = pathlib.Path(outFile.name)
env = Environment()
env.filters['format_date'] = format_date
env.trim_blocks = True
env.lstrip_blocks = True
if len(vehicles) > 0:
    template = env.from_string(getDefaultTemplate())
    template.stream(vehicles=vehicles, track=track, stats=stats, fastLimit=HIGH_SPEED_ABS).dump(outFile.name)
else:
    template = env.from_string(getEmptyTemplate())
    template.stream(stats=stats).dump(outFile.name)
GC.webpage(outPath.as_uri())
if PROD_MODE:
    time.sleep(DELETE_AFTER)
    outPath.unlink()
