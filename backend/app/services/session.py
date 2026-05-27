from threading import Lock

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

MAX_MEMORY_MESSAGES = 6

_memories: dict[str, InMemoryChatMessageHistory] = {}
_memory_lock = Lock()


def _get_memory(conversation_id: str) -> InMemoryChatMessageHistory:
    with _memory_lock:
        memory = _memories.get(conversation_id)
        if memory is None:
            memory = InMemoryChatMessageHistory()
            _memories[conversation_id] = memory
        return memory


async def get_history(conversation_id: str) -> list[dict]:
    """Get recent conversation history from LangChain memory."""
    memory = _get_memory(conversation_id)
    messages = memory.messages[-MAX_MEMORY_MESSAGES:]

    history: list[dict] = []
    for message in messages:
        role = message.type
        if role == "human":
            role = "user"
        elif role == "ai":
            role = "assistant"
        history.append({"role": role, "content": message.content})

    return history


async def append_turn(conversation_id: str, user_msg: str, assistant_msg: str) -> None:
    """Persist the latest turn in LangChain memory."""
    memory = _get_memory(conversation_id)
    await memory.aadd_messages(
        [
            HumanMessage(content=user_msg),
            AIMessage(content=assistant_msg),
        ]
    )
    if len(memory.messages) > MAX_MEMORY_MESSAGES:
        memory.messages = memory.messages[-MAX_MEMORY_MESSAGES:]
