"""Script that contains the Pydantic Models for the Rest Request."""
from enum import Enum

from fastapi import UploadFile
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):

    """The LLM Provider Enum."""

    ALEPH_ALPHA = "aa"
    OPENAI = "openai"
    GPT4ALL = "gpt4all"

    @classmethod
    def normalize(cls: type["LLMProvider"], value: str) -> "LLMProvider":
        """Normalize the LLM provider."""
        normalized_value = value.lower().replace("-", "").replace("_", "")
        if normalized_value in {"aa", "alephalpha"}:
            return cls.ALEPH_ALPHA
        elif normalized_value == "openai":
            return cls.OPENAI
        elif normalized_value == "gpt4all":
            return cls.GPT4ALL
        else:
            msg = f"Unsupported LLM provider: {value}"
            raise ValueError(msg)


class Language(str, Enum):

    """The Language Enum."""

    DETECT = "detect"
    GERMAN = "de"
    ENGLISH = "en"


class LLMBackend(BaseModel):

    """The LLM Backend Model."""

    llm_provider: LLMProvider = Field(LLMProvider.ALEPH_ALPHA, description="The LLM provider to use for embedding.")
    token: str | None = Field(None, description="The API token for the LLM provider.")
    collection_name: str | None = Field(None, description="The name of the Qdrant Collection.")


class Filtering(BaseModel):

    """The Filtering Model."""

    threshold: float = Field(0.0, title="Threshold", description="The threshold to use for the search.")
    filter: dict | None = Field(None, title="Filter", description="Filter for the database search with metadata.")


class EmbeddTextFilesRequest(BaseModel):

    """The request for the Embedd Text Files endpoint."""

    files: list[UploadFile] = Field(..., description="The list of text files to embed.")
    seperator: str = Field("###", description="The seperator to use between embedded texts.")


class SearchRequest(BaseModel):

    """The request parameters for searching the database."""

    query: str = Field(..., title="Query", description="The search query.")
    amount: int = Field(3, title="Amount", description="The number of search results to return.")


class EmbeddTextRequest(BaseModel):

    """The request parameters for embedding text."""

    text: str = Field(..., title="Text", description="The text to embed.")
    file_name: str = Field(..., title="File Name", description="The name of the file to save the embedded text to.")
    seperator: str = Field("###", title="seperator", description="The seperator to use between embedded texts.")


class CustomPromptCompletion(BaseModel):

    """The Custom Prompt Completion Model."""

    token: str = Field(..., title="Token", description="The API token for the LLM provider.")
    prompt: str = Field(..., title="Prompt", description="The prompt to use for the completion.")
    model: str = Field(..., title="Model", description="The model to use for the completion.")
    max_tokens: int = Field(256, title="Max Tokens", description="The maximum number of tokens to generate.")
    temperature: float = Field(..., title="Temperature", description="The temperature to use for the completion.")
    stop_sequences: list[str] = Field([], title="Stop Sequences", description="The stop sequences to use for the completion.")


class RAGRequest(BaseModel):

    """Request for the QA endpoint."""

    language: Language | None = Field(Language.DETECT, title="Language", description="The language to use for the answer.")
    history: dict[str, str] | None = Field([], title="History", description="A list of previous questions and answers to include in the context.")


class ExplainQARequest(BaseModel):

    """Request for the QA endpoint."""

    rag_request: RAGRequest
    explain_threshold: float = Field(0.7, title="Explain Threshold", description="The threshold to use for the explanation.")
