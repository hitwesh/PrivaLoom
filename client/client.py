import os
import sys

import requests
import torch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from model.load_model import model, tokenizer

CHAT_URL = "http://127.0.0.1:8000/chat"
UPDATE_URL = "http://127.0.0.1:8000/send-update"


def train_and_get_update(text: str) -> list[list[float]]:
    model.zero_grad()
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs, labels=inputs["input_ids"])
    loss = outputs.loss
    loss.backward()

    gradients: list[list[float]] = []
    for param in model.parameters():
        if param.grad is not None:
            gradients.append(param.grad.view(-1)[:2].tolist())
    return gradients[:5]


def main() -> None:
    while True:
        user_input = input("You: ")
        response = requests.post(CHAT_URL, json={"prompt": user_input}, timeout=30)
        result = response.json()
        print("Bot:", result.get("response", ""))

        real_update = {"weights": train_and_get_update(user_input)}
        update_response = requests.post(UPDATE_URL, json=real_update, timeout=30)
        print("Update status:", update_response.json())


if __name__ == "__main__":
    main()
