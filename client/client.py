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
DATA_PATH = os.path.join(ROOT_DIR, "data.txt")


def _get_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


DP_ENABLED = _get_env_bool("DP_ENABLED", True)
DP_MAX_GRAD_NORM = _get_env_float("DP_MAX_GRAD_NORM", 1.0)
DP_NOISE_STDDEV = _get_env_float("DP_NOISE_STDDEV", 0.001)


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
    model.train()
    model.zero_grad()
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs, labels=inputs["input_ids"])
    loss = outputs.loss
    loss.backward()

    if DP_ENABLED:
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=DP_MAX_GRAD_NORM)
        if DP_NOISE_STDDEV > 0:
            for param in model.parameters():
                if param.grad is not None:
                    param.grad.add_(torch.randn_like(param.grad) * DP_NOISE_STDDEV)

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
