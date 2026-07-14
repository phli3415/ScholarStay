import os
import logging
from typing import Optional

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


IMPORT_LLM_MODEL = "gpt-4o-mini"


class LLMExtractedFields(BaseModel):
    has_kitchen:  bool          = Field(False, description="listing mentions a kitchen or cooking facilities")
    has_washer:   bool          = Field(False, description="listing mentions washer, dryer, or laundry")
    has_parking:  bool          = Field(False, description="listing mentions parking, garage, or driveway")
    raw_address:  Optional[str] = Field(None,  description="full address string as it appears in the text, e.g. '123 Main St'")
    city:         Optional[str] = Field(None,  description="city name")
    province:     Optional[str] = Field(None,  description="US state abbreviation or full name")


def _build_import_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=IMPORT_LLM_MODEL,
        temperature=0,
        timeout=30,
        max_retries=2,
    )


async def llm_extract(body: str, need_fields: list[str]) -> LLMExtractedFields:
    """
    Call gpt-4o-mini once to fill only the fields listed in need_fields.
    Fields not in need_fields are left at their defaults and must NOT be used by the caller.
    """
    field_lines = "\n".join(f"- {f}" for f in need_fields)
    prompt = (
        "Extract the following fields from the housing listing text below.\n"
        "Only extract what is explicitly stated. "
        "If a field cannot be determined from the text, use null or false.\n\n"
        f"Fields to extract:\n{field_lines}\n\n"
        f"Listing text:\n{body}"
    )
    logger.info("LLM request | need_fields=%s", need_fields)
    llm = _build_import_llm()
    structured = llm.with_structured_output(LLMExtractedFields)
    result = await structured.ainvoke(prompt)
    logger.info("LLM result  | %s", result.model_dump())
    return result
