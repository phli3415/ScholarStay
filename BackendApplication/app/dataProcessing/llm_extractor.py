import os
from typing import Optional

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI


IMPORT_LLM_MODEL = "gpt-4o-mini"


class LLMExtractedFields(BaseModel):
    has_kitchen:  bool          = Field(False, description="listing mentions a kitchen or cooking facilities")
    has_washer:   bool          = Field(False, description="listing mentions washer, dryer, or laundry")
    has_parking:  bool          = Field(False, description="listing mentions parking, garage, or driveway")
    street:       Optional[str] = Field(None,  description="street name only, no house number")
    house_number: Optional[str] = Field(None,  description="house/unit number prefix of the address")
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
    llm = _build_import_llm()
    structured = llm.with_structured_output(LLMExtractedFields)
    return await structured.ainvoke(prompt)
