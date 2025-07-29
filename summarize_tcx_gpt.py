import os
import openai

# ✅ Ustaw swój klucz API
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def upload_tcx_file(filepath):
    print(f"📤 Uploaduję plik: {filepath}")
    with open(filepath, "rb") as f:
        file = client.files.create(file=f, purpose="assistants")
    return file.id

def ask_gpt_with_file(file_id):
    print(f"🤖 Wysyłam zapytanie do GPT z plikiem ID: {file_id}")
    prompt = (
        "Przeanalizuj ten plik TCX i podsumuj mój trening biegowy. "
        "Wypisz dystans, czas, tempo, tętno, przewyższenia i ogólną jakość treningu. "
        "Zakończ krótkim motywacyjnym komentarzem."
    )

    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt,
        file_ids=[file_id]
    )

    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=None, model="gpt-4-turbo")

    # Czekaj na zakończenie
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            break
        elif run.status in ["failed", "cancelled", "expired"]:
            raise Exception(f"❌ Błąd run: {run.status}")
        import time; time.sleep(2)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    answer = messages.data[0].content[0].text.value.strip()
    return answer

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
