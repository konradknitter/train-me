import os
import requests
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, ElementTree

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

def refresh_access_token():
    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": STRAVA_REFRESH_TOKEN
    })
    return resp.json()["access_token"]

def get_latest_activity(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get("https://www.strava.com/api/v3/athlete/activities?per_page=1", headers=headers)
    return resp.json()[0]

def get_streams(activity_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    keys = "time,distance,latlng,altitude,velocity_smooth,heartrate,cadence,watts,temp,moving,grade_smooth"
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    resp = requests.get(url, headers=headers, params={"keys": keys, "key_by_type": "true"})
    return resp.json()

def create_tcx(activity, streams, filename):
    NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
    TPX_NS = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"

    root = Element("TrainingCenterDatabase", xmlns=NS)
    activities_el = SubElement(root, "Activities")
    activity_el = SubElement(activities_el, "Activity", Sport=activity["type"])
    SubElement(activity_el, "Id").text = activity["start_date_local"]
    lap = SubElement(activity_el, "Lap", StartTime=activity["start_date_local"])
    SubElement(lap, "TotalTimeSeconds").text = str(activity["elapsed_time"])
    SubElement(lap, "DistanceMeters").text = str(activity["distance"])
    SubElement(lap, "Calories").text = str(activity.get("calories", 0))
    SubElement(lap, "Intensity").text = "Active"
    track = SubElement(lap, "Track")

    base_time = datetime.fromisoformat(activity["start_date_local"].replace("Z", ""))

    length = len(streams["time"]["data"])
    for i in range(length):
        tp = SubElement(track, "Trackpoint")

        # Time
        timestamp = base_time + timedelta(seconds=streams["time"]["data"][i])
        SubElement(tp, "Time").text = timestamp.isoformat() + "Z"

        # Position
        if "latlng" in streams:
            latlon = streams["latlng"]["data"][i]
            pos = SubElement(tp, "Position")
            SubElement(pos, "LatitudeDegrees").text = str(latlon[0])
            SubElement(pos, "LongitudeDegrees").text = str(latlon[1])

        # Distance
        if "distance" in streams:
            SubElement(tp, "DistanceMeters").text = str(streams["distance"]["data"][i])

        # Altitude
        if "altitude" in streams:
            SubElement(tp, "AltitudeMeters").text = str(streams["altitude"]["data"][i])

        # Heart rate
        if "heartrate" in streams:
            hr = SubElement(tp, "HeartRateBpm")
            SubElement(hr, "Value").text = str(streams["heartrate"]["data"][i])

        # Cadence
        if "cadence" in streams:
            SubElement(tp, "Cadence").text = str(streams["cadence"]["data"][i])

        # Extensions
        extensions = SubElement(tp, "Extensions")
        tpx = SubElement(extensions, f"TPX", xmlns=TPX_NS)

        if "velocity_smooth" in streams:
            SubElement(tpx, "Speed").text = str(streams["velocity_smooth"]["data"][i])

        if "watts" in streams:
            SubElement(tpx, "Watts").text = str(streams["watts"]["data"][i])

        if "temp" in streams:
            SubElement(tpx, "Temp").text = str(streams["temp"]["data"][i])

        if "grade_smooth" in streams:
            SubElement(tpx, "Slope").text = str(streams["grade_smooth"]["data"][i])

    ElementTree(root).write(filename, encoding="utf-8", xml_declaration=True)
    print(f"✅ TCX zapisany jako {filename}")

def main():
    token = refresh_access_token()
    activity = get_latest_activity(token)
    streams = get_streams(activity["id"], token)
    filename = f"activity_{activity['id']}.tcx"
    create_tcx(activity, streams, filename)

if __name__ == "__main__":
    main()
