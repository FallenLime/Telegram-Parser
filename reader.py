"""
reader.py — чтение структуры исходного канала (топики, сообщения, альбомы).
"""

import asyncio
from typing import AsyncIterator

from telethon import TelegramClient
from telethon.tl.types import (
    Channel, Chat,
    MessageMediaPhoto, MessageMediaDocument,
    DocumentAttributeVideo, DocumentAttributeAudio,
    DocumentAttributeSticker,
    ForumTopic,
    InputMessagesFilterEmpty,
)
from telethon.tl.functions.channels import (
    GetForumTopicsRequest,
    GetFullChannelRequest,
)
from telethon.tl.functions.messages import SearchRequest
from telethon.errors import FloodWaitError, RPCError

import ui
from config import get_logger


# ── Helpers ───────────────────────────────────────────────────────

def media_type(msg) -> str:
    if not msg or not msg.media:
        return "none"
    if isinstance(msg.media, MessageMediaPhoto):
        return "photo"
    if isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        if doc is None:
            return "other"
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeVideo):
                return "video"
            if isinstance(attr, DocumentAttributeSticker):
                return "sticker"
            if isinstance(attr, DocumentAttributeAudio):
                return "voice" if getattr(attr, "voice", False) else "audio"
        return "document"
    return "other"


def file_size_mb(msg) -> float:
    try:
        if isinstance(msg.media, MessageMediaDocument):
            return round(msg.media.document.size / 1024 / 1024, 2)
    except Exception:
        pass
    return 0.0


def get_topic_id(msg) -> int | None:
    """Возвращает top_msg_id темы сообщения (None = General / нет топиков)."""
    try:
        if msg.reply_to and getattr(msg.reply_to, "forum_topic", False):
            return msg.reply_to.reply_to_top_id or msg.reply_to.reply_to_msg_id
    except Exception:
        pass
    return None


_GENERAL_TOPIC_TITLES = frozenset({
    "general", "general chat", "общее", "общий чат", "основное",
})


def _topic_title(entry) -> str:
    if isinstance(entry, dict):
        return (entry.get("title") or "").strip()
    return (str(entry or "")).strip()


def topic_top_message_id(src_topics: dict | None, topic_id: int) -> int | None:
    """
  ID якорного сообщения темы для GetRepliesRequest.
  Нельзя подставлять topic_id — иначе TOPIC_ID_INVALID.
    """
    entry = (src_topics or {}).get(topic_id)
    if isinstance(entry, dict):
        top = entry.get("top_message")
        if top and int(top) > 0:
            return int(top)
    return None


def get_general_topic_ids(src_topics: dict | None) -> set[int]:
    """ID тем General / «общий чат» в форуме (всегда включает 1)."""
    ids = {1}
    for tid, entry in (src_topics or {}).items():
        if _topic_title(entry).lower() in _GENERAL_TOPIC_TITLES:
            ids.add(tid)
    return ids


def get_named_topic_ids(src_topics: dict | None) -> set[int]:
    """Именованные темы (всё, кроме General)."""
    if not src_topics:
        return set()
    general = get_general_topic_ids(src_topics)
    return {tid for tid in src_topics if tid not in general}


def is_named_topic_message(msg, src_topics: dict | None) -> bool:
    """Сообщение принадлежит именованной теме форума (не General и не «без темы»)."""
    tid = get_topic_id(msg)
    if tid is None:
        return False
    return tid in get_named_topic_ids(src_topics)


def is_general_topic_message(msg, src_topics: dict | None = None) -> bool:
    """Сообщение из General / болталки."""
    return not is_named_topic_message(msg, src_topics)


def should_copy_message(msg, src_info: dict, src_topics: dict | None, cfg: dict) -> bool:
    """
    Нужно ли копировать сообщение с учётом copy_general_topic.

    Выкл → не копируем:
      • весь канал/группу без форума (это один «обычный чат»);
      • тему General и сообщения без темы;
      • только именованные темы форума.
    """
    if cfg.get("copy_general_topic", True):
        return True

    if not src_info.get("forum"):
        return False

    return is_named_topic_message(msg, src_topics)


# ── Информация о канале ───────────────────────────────────────────

async def get_entity_info(client: TelegramClient, entity) -> dict:
    """Возвращает удобный dict с метаданными канала/группы."""
    about = ""
    count = getattr(entity, "participants_count", None)

    if isinstance(entity, Channel):
        try:
            full = await client(GetFullChannelRequest(channel=entity))
            about = full.full_chat.about or ""
            count = full.full_chat.participants_count
        except Exception:
            pass

    is_forum = getattr(entity, "forum", False)
    ch_type  = "Канал"
    if isinstance(entity, Chat):
        ch_type = "Группа"
    elif isinstance(entity, Channel):
        ch_type = "Супергруппа" if entity.megagroup else "Канал"

    username = getattr(entity, "username", None)
    return {
        "id":           entity.id,
        "title":        getattr(entity, "title", ""),
        "username":     f"@{username}" if username else "приватный",
        "type":         ch_type,
        "participants": count if count is not None else "?",
        "forum":        is_forum,
        "about":        (about[:100] + "…") if len(about) > 100 else about,
    }


