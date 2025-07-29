import os
import time
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def upload_tcx_file(filepath):
    print(f"📤 Uploaduję plik: {filepath}")

    temp_path = "temp_upload.xml"
    with open(filepath, "rb") as src, open(temp_path, "wb") as dst:
        dst.write(src.read())

    with open(temp_path, "rb") as f:
        file = client.files.create(file=f, purpose="assistants")

    print(f"✅ Upload zakończony. file_id: {file.id}")
    return file.id

def ask_gpt_with_file(file_id):
    print("🤖 Tworzę wiadomość z plikiem TCX do analizy...")

    # 🔁 Utwórz wątek
    thread = client.beta.threads.create()

    # 📨 Dodaj wiadomość z plikiem
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Załączam plik TCX do analizy treningu.",
        file_ids=[file_id]
    )

    # ▶️ Uruchom GPT z modelem gpt-4-o (lub gpt-3.5-turbo jeśli wolisz)
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        model="gpt-4o",
        instructions=(
            "Jesteś ekspertem od biegania. "
            "Analizuj dane z pliku TCX: dystans, czas, tempo, interwały, tętno, przewyższenia. "
            "Na końcu dodaj 1-zdaniowy komentarz motywacyjny."
        )
    )

    print("⏳ Czekam na odpowiedź GPT...")
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            break
        elif run.status in ["failed", "expired"]:
            raise Exception(f"❌ Błąd: run zakończony jako {run.status}")
        time.sleep(2)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    latest = messages.data[0].content[0].text.value.strip()
    return latest

def main():
    files = sorted([f for f in os.listdir() if f.endswith(".tcx")], reverse=True)
    if not files:
        print("❌ Nie znaleziono żadnego pliku .tcx.")
        return

    tcx_file = files[0]
    print(f"📂 Analizuję plik: {tcx_file}")

    file_id = upload_tcx_file(tcx_file)
    summary = ask_gpt_with_file(file_id)

    print("🧠 Odpowiedź GPT:")
    print(summary)

    with open("summary.txt", "w") as f:
        f.write(summary)
    print("✅ Zapisano do summary.txt")

if __name__ == "__main__":
    main()
