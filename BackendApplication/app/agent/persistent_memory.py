# Persistent Memory for LangChain Agent
# Stores chat history in the database using ChatHistory model

import json
from typing import Dict, Any, List
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from ..model.chat_history import ChatHistory
from ..model.user import User


class PersistentChatMemory(ConversationBufferMemory):
    """
    Custom memory class that persists chat history to the database.
    Inherits from ConversationBufferMemory for compatibility.
    """

    def __init__(self, session_id: str, user_id: int, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.user_id = user_id

    async def save_context(self, messages_list: List[Dict[str, Any]], user_input: str = "") -> None:
        """
        Save the context of the current conversation to the database.
        
        Args:
            messages_list: List of message dicts with structure:
                          [{"role": "user/assistant/tool", "content": "...", "tool_calls": [...], "timestamp": "..."}, ...]
            user_input: Optional user input for title generation on first message
        """
        try:
            # Get or create chat record
            user = await User.get(id=self.user_id)
            chat_record, created = await ChatHistory.get_or_create(
                session_id=self.session_id,
                user=user,
                defaults={"title": "Agent Chat Session"}
            )

            # Generate title if new session and no title
            if created and not chat_record.title and user_input:
                title = await self._generate_title(user_input)
                chat_record.title = title

            # Append messages to existing history
            existing_messages = chat_record.messages or []
            existing_messages.extend(messages_list)
            chat_record.messages = existing_messages

            # Save to database
            await chat_record.save()

        except Exception as e:
            print(f"Error saving context: {e}")
            

    async def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        """
        Load memory variables from the database.
        """
        try:
            user = await User.get(id=self.user_id)
            chat_record = await ChatHistory.get_or_none(session_id=self.session_id, user=user)

            if chat_record and chat_record.messages:
                # Convert JSON messages to LangChain format
                langchain_messages = []
                for msg in chat_record.messages:
                    if msg["role"] == "user":
                        langchain_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        langchain_messages.append(AIMessage(content=msg["content"]))

                # Set buffer
                self.buffer = langchain_messages

            return super().load_memory_variables(inputs)

        except Exception as e:
            print(f"Error loading memory: {e}")
            # Return empty or fallback
            return super().load_memory_variables(inputs)

    async def _generate_title(self, user_input: str) -> str:
        """
        Generate a title for the chat session based on user input.
        """
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
            prompt = f"Generate a short, descriptive title for a chat session about rental properties based on this user query: '{user_input}'. Keep it under 10 words."
            title = await llm.ainvoke(prompt)
            return title.content.strip()
        except Exception as e:
            print(f"Error generating title: {e}")
            return "Agent Chat Session"