# ── Топики ────────────────────────────────────────────────────────

async def fetch_topics(client: TelegramClient, entity) -> dict[int, str]:
    """Возвращает dict {topic_id: topic_title} для forum-канала."""
    if not getattr(entity, "forum", False):
        return {}

    topics: dict[int, str] = {}
    offset_topic = 0
    offset_id = 0
    offset_date = 0

    while True:
        try:
            res = await client(GetForumTopicsRequest(
                channel=entity,
                q="",
                offset_date=offset_date,
                offset_id=offset_id,
                offset_topic=offset_topic,
                limit=100,
            ))
        except FloodWaitError as e:
            ui.warn(f"FloodWait при загрузке тем: {e.seconds}с…")
            await asyncio.sleep(e.seconds + 2)
            continue
        except Exception as e:
            ui.warn(f"Не удалось получить темы: {e}")
            break

        batch = [t for t in res.topics if isinstance(t, ForumTopic)]
        msgs_by_id = {
            m.id: m for m in (getattr(res, "messages", None) or [])
            if getattr(m, "id", None)
        }
        for t in batch:
            top = int(getattr(t, "top_message", 0) or 0)
            if top <= 0:
                top = 0
            topics[t.id] = {
                "title": t.title,
                "top_message": top,
            }
        # Дополняем top_message из пакета messages API
        for tid, info in list(topics.items()):
            if info.get("top_message", 0) > 0:
                continue
            for m in msgs_by_id.values():
                rt = getattr(m, "reply_to", None)
                if not rt:
                    continue
                top_id = getattr(rt, "reply_to_top_id", None)
                if top_id and int(top_id) == tid:
                    anchor = getattr(rt, "reply_to_msg_id", None) or m.id
                    if anchor and int(anchor) > 0:
                        info["top_message"] = int(anchor)
                        break

        if not batch or len(res.topics) < 100:
            break

        last = batch[-1]
        offset_topic = last.id
        offset_id = getattr(last, "top_message", 0) or 0
        offset_date = getattr(last, "date", 0) or 0
        if hasattr(offset_date, "timestamp"):
            offset_date = int(offset_date.timestamp())
        await asyncio.sleep(0.5)

    return topics


# ── Итерация сообщений ────────────────────────────────────────────

async def iter_messages_asc(
    client_or_takeout,
    entity,
    min_id: int = 0,
    max_id: int | None = None,
    reply_to: int | None = None,
) -> AsyncIterator:
    """Асинхронный генератор сообщений от старых к новым."""
    kwargs: dict = {"limit": None, "reverse": True}
    if min_id:
        kwargs["min_id"] = min_id
    if max_id:
        kwargs["max_id"] = max_id
    if reply_to is not None:
        kwargs["reply_to"] = reply_to

    async for msg in client_or_takeout.iter_messages(entity, **kwargs):
        yield msg


async def _iter_topic_via_search(
    client,
    peer,
    top_msg_id: int,
    min_id: int,
    max_id: int | None,
) -> AsyncIterator:
    """
    Чтение сообщений темы через messages.search + top_msg_id.
    GetReplies для форумов не работает (TOPIC_ID_INVALID).
    """
    offset_id = 0
    last_yielded = int(min_id or 0)
    limit = 100

    while True:
        result = await client(SearchRequest(
            peer=peer,
            q="",
            filter=InputMessagesFilterEmpty(),
            min_date=None,
            max_date=None,
            offset_id=offset_id,
            add_offset=0,
            limit=limit,
            max_id=int(max_id or 0),
            min_id=last_yielded,
            hash=0,
            top_msg_id=int(top_msg_id),
        ))
        messages = [m for m in result.messages if getattr(m, "id", None)]
        if not messages:
            break

        messages.sort(key=lambda m: m.id)
        yielded_any = False
        for msg in messages:
            mid = int(msg.id)
            if mid <= last_yielded:
                continue
            if max_id and mid > max_id:
                return
            yield msg
            last_yielded = mid
            yielded_any = True

        if len(messages) < limit:
            break
        next_offset = int(messages[-1].id)
        if next_offset <= offset_id and not yielded_any:
            break
        offset_id = next_offset


