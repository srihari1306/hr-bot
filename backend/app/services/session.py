from asyncio import Lock as AsyncLock
from threading import Lock

from cachetools import TTLCache

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

SESSION_TTL_SECONDS = 3600
MAX_CONVERSATIONS = 10000
MAX_TURNS = 5
MAX_MEMORY_MESSAGES = MAX_TURNS * 2

_memories: TTLCache[str, InMemoryChatMessageHistory] = TTLCache(
    maxsize=MAX_CONVERSATIONS,
    ttl=SESSION_TTL_SECONDS,
)
_conversation_locks: TTLCache[str, AsyncLock] = TTLCache(
    maxsize=MAX_CONVERSATIONS,
    ttl=SESSION_TTL_SECONDS,
)
_memory_lock = Lock()


def _get_memory(conversation_id: str) -> InMemoryChatMessageHistory:
    with _memory_lock:
        memory = _memories.get(conversation_id)
        if memory is None:
            memory = InMemoryChatMessageHistory()
            _memories[conversation_id] = memory
        return memory


def _get_conversation_lock(conversation_id: str) -> AsyncLock:
    with _memory_lock:
        lock = _conversation_locks.get(conversation_id)
        if lock is None:
            lock = AsyncLock()
            _conversation_locks[conversation_id] = lock
        return lock


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
    async with _get_conversation_lock(conversation_id):
        memory = _get_memory(conversation_id)
        await memory.aadd_messages(
            [
                HumanMessage(content=user_msg),
                AIMessage(content=assistant_msg),
            ]
        )
        if len(memory.messages) > MAX_MEMORY_MESSAGES:
            memory.messages = memory.messages[-MAX_MEMORY_MESSAGES:]
