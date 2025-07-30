import os
import time
from openai import OpenAI
from dotenv import load_dotenv  # <-- dodano

load_dotenv()  # <-- dodano

# ✅ Ustaw swój klucz API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ASSISTANT_NAME = "TreningowyAnalizator"
VECTOR_STORE_NAME = "tcx_vector_store"

def upload_file_to_openai(filepath):
    print(f"📤 Uploaduję plik: {filepath}")

    temp_path = "temp_upload.xml"
    with open(filepath, "rb") as src, open(temp_path, "wb") as dst:
        dst.write(src.read())

    with open(temp_path, "rb") as f:
        file = client.files.create(file=f, purpose="assistants")

    print(f"✅ Upload zakończony. file_id: {file.id}")
    return file

def get_or_create_vector_store():
    stores = client.beta.vector_stores.list().data
    for store in stores:
        if store.name == VECTOR_STORE_NAME:
            return store
    return client.beta.vector_stores.create(name=VECTOR_STORE_NAME)

def attach_file_to_vector_store(vector_store_id, file_id):
    client.beta.vector_stores.file_batches.create(
        vector_store_id=vector_store_id,
        file_ids=[file_id]
    )

def get_or_create_assistant(vector_store_id):
    assistants = client.beta.assistants.list().data
    for assistant in assistants:
        if assistant.name == ASSISTANT_NAME:
            return assistant
    return client.beta.assistants.create(
        name=ASSISTANT_NAME,
        instructions=(
            "Jesteś trenerem biegowym. Analizuj dane z pliku TCX (trening biegowy): "
            "podaj dystans, czas, tempo, tętno, przewyższenia, interwały. "
            "Na końcu dodaj motywacyjny komentarz."
        ),
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
        model="gpt-4o"
    )


def analyze_tcx_with_assistant(assistant_id):
    thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Proszę przeanalizuj mój trening z załączonego pliku TCX."
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

    print("⏳ GPT analizuje plik...")
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            break
        elif run.status in ["failed", "expired"]:
            raise Exception(f"❌ Run nie powiódł się: {run.status}")
        time.sleep(2)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    return messages.data[0].content[0].text.value.strip()

def main():
    # 🔍 Znajdź najnowszy .tcx
    files = sorted([f for f in os.listdir() if f.endswith(".tcx")], reverse=True)
    if not files:
        print("❌ Nie znaleziono pliku .tcx.")
        return

    tcx_file = files[0]
    print(f"📂 Analizuję plik: {tcx_file}")

    # ✅ Upload
    file = upload_file_to_openai(tcx_file)

    # 🧠 Utwórz lub znajdź vector store
    vector_store = get_or_create_vector_store()

    # 📎 Podłącz plik
    attach_file_to_vector_store(vector_store.id, file.id)

    response = client.responses.create(
        model="gpt-4o",
        instructions="Jesteś trenerem biegowym. Analizuj dane z pliku TCX (trening biegowy): "
            "podaj dystans, czas, tempo, tętno, przewyższenia, interwały. "
            "Na końcu dodaj motywacyjny komentarz.",
        input="How do I check if a Python object is an instance of a class?",
    )

    print(response.output_text)

    with open("summary.txt", "w") as f:
        f.write(response.output_text)
    print("✅ Zapisano do summary.txt")

if __name__ == "__main__":
    main()
