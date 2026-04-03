import os
import sys

import requests

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from model.load_model import model

CHAT_URL = "http://127.0.0.1:8000/chat"
UPDATE_URL = "http://127.0.0.1:8000/send-update"


def get_model_update() -> list[list[float]]:
    updates: list[list[float]] = []
    for param in model.parameters():
        updates.append(param.data.view(-1)[:2].tolist())
    return updates[:5]


def main() -> None:
    while True:
        user_input = input("You: ")
        response = requests.post(CHAT_URL, json={"prompt": user_input}, timeout=30)
        result = response.json()
        print("Bot:", result.get("response", ""))

        real_update = {"weights": get_model_update()}
        update_response = requests.post(UPDATE_URL, json=real_update, timeout=30)
        print("Update status:", update_response.json())


if __name__ == "__main__":
    main()
