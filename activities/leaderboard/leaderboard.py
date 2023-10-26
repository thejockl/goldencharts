# -*- coding: utf-8 -*-

import pandas
import numpy as np
import pathlib
import tempfile
import time
import traceback
from jinja2 import Environment
from jinja2.filters import pass_environment
from datetime import date, datetime, timedelta
from collections import OrderedDict


MAP_PROVIDER = "https://tiles.int.soschee.net/osm/{z}/{x}/{y}.png"
MAP_MAX_ZOOM = "17"
MAP_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
TRACE_COLOR = "purple"

DATE_FORMAT = "%d.%m.%Y"

BOOTSTRAP_CSS_TAG = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
      integrity="sha384-rbsA2VBKQhggwzxH7pPCaAqO46MgnOM80zW1RWuH61DGLwZJEdK2Kadq2F9CUG65"
      crossorigin="anonymous">
"""

BOOTSTRAP_JS_TAG = """
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"
        integrity="sha384-kenU1KFdBIe4zVF0s0G1M5b4hcpxyD9F7jL+jjXkk+Q2h455rYXK/7HAuoJl+0I4"
        crossorigin="anonymous"></script>
"""


LEAFLET_CSS_TAG = """
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.3/dist/leaflet.css"
      integrity="sha256-kLaT2GOSpHechhsozzB+flnD+zUyjE2LlfWPgU04xyI="
      crossorigin=""/>
"""

LEAFLET_JS_TAG = """
<script src="https://unpkg.com/leaflet@1.9.3/dist/leaflet.js"
        integrity="sha256-WBkoXOwTeyKclOHuWtc+i2uENFpDZ9YPdf5Hf+D7ewM="
        crossorigin=""></script>
