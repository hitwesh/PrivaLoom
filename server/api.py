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
    print("Applying REAL aggregated updates...")

    num_updates = len(updates)
    aggregated: list[list[float]] = []

    for i in range(len(updates[0])):
        slice_sum = [0.0] * len(updates[0][i])
        for update in updates:
            for j in range(len(update[i])):
                slice_sum[j] += update[i][j]
        slice_avg = [value / num_updates for value in slice_sum]
        aggregated.append(slice_avg)

    with torch.no_grad():
        param_index = 0
        for param in model.parameters():
            if param.requires_grad:
                if param_index < len(aggregated):
                    update_tensor = torch.tensor(aggregated[param_index])
                    flat_param = param.view(-1)
                    flat_param[: len(update_tensor)] += update_tensor
                    param_index += 1

    print("Model updated with REAL aggregation!")
