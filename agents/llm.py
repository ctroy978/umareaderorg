import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_xai import ChatXAI

load_dotenv()


@lru_cache(maxsize=1)
def get_worker_llm() -> ChatXAI:
    return ChatXAI(
        model="grok-3-mini-fast",
        api_key=os.environ["XAI_API_KEY"],
        temperature=0.7,
    )


@lru_cache(maxsize=1)
def get_judge_llm() -> ChatXAI:
    return ChatXAI(
        model="grok-3-mini-fast",
        api_key=os.environ["XAI_API_KEY"],
        temperature=0.0,
    )


@lru_cache(maxsize=1)
def get_planner_llm() -> ChatXAI:
    return ChatXAI(
        model="grok-3-mini",
        api_key=os.environ["XAI_API_KEY"],
        temperature=0.7,
    )


@lru_cache(maxsize=1)
def get_feedback_llm() -> ChatXAI:
    return ChatXAI(model="grok-3", api_key=os.environ["XAI_API_KEY"], temperature=0.3)
