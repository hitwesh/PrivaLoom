from fastapi import FastAPI
from pydantic import BaseModel

from model.load_model import generate_response

app = FastAPI()

class ChatRequest(BaseModel):
    prompt: str

@app.get("/")
def home() -> dict[str, str]:
    return {"message": "Server is running"}

@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    user_input = request.prompt
    response = generate_response(user_input)
    return {"input": user_input, "response": response}
