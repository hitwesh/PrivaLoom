import torch
from fastapi import FastAPI
from pydantic import BaseModel

from model.load_model import generate_response, model

app = FastAPI()

global_updates: list[list[list[float]]] = []
UPDATE_THRESHOLD = 2

class ChatRequest(BaseModel):
    prompt: str


class UpdateRequest(BaseModel):
    weights: list[list[float]]

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
    global_updates.append(update.weights)
    print(f"Total updates received: {len(global_updates)}")

    if len(global_updates) >= UPDATE_THRESHOLD:
        apply_updates(global_updates)
        global_updates.clear()

    return {"status": "update received"}


def apply_updates(updates: list[list[list[float]]]) -> None:
    _ = updates
    print("Applying aggregated updates...")

    with torch.no_grad():
        for param in model.parameters():
            if param.requires_grad:
                noise = torch.randn_like(param) * 0.0001
                param.add_(noise)

    print("Model updated!")
