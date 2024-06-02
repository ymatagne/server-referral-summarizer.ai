from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
import time
import shutil

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "TOTO"))

def wait_on_run(run, thread):
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file format")

    temp_file_path = f"/tmp/{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Upload file using the temporary file path
    with open(temp_file_path, "rb") as temp_file:
        uploaded_file = client.files.create(file=temp_file, purpose="assistants")

    # Remove the temporary file
    os.remove(temp_file_path)

    my_thread = client.beta.threads.create()
    my_thread_message = client.beta.threads.messages.create(
        thread_id=my_thread.id,
        role="user",
        content="Summary",
        attachments=[{"file_id":uploaded_file.id,"tools":[ { "type": "file_search" },{ "type": "code_interpreter" }]}]
        )

    my_run = client.beta.threads.runs.create(
        thread_id=my_thread.id,
        assistant_id="asst_HNbmFvEPqx8HVJoJ8nD6SE6B",
        model='gpt-4o-2024-05-13'
    )
    wait_on_run(my_run, my_thread)

    all_messages = client.beta.threads.messages.list(thread_id=my_thread.id)
    print(f"User: {my_thread_message.content[0].text.value}")
    print(f"Assistant: {all_messages.data[0].content[0].text.value}")

    return all_messages.data[0].content[0].text.value

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
