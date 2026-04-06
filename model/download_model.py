from transformers import AutoModelForCausalLM, AutoTokenizer
from pathlib import Path

MODEL_NAME = "distilgpt2"
MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = str(MODEL_DIR)


def download_and_save_model() -> None:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

    model.save_pretrained(MODEL_PATH)
    tokenizer.save_pretrained(MODEL_PATH)


if __name__ == "__main__":
    download_and_save_model()
    print(f"Model saved to {MODEL_PATH}")
