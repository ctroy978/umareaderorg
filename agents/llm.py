import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_xai import ChatXAI

load_dotenv()


_TIMEOUT = 90  # seconds — max wait for any single xAI API call


@lru_cache(maxsize=1)
def get_worker_llm() -> ChatXAI:
    return ChatXAI(
        model="grok-4",
        api_key=os.environ["XAI_API_KEY"],
        temperature=0.7,
        timeout=_TIMEOUT,
    )


@lru_cache(maxsize=1)
def get_judge_llm() -> ChatXAI:
    return ChatXAI(
        model="grok-4-fast-reasoning",
        api_key=os.environ["XAI_API_KEY"],
        temperature=0.0,
        timeout=_TIMEOUT,
    )


@lru_cache(maxsize=1)
def get_planner_llm() -> ChatXAI:
    return ChatXAI(
        model="grok-4-fast-reasoning",
        api_key=os.environ["XAI_API_KEY"],
        temperature=0.7,
        timeout=_TIMEOUT,
    )


@lru_cache(maxsize=1)
def get_feedback_llm() -> ChatXAI:
    return ChatXAI(
        model="grok-4-fast-reasoning",
        api_key=os.environ["XAI_API_KEY"],
        temperature=0.3,
        timeout=_TIMEOUT,
    )
