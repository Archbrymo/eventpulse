import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "qwen3.8-max"

api_key = os.environ.get("BITGET_QWEN_API_KEY")

if not api_key:
    raise RuntimeError(
        "BITGET_QWEN_API_KEY is missing. Check the project .env file."
    )

client = OpenAI(
    api_key=api_key,
    base_url="https://hackathon.bitgetops.com/v1",
)
