from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "distilgpt2"
MODEL_PATH = "./model"


def download_and_save_model() -> None:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

    model.save_pretrained(MODEL_PATH)
    tokenizer.save_pretrained(MODEL_PATH)


if __name__ == "__main__":
    download_and_save_model()
    print("Model saved to ./model")
