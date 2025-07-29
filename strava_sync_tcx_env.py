import os
import requests
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, ElementTree
from dotenv import load_dotenv

# Wczytaj zmienne środowiskowe z .env (opcjonalnie)
load_dotenv()

def refresh_access_token():
    """Uzyskaj nowy access_token ze Stravy przy pomocy refresh_token"""
    response = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": os.getenv("STRAVA_CLIENT_ID"),
        "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
        "grant_type": "refresh_token",
        "refresh_token": os.getenv("STRAVA_REFRESH_TOKEN")
    })

    if response.status_code != 200:
        raise Exception(f"Błąd odświeżania tokenu: {response.text}")

    return response.json()["access_token"]

def get_latest_activity(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://www.strava.com/api/v3/athlete/activities?per_page=1"
    resp = requests.get(url, headers=headers)
    return resp.json()[0]

def get_streams(activity_id, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    params = {"keys": "time,latlng,heartrate", "key_by_type": "true"}
    resp = requests.get(url, headers=headers, params=params)
    return resp.json()

def create_tcx(activity, streams, filename="activity.tcx"):
    NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
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

    times = streams.get("time", {}).get("data", [])
    latlngs = streams.get("latlng", {}).get("data", [])
    heartrates = streams.get("heartrate", {}).get("data", [])

    base_time = datetime.fromisoformat(activity["start_date_local"].replace("Z", ""))

    for i, point in enumerate(latlngs):
        trackpoint = SubElement(track, "Trackpoint")

        timestamp = base_time + timedelta(seconds=times[i]) if i < len(times) else base_time
        SubElement(trackpoint, "Time").text = timestamp.isoformat() + "Z"

        pos = SubElement(trackpoint, "Position")
        SubElement(pos, "LatitudeDegrees").text = str(point[0])
        SubElement(pos, "LongitudeDegrees").text = str(point[1])

        if i < len(heartrates):
            hr = SubElement(trackpoint, "HeartRateBpm")
            SubElement(hr, "Value").text = str(heartrates[i])

    ElementTree(root).write(filename, encoding="utf-8", xml_declaration=True)
    print(f"✅ TCX zapisany jako: {filename}")

def main():
    print("🔐 Pobieram token ze zmiennych środowiskowych...")
    access_token = refresh_access_token()
    activity = get_latest_activity(access_token)

    print(f"📌 Aktywność: {activity['name']} | ID: {activity['id']}")
    streams = get_streams(activity["id"], access_token)

    filename = f"activity_{activity['id']}.tcx"
    create_tcx(activity, streams, filename)

if __name__ == "__main__":
    main()