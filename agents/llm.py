import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


@lru_cache(maxsize=1)
def get_worker_llm() -> ChatGroq:
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0.7,
    )


@lru_cache(maxsize=1)
def get_judge_llm() -> ChatGroq:
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0.0,
    )


@lru_cache(maxsize=1)
def get_planner_llm() -> ChatGroq:
    return ChatGroq(
        model="llama-3.1-70b-versatile",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0.7,
    )
