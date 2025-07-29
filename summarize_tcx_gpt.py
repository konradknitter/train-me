import os
import time
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def upload_tcx_file(filepath):
    print(f"📤 Uploaduję plik: {filepath}")

    # Konwertuj na .xml (bo OpenAI nie akceptuje .tcx)
    temp_path = "temp_upload.xml"
    with open(filepath, "rb") as src, open(temp_path, "wb") as dst:
        dst.write(src.read())

    with open(temp_path, "rb") as f:
        file = client.files.create(file=f, purpose="assistants")

    print(f"✅ Upload zakończony. file_id: {file.id}")
    return file.id

def ask_gpt_with_file(file_id):
    print("🤖 Tworzę asystenta GPT do analizy TCX...")

    assistant = client.beta.assistants.create(
        name="Treningowy Analizator TCX",
        instructions=(
            "Jesteś trenerem biegowym. Analizujesz dane z pliku TCX. "
            "Podaj dystans, czas, średnie tempo, tętno, przewyższenia i interwały (jeśli są). "
            "Oceń intensywność i wykonanie treningu. Dodaj 1-zdaniowy komentarz motywacyjny."
        ),
        tools=[{"type": "file_search"}],
        model="gpt-4-o"
    )

    thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Załączam plik TCX do analizy treningu."
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        file_ids=[file_id]
    )

    print("⏳ Czekam na analizę GPT...")
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
