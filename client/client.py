import requests

URL = "http://127.0.0.1:8000/chat"


def main() -> None:
    while True:
        user_input = input("You: ")
        data = {"prompt": user_input}
        response = requests.post(URL, json=data, timeout=30)
        result = response.json()
        print("Bot:", result.get("response", ""))


if __name__ == "__main__":
    main()
