import os

from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "distilgpt2"
MODEL_PATH = "./model"


def _get_model_source() -> str:
    if os.path.isfile(os.path.join(MODEL_PATH, "config.json")):
        return MODEL_PATH
    return MODEL_NAME


model_source = _get_model_source()
tokenizer = AutoTokenizer.from_pretrained(model_source, use_fast=False)
model = AutoModelForCausalLM.from_pretrained(model_source)

if model_source == MODEL_NAME:
    os.makedirs(MODEL_PATH, exist_ok=True)
    model.save_pretrained(MODEL_PATH)
    tokenizer.save_pretrained(MODEL_PATH)


def generate_response(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_length=100,
        do_sample=True,
        temperature=0.9,
        top_k=50,
        top_p=0.95,
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)
