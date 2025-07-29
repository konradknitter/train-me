import os
import xml.etree.ElementTree as ET
from datetime import datetime
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")  # Ustaw w GitHub Secrets

def extract_summary_from_tcx(tcx_path):
    ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}
    tree = ET.parse(tcx_path)
    root = tree.getroot()

    times = []
    distances = []
    heart_rates = []

    for tp in root.findall(".//tcx:Trackpoint", ns):
        time_el = tp.find("tcx:Time", ns)
        dist_el = tp.find("tcx:DistanceMeters", ns)
        hr_el = tp.find("tcx:HeartRateBpm/tcx:Value", ns)

        if time_el is not None:
            times.append(datetime.fromisoformat(time_el.text.replace("Z", "")))
        if dist_el is not None:
            distances.append(float(dist_el.text))
        if hr_el is not None:
            heart_rates.append(int(hr_el.text))

    if not times or not distances:
        raise ValueError("Nie udało się znaleźć danych GPS lub czasu w pliku TCX.")

    duration_min = round((times[-1] - times[0]).total_seconds() / 60)
    distance_km = round(max(distances) / 1000, 2)
    avg_hr = round(sum(heart_rates) / len(heart_rates)) if heart_rates else None

    return {
        "distance_km": distance_km,
        "duration_min": duration_min,
        "avg_hr": avg_hr
    }

def ask_gpt_for_summary(summary):
    prompt = f"""
Podsumuj bieg na podstawie danych:

- Dystans: {summary['distance_km']} km
- Czas: {summary['duration_min']} minut
""" + (f"- Średnie tętno: {summary['avg_hr']} bpm" if summary['avg_hr'] else "") + """

Dodaj motywacyjny komentarz (1 zdanie)."""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

def main():
    # Szukaj ostatniego TCX w katalogu
    files = sorted([f for f in os.listdir() if f.endswith(".tcx")], reverse=True)
    if not files:
        print("❌ Nie znaleziono żadnego pliku .tcx w katalogu.")
        return

    latest_tcx = files[0]
    print(f"📂 Przetwarzam plik: {latest_tcx}")

    summary = extract_summary_from_tcx(latest_tcx)
    gpt_response = ask_gpt_for_summary(summary)

    print("🧠 Podsumowanie GPT:")
    print(gpt_response)

    with open("summary.txt", "w") as f:
        f.write(gpt_response)

    print("✅ Zapisano do summary.txt")

if __name__ == "__main__":
    main()
