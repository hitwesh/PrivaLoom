import random
import requests

CHAT_URL = "http://127.0.0.1:8000/chat"
UPDATE_URL = "http://127.0.0.1:8000/send-update"


def main() -> None:
    while True:
        user_input = input("You: ")
        response = requests.post(CHAT_URL, json={"prompt": user_input}, timeout=30)
        result = response.json()
        print("Bot:", result.get("response", ""))

        fake_update = {"weights": [random.random() for _ in range(5)]}
        update_response = requests.post(UPDATE_URL, json=fake_update, timeout=30)
        print("Update status:", update_response.json())


if __name__ == "__main__":
    main()
