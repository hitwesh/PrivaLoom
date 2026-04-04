import os
import sys

import requests

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from model.load_model import model, tokenizer

CHAT_URL = "http://127.0.0.1:8000/chat"
UPDATE_URL = "http://127.0.0.1:8000/send-update"
DATA_PATH = os.path.join(ROOT_DIR, "data.txt")


def load_dataset() -> list[str]:
    if not os.path.isfile(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def aggregate_updates(updates: list[list[list[float]]]) -> list[list[float]]:
    if not updates:
        return []

    num_updates = len(updates)
    aggregated: list[list[float]] = []
    for i in range(len(updates[0])):
        slice_sum = [0.0] * len(updates[0][i])
        for update in updates:
            for j in range(len(update[i])):
                slice_sum[j] += update[i][j]
        slice_avg = [value / num_updates for value in slice_sum]
        aggregated.append(slice_avg)
    return aggregated


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


def train_on_dataset(fallback_text: str) -> list[list[float]]:
    samples = load_dataset()
    if not samples:
        return train_and_get_update(fallback_text)
    updates = [train_and_get_update(sample) for sample in samples]
    return aggregate_updates(updates)


def main() -> None:
    dataset_trained = False
    while True:
        user_input = input("You: ")
        response = requests.post(CHAT_URL, json={"prompt": user_input}, timeout=30)
        result = response.json()
        print("Bot:", result.get("response", ""))

        if not dataset_trained:
            print("Training on local dataset...")
            update_weights = train_on_dataset(user_input)
            dataset_trained = True
        else:
            update_weights = train_and_get_update(user_input)

        real_update = {"weights": update_weights}
        update_response = requests.post(UPDATE_URL, json=real_update, timeout=30)
        print("Update status:", update_response.json())


if __name__ == "__main__":
    main()
