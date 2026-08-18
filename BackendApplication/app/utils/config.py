import os

#Config Class
class Config:

    #prompt file path
    PROMPT_TEMPLATE_TXT_KEYWORD = "app/prompts/prompt_template_keyWordExtraction.txt"
    PROMPT_TEMPLATE_TXT_CLARIFICATION = "app/prompts/prompt_template_clarification.txt"
    PROMPT_TEMPLATE_TXT_GRADE = "app/prompts/prompt_template_resultGrading.txt"
    PROMPT_TEMPLATE_TXT_CHITCHAT = "app/prompts/prompt_template_chitChat.txt"
    PROMPT_TEMPLATE_TXT_SUMMARY = "app/prompts/prompt_template_memorySummarizer.txt"
    PROMPT_TEMPLATE_TXT_RECOMMENDATION = "app/prompts/prompt_template_recommendationGeneration.txt"

    #pgvector

    LOG_FILE = "output/app.log"
    MAX_BYTES = 5 * 1024 * 1024
    BACKUP_COUNT = 3

    LLM_TYPE = "openai"

    # RAG candidate pool size — how many houses the similarity search retrieves
    # for grading, before relevance filtering narrows it down.
    EMBEDDING_HOUSES_RETURN = 10
    # Max houses actually shown to the user after grading (house_ids/recommendation
    # are both capped to this, so they always stay in sync with each other).
    MAX_RECOMMENDATIONS = 3


    HOST = "0.0.0.0"
    PORT = 8080