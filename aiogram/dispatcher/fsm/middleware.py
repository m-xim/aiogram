from typing import Any, Awaitable, Callable, Dict, Optional, cast

from aiogram import Bot
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.dispatcher.fsm.storage.base import DEFAULT_DESTINY, BaseStorage, StorageKey
from aiogram.dispatcher.fsm.strategy import FSMStrategy, apply_strategy
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject


class FSMContextMiddleware(BaseMiddleware):
    def __init__(
        self,
        storage: BaseStorage,
        strategy: FSMStrategy = FSMStrategy.USER_IN_CHAT,
        isolate_events: bool = True,
    ) -> None:
        self.storage = storage
        self.strategy = strategy
        self.isolate_events = isolate_events

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        bot: Bot = cast(Bot, data["bot"])
        context = self.resolve_event_context(bot, data)
        data["fsm_storage"] = self.storage
        if context:
            data.update({"state": context, "raw_state": await context.get_state()})
            if self.isolate_events:
                async with self.storage.lock(bot=bot, key=context.key):
                    return await handler(event, data)
        return await handler(event, data)

    def resolve_event_context(
        self,
        bot: Bot,
        data: Dict[str, Any],
        destiny: str = DEFAULT_DESTINY,
    ) -> Optional[FSMContext]:
        user = data.get("event_from_user")
        chat = data.get("event_chat")
        chat_id = chat.id if chat else None
        user_id = user.id if user else None
        return self.resolve_context(bot=bot, chat_id=chat_id, user_id=user_id, destiny=destiny)

    def resolve_context(
        self,
        bot: Bot,
        chat_id: Optional[int],
        user_id: Optional[int],
        destiny: str = DEFAULT_DESTINY,
    ) -> Optional[FSMContext]:
        if chat_id is None:
            chat_id = user_id

        if chat_id is not None and user_id is not None:
            chat_id, user_id = apply_strategy(
                chat_id=chat_id, user_id=user_id, strategy=self.strategy
            )
            return self.get_context(bot=bot, chat_id=chat_id, user_id=user_id, destiny=destiny)
        return None

    def get_context(
        self,
        bot: Bot,
        chat_id: int,
        user_id: int,
        destiny: str = DEFAULT_DESTINY,
    ) -> FSMContext:
        return FSMContext(
            bot=bot,
            storage=self.storage,
            key=StorageKey(
                user_id=user_id,
                chat_id=chat_id,
                bot_id=bot.id,
                destiny=destiny,
            ),
        )