async def _iter_topic_via_filter(
    client,
    entity,
    topic_id: int,
    min_id: int,
    max_id: int | None,
) -> AsyncIterator:
    """Запасной вариант: полный поток с фильтром по topic_id (медленнее, но надёжно)."""
    async for msg in iter_messages_asc(client, entity, min_id=min_id, max_id=max_id):
        tid = get_topic_id(msg)
        if tid == topic_id:
            yield msg


async def iter_topic_messages_asc(
    client,
    entity,
    top_message_id: int | None,
    min_id: int = 0,
    max_id: int | None = None,
    topic_id: int | None = None,
) -> AsyncIterator:
    """Сообщения одной темы форума (старые → новые)."""
    log = get_logger()
    if topic_id is None and (not top_message_id or top_message_id <= 0):
        return

    peer = await client.get_input_entity(entity)
    # messages.search top_msg_id = ID темы форума (ForumTopic.id), не anchor message
    search_ids: list[int] = []
    if topic_id:
        search_ids.append(int(topic_id))
    if top_message_id and int(top_message_id) > 0 and int(top_message_id) not in search_ids:
        search_ids.append(int(top_message_id))

    for sid in search_ids:
        count = 0
        try:
            async for msg in _iter_topic_via_search(client, peer, sid, min_id, max_id):
                yield msg
                count += 1
            if count > 0:
                log.debug("topic %s: %s msgs via search id=%s", topic_id, count, sid)
                return
        except FloodWaitError as e:
            log.warning("FloodWait search topic %s: %ss", topic_id, e.seconds)
            await asyncio.sleep(e.seconds + 2)
        except RPCError as e:
            log.warning("search failed topic=%s top=%s: %s", topic_id, sid, e)

    if topic_id:
        log.info("topic %s: fallback to filtered history", topic_id)
        async for msg in _iter_topic_via_filter(client, entity, topic_id, min_id, max_id):
            yield msg


def filter_topics_with_valid_top(src_topics: dict) -> dict[int, dict]:
    """Темы, которые можно читать (есть top_message или хотя бы topic id)."""
    return dict(src_topics)


# ── Группировка альбомов ──────────────────────────────────────────

def group_albums(messages: list) -> list:
    """Принимает список сообщений (уже в порядке ASC),
    возвращает список: одиночные сообщения ИЛИ списки сообщений (альбом).
    """
    result:  list = []
    seen_albums: set = set()
    albums: dict[int, list] = {}

    for msg in messages:
        gid = getattr(msg, "grouped_id", None)
        if gid:
            albums.setdefault(gid, []).append(msg)

    for msg in messages:
        gid = getattr(msg, "grouped_id", None)
        if gid:
            if gid in seen_albums:
                continue
            seen_albums.add(gid)
            result.append(albums[gid])
        else:
            result.append(msg)

    return result


# ── Классификация диалогов и список ───────────────────────────────

def _classify_dialog(ent) -> str:
    """Возвращает строковую категорию диалога:
       broadcast | forum | supergroup | legacy_chat | other
    """
    if isinstance(ent, Chat):
        return "legacy_chat"
    if isinstance(ent, Channel):
        if getattr(ent, "forum", False):
            return "forum"
        if getattr(ent, "megagroup", False):
            return "supergroup"
        return "broadcast"
    return "other"


def _is_regular_chat(ent) -> bool:
    """Считаем «обычным чатом, где общаются люди»:
       — все Chat (legacy small groups)
       — мегагруппы, у которых не включены темы (просто чат)
    Каналы (broadcast) и форум-супергруппы — НЕ считаем флудом.
    """
    cat = _classify_dialog(ent)
    return cat in ("legacy_chat", "supergroup")


async def list_dialogs(
    client: TelegramClient,
    hide_regular_chats: bool = False,
) -> list[dict]:
    """Возвращает список ваших каналов/групп. С опциональной фильтрацией."""
    result = []
    async for dialog in client.iter_dialogs():
        ent = dialog.entity
        if not isinstance(ent, (Channel, Chat)):
            continue
        if hide_regular_chats and _is_regular_chat(ent):
            continue
        is_forum = getattr(ent, "forum", False)
        ch_type = "группа"
        if isinstance(ent, Channel):
            if ent.megagroup:
                ch_type = "супергруппа 📋" if is_forum else "супергруппа"
            else:
                ch_type = "канал"
        result.append({
            "id":                 ent.id,
            "title":              getattr(ent, "title", "") or "(без названия)",
            "type":               ch_type,
            "forum":              is_forum,
            "participants_count": getattr(ent, "participants_count", "?"),
            "category":           _classify_dialog(ent),
        })
    return sorted(result, key=lambda x: (x["title"] or "").lower())