"""


COMMON_KEYS = ["name", "Distance", "Elevation_Gain", "Elevation_Loss", "Duration", "Average_Power",
               "Average_Heart_Rate", "Average_Speed", "Average_Cadence", "BikeStress", "VAM"]


def main():
    st = time.time()
    failed = False
    try:
        segments, info = collectData()
    except MissingSeasonError:
        failed = True
        msg = 'Failed to load route segments'
        resolution = 'Please select a season in Trends View first'
        trace = ''
    except NoActivitySegmentsError as e:
        failed = True
        if len(e.info['Route']) > 0:
            msg = 'No route segments found for activity "{}" ({})'.format(e.info['Route'],
                                                                          e.info['date'].strftime(DATE_FORMAT))
        else:
            msg = 'No route segments found for selected activity ({})'.format(e.info['date'].strftime(DATE_FORMAT))
        resolution = ''
        trace = ''
    except Exception:
        traceback.print_exc()
        failed = True
        msg = 'Failed to load segments'
        resolution = ''
        trace = traceback.format_exc()
    et = time.time()
    print("Dataprocessing took {:.3f} seconds".format(et-st))

    outFile = tempfile.NamedTemporaryFile(mode="w+t", prefix="GC_", suffix=".html", delete=False)
    env = Environment()
    env.filters['duration'] = duration
    env.filters['format_date'] = format_date
    env.filters['show'] = show
    env.trim_blocks = True
    env.lstrip_blocks = True

    if not failed:
        template = env.from_string(getDefaultTemplate())
        template.stream(segments=segments, info=info).dump(outFile.name)
    else:
        template = env.from_string(getErrorTemplate())
        template.stream(msg=msg, resolution=resolution, trace=trace).dump(outFile.name)

    GC.webpage(pathlib.Path(outFile.name).as_uri())


@pass_environment
def duration(environment, value, attribute=None):
    if isinstance(value, float):
        mins = int(value / 60)
        secs = int(value % 60)
        return "{}:{:0>2d}".format(mins, secs)
    else:
        return "0:00"


@pass_environment
def format_date(environment, value, attribute=None):
    if isinstance(value, str):
        when = date.fromisoformat(value)
        return when.strftime(DATE_FORMAT)
    elif isinstance(value, datetime) or isinstance(value, date):
        return value.strftime(DATE_FORMAT)


@pass_environment
def show(environment, value, attribute=None):
    if isinstance(value, int):
        if value > 0:
            return value
        else:
            return "-"
    elif isinstance(value, float):
        if value > 0:
            return round(value, 1)
        else:
            return "-"
    else:
        return value


class MissingSeasonError(Exception):
    pass


class NoActivitySegmentsError(Exception):
    def __init__(self, activityStart, info):
        self.activityStart = activityStart
        self.info = info


def retrieveData():
    try:
        activitySeason = GC.season()
    except Exception:
        raise MissingSeasonError
    seasonStart = activitySeason['start'][0]
    seasonEnd = activitySeason['end'][0]
    am = GC.activityMetrics()
    info = dict()
    info['outOfSeason'] = False
    info['Route'] = am.get('Route', '')
    info['date'] = am['date']
    info['seasonName'] = activitySeason['name'][0]
    activityStart = datetime.combine(am['date'], am['time'])
    activityEnd = activityStart + timedelta(seconds=am['Duration'])
    typeName = GC.intervalType(type=6)
    activityIntervals = reduceActivityIntervals(GC.activityIntervals(type=typeName))
    if len(activityIntervals['start']) == 0:
        raise NoActivitySegmentsError(activityStart=activityStart, info=info)

    trendIntervals = reduceTrendIntervals(GC.seasonIntervals(type=typeName))
    if activityStart.date() < seasonStart or activityEnd.date() > seasonEnd:
        trendIntervals = extendWithActivityIntervals(trendIntervals, activityStart, activityIntervals)
        info['outOfSeason'] = True

    activity = GC.activity()
    activityMetrics = GC.activityMetrics()
    return trendIntervals, activity, activityIntervals, activityMetrics, activitySeason, info


def extendWithActivityIntervals(trendIntervals, activityStart, activityIntervals):
    i = len(trendIntervals['date'])
    s = len(activityIntervals['start'])
    trendIntervals['date'].extend([None] * s)
    trendIntervals['time'].extend([None] * s)
    for s in activityIntervals['start']:
        dt = activityStart + timedelta(seconds=s)
        trendIntervals['date'][i] = dt.date()
        trendIntervals['time'][i] = dt.time()
        i += 1
    for key in COMMON_KEYS:
        trendIntervals[key].extend(activityIntervals[key])
    return trendIntervals


def reduceActivityIntervals(intervals):
    keys = ["start", "stop"]
    keys.extend(COMMON_KEYS)
    newIntervals = dict()
    for key in keys:
        newIntervals[key] = intervals[key]
    return newIntervals


def reduceTrendIntervals(intervals):
    keys = ["date", "time"]
    keys.extend(COMMON_KEYS)
    newIntervals = dict()
    for key in keys:
        newIntervals[key] = intervals[key]
    return newIntervals


def secsToIndex(sec, secs):
    """
    Find the index of sec in secs.
    This method can be used to find the index of a segment within thw

    :return: Index of the given time
    """
    for i, s in enumerate(secs):
        if s >= sec:
            return i
    return 0


def findTrace(start, end, activity):
    istart = secsToIndex(start, activity['seconds'])
    iend = secsToIndex(end, activity['seconds'])
    trace = []
    for i in range(istart, iend + 1):
        trace.append((activity['latitude'][i], activity['longitude'][i]))
    return trace


def prepareData(trendIntervals, activityIntervals, activityMetrics, activitySeason, activity):
    trendIntervalsDF = pandas.DataFrame(trendIntervals)
    activityIntervalsDF = pandas.DataFrame(activityIntervals)

    activityIntervalsDF['trace'] = activityIntervalsDF.apply(lambda row: findTrace(row['start'],
                                                                                   row['stop'],
                                                                                   activity), axis=1)
    matchingIntervalsDF = trendIntervalsDF[trendIntervalsDF['name'].isin(activityIntervalsDF['name'])]
    activityStart = datetime.combine(activityMetrics['date'], activityMetrics['time'])
    activityIntervalsDF['datetime'] = pandas.to_datetime(activityStart
                                                         + pandas.to_timedelta(activityIntervalsDF['start'], unit='s'))
    activityIntervalsDF['date'] = pandas.to_datetime(activityIntervalsDF['datetime']).dt.date
    activityIntervalsDF['time'] = pandas.to_datetime(activityIntervalsDF['datetime']).dt.time
    activityIntervalsDF['isCurrent'] = True
    activityIntervalsDF = activityIntervalsDF[['name', 'date', 'time', 'isCurrent', 'trace']]

    matchingIntervalsDF = pandas.merge(matchingIntervalsDF,
                                       activityIntervalsDF,
                                       how='left',
                                       left_on=['name', 'date', 'time'],
                                       right_on=['name', 'date', 'time'])
    matchingIntervalsDF['isCurrent'] = matchingIntervalsDF['isCurrent'].fillna(False)
    segmentNamesAttempts = matchingIntervalsDF['name'].value_counts()

    return matchingIntervalsDF, segmentNamesAttempts


def createSegmentsOverview(segmentNamesAttempts, activitySeason):
    segmentsOverview = dict()

    segmentsOverview['numSegments'] = len(segmentNamesAttempts)

    return segmentsOverview


def segmentTrace(start, stop, activity):
    startIdx = secsToIndex(start, activity['seconds'])
    stopIdx = secsToIndex(stop, activity['seconds'])
    trace = []
    if startIdx > 0 and stopIdx > 0:
        for i in range(startIdx, stopIdx + 1):
            trace.append((activity['latitudes'][i], activity['longitudes'][i]))
    return trace


def findSegments(segmentNamesAttempts, matchingIntervalsDF):
    segmentsDict = dict()

    for name, attempts in segmentNamesAttempts.sort_values(axis=0, ascending=False).items():
        segmentDF = matchingIntervalsDF[matchingIntervalsDF.name == name].copy()
        segmentDF['Average_Heart_Rate'].replace(0.0, np.NaN, inplace=True)
        segmentDF['Average_Power'].replace(0.0, np.NaN, inplace=True)
        segmentDF['Average_Cadence'].replace(0.0, np.NaN, inplace=True)
        segmentDF['BikeStress'].replace(0.0, np.NaN, inplace=True)
        segmentInfoSeries = segmentDF[['Distance',
                                       'Elevation_Gain',
                                       'Elevation_Loss']].mean()
        segmentAvgSeries = segmentDF[['Duration',
                                      'Average_Power',
                                      'Average_Heart_Rate',
                                      'Average_Speed',
                                      'Average_Cadence',
                                      'BikeStress']].mean()
        segmentBoardDF = segmentDF[['date',
                                    'time',
                                    'Duration',
                                    'Average_Power',
                                    'Average_Heart_Rate',
                                    'Average_Speed',
                                    'Average_Cadence',
                                    'BikeStress',
                                    'VAM',
                                    'isCurrent']].sort_values(by='Duration', ignore_index=True)
        current = segmentDF.loc[segmentDF['isCurrent'] == True, ['date', 'time', 'trace']].iloc[0]
        currentDateTime = datetime.combine(current['date'], current['time'])
        durationDF = segmentBoardDF['Duration']
        minDuration = durationDF.min()
        maxDuration = durationDF.max()
        segmentBoardDF['deltaDuration'] = (segmentBoardDF['Duration'] - minDuration)
        segmentBoardDF['deltaPercent'] = 100 * segmentBoardDF['deltaDuration'] / minDuration
        segmentData = dict()
        segmentData['name'] = name
        segmentData['numAttempts'] = attempts
        segmentData['hasHeartRate'] = ((segmentDF['Average_Heart_Rate'] > 0.0).sum())
        segmentData['hasCadence'] = ((segmentDF['Average_Cadence'] > 0.0).sum())
        segmentData['hasPower'] = ((segmentDF['Average_Power'] > 0.0).sum())
        segmentData['rank'] = segmentBoardDF.index[segmentBoardDF['isCurrent']][0] + 1
        segmentData['rankPercent'] = segmentData['rank'] / attempts * 100
        segmentData['info'] = segmentInfoSeries.to_dict()
        segmentData['averages'] = segmentAvgSeries.to_dict()
        segmentData['attempts'] = segmentBoardDF.to_dict('records')
        segmentData['firstAttempt'] = segmentDF['date'].min()
        segmentData['lastAttempt'] = segmentDF['date'].max()
        segmentData['deltaDuration'] = maxDuration - minDuration
        segmentData['deltaPercent'] = 100 * (maxDuration - minDuration) / minDuration
        segmentData['trace'] = current['trace']
        segmentsDict[currentDateTime] = segmentData
    od = OrderedDict(sorted(segmentsDict.items()))
    return od.values()


def collectData():
    st = time.time()
    trendIntervals, activity, activityIntervals, activityMetrics, activitySeason, info = retrieveData()
    et1 = time.time()
    matchingIntervalsDF, segmentNamesAttempts = prepareData(trendIntervals,
                                                            activityIntervals,
                                                            activityMetrics,
                                                            activitySeason,
                                                            activity)
    et2 = time.time()
    print("retrieveData took {:.3f} seconds".format(et1-st))
    print("prepareData took {:.3f} seconds".format(et2-et1))

    return {
        'overview': createSegmentsOverview(segmentNamesAttempts, activitySeason),
        'data': findSegments(segmentNamesAttempts, matchingIntervalsDF)
    }, info


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
        """ + BOOTSTRAP_CSS_TAG + LEAFLET_CSS_TAG + """
        <title>Route Segments</title>
        <style>
          span.vrank {
            float: left;
            width: 30pt;
            text-align: center;
            font-size: 150%;
          }
          span.rank {
            float: left;
            width: 40pt;
            text-align: right;
          }
          span.attempts {
            float: left;
            width: 40pt;
            text-align: left;
          }
          div.map {
            height: 200px;
          }
          .tableFixHead {
            overflow: auto;
            height: 100px;
          }
          .tableFixHead thead th {
            position: sticky;
            top: 0;
            z-index: 15;
            background-color: white;
          }
        </style>
      </head>
      <body>
        <h1>
          {%- if info.Route | length > 0 -%}{{ info.Route }}{%- else %}Activity{%- endif %}
          ({{ info.date | format_date }})
        </h1>
        <h2>Found {{ segments.overview.numSegments }} route
          {%- if segments.overview.numSegments == 1 -%}segment{%- else %}segments{%- endif %}
          in season <em>{{ info.seasonName}}</em>
          {%- if info.outOfSeason -%}<small class="text-muted">Activity is out of season</small>{%- endif -%}
        </h2>
        <div class="accordion" id="accordionSegments">
        {% for segment in segments.data %}
          <div class="accordion-item">
            <h2 class="accordion-header" id="heading{{ loop.index }}">
              <button class="accordion-button collapsed"
                      type="button"
                      data-bs-toggle="collapse"
                      data-bs-target="#collapse{{ loop.index}}"
                      aria-expanded="false"
                      aria-controls="collapse{{ loop.index }}">
                <span class="vrank">
                {%- if segment.numAttempts > 1 -%}
                  {%- if segment.rank == 1 -%}&#x1F947;
                  {%- elif segment.rank == 2 -%}&#x1F948;
                  {%- elif segment.rank == 3 -%}&#x1F949;
                  {%- elif segment.rank == segment.numAttempts -%}&#x1F3EE;
                  {%- else -%}
                    <div class="progress">
                      <div class="progress-bar"
                           role="progressbar"
                           style="width: {{ segment.rankPercent }}%"
                           aria-valuenow="{{ segment.rankPercent }}"
                           aria-valuemin="0"
                           aria-valuemax="100"></div>
                    </div>
                  {%- endif -%}
                {%- endif -%}
                </span>
                <span class="rank">{{ segment.rank }}</span>&thinsp;/&thinsp;
                <span class="attempts">{{ segment.numAttempts }}</span>{{ segment.name }}
              </button>
            </h2>
            <div id="collapse{{ loop.index }}"
                 class="accordion-collapse collapse"
                 aria-labelledby="heading{{ loop.index }}"
                 data-bs-parent="#accordionSegments">
              <div class="accordion-body">
                <div class="container">
                  <div class="row mb-3">
                    <div class="col">
                      <div class="map" id="map{{ loop.index }}"></div>
                    </div>
                  </div>
                  <div class="row">
                    <div class="col">
                      <h5>Segment Info</h5>
                      <table class="table table-sm">
                        <tbody>
                          <tr>
                            <th scope="row">Distance</th>
                            <td>{{ segment.info.Distance | round(2) }}</td>
                          </tr>
                          <tr>
                            <th scope="row">Elevation gain / loss</th>
                            <td>
                              🡱 {{ segment.info.Elevation_Gain | round(1) }} /
                              🡳 {{ segment.info.Elevation_Loss | round(1) }}
                            </td>
                          </tr>
                          {% if segment.numAttempts > 1 %}
                          <tr>
                            <th scope="row">Attempts between</th>
                            <td>{{ segment.firstAttempt | format_date }} - {{ segment.lastAttempt | format_date }}</td>
                          </tr>
                          <tr>
                            <th scope="row">Δ Fastest / slowest duration</th>
                            <td>{{ segment.deltaDuration | duration }} ({{ segment.deltaPercent | round(1) }}%)</td>
                          </tr>
                          {% endif %}
                        </tbody>
                      </table>
                    </div>
                    {% if segment.numAttempts > 1 %}
                    <div class="col">
                      <h5>Average Attempt</h5>
                      <table class="table table-sm">
                        <tbody>
                          <tr>
                            <th scope="row">Duration</th>
                            <td>{{ segment.averages.Duration | duration }}</td>
                          </tr>
                          {% if segment.hasPower %}
                          <tr>
                            <th scope="row">ø Power</th>
                            <td>{{ segment.averages.Average_Power | show }}</td>
                          </tr>
                          {% endif %}
                          {% if segment.hasHeartRate %}
                          <tr>
                            <th scope="row">ø Heart Rate</th>
                            <td>{{ segment.averages.Average_Heart_Rate | int }}</td>
                          </tr>
                          {% endif %}
                          <tr>
                            <th scope="row">ø Speed</th>
                            <td>{{ segment.averages.Average_Speed | round(2) }}</td>
                          </tr>
                          {% if segment.hasCadence %}
                          <tr>
                            <th scope="row">ø Cadence</th>
                            <td>{{ segment.averages.Average_Cadence | int }}</td>
                          </tr>
                          {% endif %}
                          {% if segment.hasPower %}
                          <tr>
                            <th scope="row">BikeStress</th>
                            <td>{{ segment.averages.BikeStress | int }}</td>
                          </tr>
                          {% endif %}
                        </tbody>
                      </table>
                    </div>
                    {% endif %}
                  </div>
                </div>
                <h5>Leaderboard</h5>
                <table class="table table-sm table-striped tableFixHead">
                  <thead>
                    <tr>
                      <th scope="col">#</th>
                      <th scope="col">Date</th>
                      <th scope="col">Time</th>
                      <th scope="col">Duration</th>
                      {% if segment.numAttempts > 1 %}
                      <th scope="col">Δ Fastest</th>
                      {% endif %}
                      {% if segment.hasPower %}
                      <th scope="col">ø Power</th>
                      {% endif %}
                      {% if segment.hasHeartRate %}
                      <th scope="col">ø Heart Rate</th>
                      {% endif %}
                      <th scope="col">ø Speed</th>
                      {% if segment.hasCadence %}
                      <th scope="col">ø Cadence</th>
                      {% endif %}
                      {% if segment.hasPower %}
                      <th scope="col">BikeStress</th>
                      {% endif %}
                      <th scope="col">VAM</th>
                    </tr>
                  </thead>
                  <tbody>
                  {% for attempt in segment.attempts %}
                    {%if attempt.isCurrent %}
                    <tr class="table-primary">
                    {% else %}
                    <tr>
                    {% endif %}
                      <th scope="row">{{ loop.index }}</th>
                      <td>{{ attempt.date | format_date }}</td>
                      <td>{{ attempt.time }}</td>
                      <td>{{ attempt.Duration | duration }}</td>
                      {% if segment.numAttempts > 1 -%}
                      <td>{%- if loop.index > 1 -%}{{ attempt.deltaDuration | duration }}
                      ({{ attempt.deltaPercent | round(1) }}%){%- endif -%}</td>
                      {%- endif %}
                      {% if segment.hasPower %}
                      <td>{{ attempt.Average_Power | show }}</td>
                      {% endif %}
                      {% if segment.hasHeartRate %}
                      <td>{{ attempt.Average_Heart_Rate | int | show }}</td>
                      {% endif %}
                      <td>{{ attempt.Average_Speed | round(2) }}</td>
                      {% if segment.hasCadence %}
                      <td>{{ attempt.Average_Cadence | int | show }}</td>
                      {% endif %}
                      {% if segment.hasPower %}
                      <td>{{ attempt.BikeStress | int }}</td>
                      {% endif %}
                      <td>{{ attempt.VAM | int }}</td>
                    </tr>
                  {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>
            <script>
              var acc = document.getElementById('collapse{{ loop.index }}')
              acc.addEventListener('shown.bs.collapse', function (event) {
                var map = L.map('map{{ loop.index }}', {
                  scrollWheelZoom: false,
                  maxZoom: """ + MAP_MAX_ZOOM + """
                });

                L.tileLayer('""" + MAP_PROVIDER + """', {
                    attribution: '""" + MAP_ATTRIBUTION + """'
                }).addTo(map);

                var latlngs = [
                {%- for trace in segment.trace -%}
                  [{{ trace[0] }}, {{ trace[1] }}],
                {%- endfor -%}
                ];
                var polyline = L.polyline(latlngs, {color: '""" + TRACE_COLOR + """'}).addTo(map);
                var markerStart = L.marker(latlngs[0], {icon: greenMarker}).addTo(map);
                var markerFinish = L.marker(latlngs[latlngs.length - 1], {icon: redMarker}).addTo(map);
                var group = new L.featureGroup([polyline, markerStart, markerFinish]);
                map.fitBounds(group.getBounds());
                map.invalidateSize(true);
              })
            </script>
          </div>
        {% endfor %}
        </div>
        """ + BOOTSTRAP_JS_TAG + LEAFLET_JS_TAG + """
        <script type="text/javascript">
          {% for color in ['red', 'green'] %}
          const {{ color }}Marker = L.divIcon({
            html: `
              <svg width="16" height="16" viewBox="0 0 100 100" version="1.1"
                preserveAspectRatio="none"
                xmlns="http://www.w3.org/2000/svg">
                <circle cx="50" cy="50" r="50" fill="{{ color }}" fill-opacity="50%" />
              </svg>`,
            className: "svg-pos-marker",
            iconSize: [16, 16],
            iconAnchor: [8, 8]});
          {% endfor %}
        </script>
      </body>
    </html>""")


def getErrorTemplate():
    return multilineStrip("""<!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        """ + BOOTSTRAP_CSS_TAG + """
        <title>Segments</title>
      </head>
      <body>
        <h1>{{ msg }}</h1>
        {{ resolution }}
        <pre>{{ trace }}</pre>
      </body>
    </html>""")


if __name__ == '__main__':
    main()
