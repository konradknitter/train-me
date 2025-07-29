import os
import openai

# ✅ Ustaw swój klucz API
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def upload_tcx_file(filepath):
    print(f"📤 Uploaduję plik: {filepath}")

    # Zapisz plik tymczasowy z odpowiednim rozszerzeniem .xml
    temp_path = "temp_upload.xml"
    with open(filepath, "rb") as src, open(temp_path, "wb") as dst:
        dst.write(src.read())

    # Teraz upload jako XML (akceptowalny format)
    with open(temp_path, "rb") as f:
        file = client.files.create(file=f, purpose="assistants")

    print(f"✅ Upload zakończony. file_id: {file.id}")
    return file.id

def ask_gpt_with_file(file_id):
    print(f"🤖 Tworzę asystenta GPT do analizy TCX...")

    # Stwórz asystenta, który będzie analizował pliki XML/TCX
    assistant = client.beta.assistants.create(
        name="Treningowy Analizator TCX",
        instructions=(
            "Jesteś ekspertem od biegania. "
            "Na podstawie danych TCX oceń bieg: dystans, czas, tempo, intensywność, tętno, interwały, przewyższenia. "
            "Zakończ krótkim motywacyjnym komentarzem."
        ),
        tools=[{"type": "file_search"}],
        model="gpt-4-turbo"
    )

    # Utwórz nowy wątek
    thread = client.beta.threads.create()

    # Dodaj wiadomość użytkownika (bez file_ids!)
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Załączam plik TCX do analizy treningu.",
    )

    # Uruchom analizę (asystent + plik)
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        file_ids=[file_id]
    )

    # Poczekaj aż GPT zakończy analizę
    import time
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            break
        elif run.status in ["failed", "expired"]:
            raise Exception(f"❌ Run zakończony błędem: {run.status}")
        print("⏳ Czekam na odpowiedź GPT...")
        time.sleep(2)

    # Pobierz odpowiedź
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    latest = messages.data[0].content[0].text.value.strip()

    return latest

def main():
    # Szukamy najnowszego pliku .tcx
    files = sorted([f for f in os.listdir() if f.endswith(".tcx")], reverse=True)
    if not files:
        print("❌ Nie znaleziono pliku .tcx.")
        return

    tcx_file = files[0]
    file_id = upload_tcx_file(tcx_file)
    summary = ask_gpt_with_file(file_id)

    print("🧠 Odpowiedź GPT:")
    print(summary)

    with open("summary.txt", "w") as f:
        f.write(summary)
    print("✅ Zapisano do summary.txt")

if __name__ == "__main__":
    main()
