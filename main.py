from model.load_model import generate_response


def main() -> None:
    while True:
        text = input("You: ")
        print("Bot:", generate_response(text))


if __name__ == "__main__":
    main()
