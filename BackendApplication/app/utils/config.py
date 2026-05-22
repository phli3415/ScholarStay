import os

#Config Class
class Config:

    #prompt file path
    PROMPT_TEMPLATE_TXT_KEYWORD = "prompts/prompt_template_keyWordExtraction.txt"
    PROMPT_TEMPLATE_TXT_CLARIFICATION = "prompts/prompt_template_clarification.txt"
    PROMPT_TEMPLATE_TXT_GRADE = "prompts/prompt_template_resultGrading.txt"
    PROMPT_TEMPLATE_TXT_CHITCHAT = "prompts/prompt_template_chitChat.txt"
    PROMPT_TEMPLATE_TXT_SUMMARY = "prompts/prompt_template_memorySummarizer.txt"
    PROMPT_TEMPLATE_TXT_RECOMMENDATION = "prompts/prompt_template_recommendationGeneration.txt"

    #pgvector

    LOG_FILE = "output/app.log"
    MAX_BYTES = 5 * 1024 * 1024
    BACKUP_COUNT = 3

    LLM_TYPE = "openai"


    HOST = "0.0.0.0"
    PORT = 8080