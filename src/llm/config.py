"""
LLM configuration for Canopy API (OpenAI-compatible).
Uses environment variable CANOPY_API_KEY - never hardcode keys in production.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = os.getenv("MODEL", "openai/gpt-oss-120b")


def get_llm(temperature=0.7, max_tokens=1000, **kwargs):
    """Get configured ChatOpenAI instance for Groq API."""
    api_key = os.getenv("API_KEY_GROQ")
    if not api_key:
        raise ValueError("API_KEY_GROQ environment variable is required")
    
    return ChatOpenAI(
        base_url=GROQ_BASE_URL,
        api_key=api_key,
        model=DEFAULT_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
