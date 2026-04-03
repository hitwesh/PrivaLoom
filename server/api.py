from fastapi import FastAPI
from pydantic import BaseModel

from model.load_model import generate_response

app = FastAPI()

class ChatRequest(BaseModel):
    prompt: str


class UpdateRequest(BaseModel):
    weights: list

@app.get("/")
def home() -> dict[str, str]:
    return {"message": "Server is running"}

@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    user_input = request.prompt
    response = generate_response(user_input)
    return {"input": user_input, "response": response}


@app.post("/send-update")
def receive_update(update: UpdateRequest) -> dict[str, str]:
    print("Received update:", update.weights)
    return {"status": "update received"}
