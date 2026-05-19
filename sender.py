"""
sender.py — отправка сообщений в целевой канал с созданием тем.

Исправлено:
* Импорт UpdatePinnedMessageRequest перенесён из channels в messages
  (с этого падал main.py).
* Корректное извлечение id новой темы из ответа CreateForumTopicRequest.
* Reply в форумах — только int (Telethon сам строит InputReplyToMessage).
* Удалены неиспользуемые импорты.
"""

import asyncio
import shutil
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import (
    UpdateMessageID,
    UpdateNewChannelMessage,
    UpdateNewMessage,
)
from telethon.tl.functions.channels import (
    CreateForumTopicRequest,
)
from telethon.tl.functions.messages import (
    UpdatePinnedMessageRequest,
)
from telethon.errors import (
    FloodWaitError,
    ChatAdminRequiredError,
    MessageNotModifiedError,
    MessageIdInvalidError,
    SlowModeWaitError,
)

import ui
from reader import media_type, file_size_mb
from config import temp_dir, cfg_value


# ── Создание / поиск темы ────────────────────────────────────────

def _extract_topic_id(result) -> int | None:
    """
    Из результата CreateForumTopicRequest (Updates) достаёт id новой темы.
    Это id сообщения-якоря темы.
    """
    updates = getattr(result, "updates", None) or []
    # Сначала ищем UpdateMessageID — это финальный id, привязанный к нашему random_id
    for u in updates:
        if isinstance(u, UpdateMessageID):
            return u.id
    # Запасной вариант — извлекаем id из сообщения о создании
    for u in updates:
        if isinstance(u, (UpdateNewChannelMessage, UpdateNewMessage)):
            msg = getattr(u, "message", None)
            if msg and getattr(msg, "id", None):
                return msg.id
    return None


async def ensure_topics_parallel(
    client: TelegramClient,
    dst_entity,
    topics: dict[int, dict],
    state: dict,
    cfg: dict,
) -> int:
    """Создаёт все темы в цели параллельно. Возвращает число новых тем."""
    workers = max(1, int(cfg_value(cfg, "parallel_topic_workers", 3)))
    sem = asyncio.Semaphore(workers)
    created = 0

    async def _one(tid: int, info: dict):
        nonlocal created
        async with sem:
            title = info.get("title") if isinstance(info, dict) else str(info)
            res = await ensure_topic(
                client, dst_entity,
                topic_title=title or f"Тема #{tid}",
                state=state,
                src_topic_id=tid,
                cfg=cfg,
                quiet=True,
            )
            if res:
                created += 1

    await asyncio.gather(*[_one(tid, info) for tid, info in topics.items()])
    return created


async def ensure_topic(
    client: TelegramClient,
    dst_entity,
    topic_title: str,
    state: dict,
    src_topic_id: int,
    delay: float | None = None,
    cfg: dict | None = None,
    quiet: bool = False,
) -> int | None:
    """
    Создаёт тему в dst_entity если её ещё нет.
    Возвращает dst topic_id (id сообщения-якоря темы) или None при неудаче.
    Результат кэшируется в state["topic_map"].
    """
    topic_map: dict = state["topic_map"]
    key = str(src_topic_id)

    if key in topic_map:
        return topic_map[key]

    if delay is None:
        delay = float(cfg_value(cfg or {}, "delay_between_topics", 3.0))
    if not quiet:
        ui.info(f"Создаю тему: [bold]{topic_title}[/bold]")
    if delay > 0:
        await asyncio.sleep(delay)

    for attempt in range(5):
        try:
            result = await client(CreateForumTopicRequest(
                channel=dst_entity,
                title=topic_title or "Без названия",
            ))
            new_topic_id = _extract_topic_id(result)
            if not new_topic_id:
                ui.warn("Не удалось получить id новой темы (пустой ответ API)")
                return None

            topic_map[key] = new_topic_id
            state["total_topics"] += 1
            if not quiet:
                ui.ok(f"Тема создана: «{topic_title}» (id={new_topic_id})")
            return new_topic_id

        except FloodWaitError as e:
            ui.warn(f"FloodWait {e.seconds}с при создании темы…")
            await asyncio.sleep(e.seconds + 3)
        except ChatAdminRequiredError:
            ui.err("Нет прав на создание тем в целевой группе. Назначьте аккаунт администратором.")
            return None
        except Exception as e:
            ui.err(f"Ошибка создания темы ({attempt+1}/5): {e}")
            await asyncio.sleep(5 * (attempt + 1))

    ui.warn(f"Не удалось создать тему «{topic_title}», отправлю без темы")
    return None


# ── Скачивание медиа ─────────────────────────────────────────────

async def download_msg_media(
    client: TelegramClient,
    msg,
    cfg: dict,
) -> Path | None:
    """Скачивает медиа сообщения во временную папку. Возвращает путь или None."""
    mtype = media_type(msg)
    if mtype in ("none", "other"):
        return None
    if mtype == "photo"    and not cfg.get("download_photos",    True): return None
    if mtype == "video"    and not cfg.get("download_videos",    True): return None
    if mtype in ("document", "audio", "voice", "sticker") and not cfg.get("download_documents", True):
        return None

    max_mb = cfg.get("media_max_size_mb", 500)
    if mtype in ("video", "document", "audio", "voice"):
        size = file_size_mb(msg)
        if size and size > max_mb:
            ui.warn(f"Пропускаю файл {size} МБ > {max_mb} МБ (#{msg.id})")
            return None

    tmp = temp_dir(cfg)
    dest = tmp / f"{msg.id}"

    last_err: Exception | None = None
    for attempt in range(4):
        try:
            path = await client.download_media(msg, file=str(dest))
            return Path(path) if path else None
        except FloodWaitError as e:
            ui.warn(f"FloodWait при скачивании: {e.seconds}с…")
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            last_err = e
            ui.warn(f"Ошибка скачивания #{msg.id} ({attempt+1}/4): {e}")
            await asyncio.sleep(3 * (attempt + 1))

    if last_err:
        ui.err(f"Не смог скачать #{msg.id}: {last_err}")
    return None


# ── Отправка одного сообщения ────────────────────────────────────

async def send_one(
    client: TelegramClient,
    dst_entity,
    msg,
    dst_topic_id: int | None,
    state: dict,
    cfg: dict,
    media_path: Path | None,
) -> int | None:
    """
    Отправляет одно сообщение (текст или медиа) в dst.
    Возвращает id нового сообщения или None.
    """
    text  = _build_text(msg, cfg)
    reply = _resolve_reply(msg, state, dst_topic_id, cfg)

    base_kwargs: dict = {
        "entity": dst_entity,
        "silent": cfg.get("silent_send", True),
    }
    if reply is not None:
        base_kwargs["reply_to"] = reply

    # formatting_entities передаём только если они есть, иначе используется
    # дефолтный parse_mode (markdown) — что нам и нужно, если мы сами
    # добавили "🔗 Оригинал".
    entities = list(msg.entities) if getattr(msg, "entities", None) else None

    for attempt in range(5):
        try:
            if media_path and media_path.exists():
                send_kwargs = dict(base_kwargs, caption=text or "")
                if entities and not cfg.get("add_source_link"):
                    send_kwargs["formatting_entities"] = entities
                sent = await client.send_file(file=str(media_path), **send_kwargs)
            elif text:
                send_kwargs = dict(base_kwargs, message=text)
                if entities and not cfg.get("add_source_link"):
                    send_kwargs["formatting_entities"] = entities
                sent = await client.send_message(**send_kwargs)
            else:
                # Ни текста, ни медиа — отправлять нечего.
                return None

            new_id = sent.id if not isinstance(sent, list) else sent[-1].id
            state["msg_id_map"][str(msg.id)] = new_id
            return new_id

        except FloodWaitError as e:
            ui.warn(f"FloodWait {e.seconds}с (msg #{msg.id})…")
            await asyncio.sleep(e.seconds + 2)
        except SlowModeWaitError as e:
            ui.warn(f"SlowMode: жду {e.seconds}с…")
            await asyncio.sleep(e.seconds + 2)
        except MessageIdInvalidError:
            ui.warn(f"Сообщение #{msg.id}: reply недоступен — отправлю в тему без reply")
            base_kwargs["reply_to"] = dst_topic_id
        except TypeError as e:
            if "Invalid message type" in str(e):
                ui.warn(f"Сообщение #{msg.id}: неверный reply_to — отправлю в тему")
                base_kwargs["reply_to"] = dst_topic_id
            else:
                raise
        except Exception as e:
            ui.warn(f"Ошибка отправки #{msg.id} ({attempt+1}/5): {e}")
            await asyncio.sleep(4 * (attempt + 1))

    return None


# ── Отправка альбома ─────────────────────────────────────────────

async def send_album(
    client: TelegramClient,
    dst_entity,
    msgs: list,
    dst_topic_id: int | None,
    state: dict,
    cfg: dict,
    media_paths: list[Path | None],
) -> int | None:
    """Отправляет группу медиа (альбом) одной пачкой. Возвращает id последнего dst-сообщения."""
    valid = [(p, m) for p, m in zip(media_paths, msgs) if p and p.exists()]
    if not valid:
        return None

    paths  = [str(p) for p, _ in valid]
    anchor = valid[0][1]
    text   = _build_text(anchor, cfg)
    reply  = _resolve_reply(anchor, state, dst_topic_id, cfg)
    entities = list(anchor.entities) if getattr(anchor, "entities", None) else None

    base_kwargs: dict = {
        "entity":  dst_entity,
        "caption": text or "",
        "silent":  cfg.get("silent_send", True),
    }
    if reply is not None:
        base_kwargs["reply_to"] = reply
    if entities and not cfg.get("add_source_link"):
        base_kwargs["formatting_entities"] = entities

    for attempt in range(5):
        try:
            sent = await client.send_file(file=paths, **base_kwargs)
            if isinstance(sent, list):
                for (_, src_m), dst_m in zip(valid, sent):
                    state["msg_id_map"][str(src_m.id)] = dst_m.id
                return sent[-1].id if sent else None
            return getattr(sent, "id", None)

        except FloodWaitError as e:
            ui.warn(f"FloodWait {e.seconds}с (альбом)…")
            await asyncio.sleep(e.seconds + 2)
        except SlowModeWaitError as e:
            ui.warn(f"SlowMode: жду {e.seconds}с…")
            await asyncio.sleep(e.seconds + 2)
        except MessageIdInvalidError:
            base_kwargs["reply_to"] = dst_topic_id
        except TypeError as e:
            if "Invalid message type" in str(e):
                base_kwargs["reply_to"] = dst_topic_id
            else:
                raise
        except Exception as e:
            ui.warn(f"Ошибка отправки альбома ({attempt+1}/5): {e}")
            await asyncio.sleep(4 * (attempt + 1))

    return None


# ── Закрепление ──────────────────────────────────────────────────

async def pin_message(client: TelegramClient, dst_entity, dst_msg_id: int) -> None:
    if not dst_msg_id:
        return
    try:
        await client(UpdatePinnedMessageRequest(
            peer=dst_entity,
            id=dst_msg_id,
            silent=True,
        ))
    except ChatAdminRequiredError:
        ui.warn("Нет прав для закрепления сообщений")
    except MessageNotModifiedError:
        pass  # уже закреплено
    except Exception as e:
        ui.warn(f"Не удалось закрепить #{dst_msg_id}: {e}")


# ── Внутренние хелперы ───────────────────────────────────────────

def _build_text(msg, cfg: dict) -> str:
    text = (getattr(msg, "raw_text", None) or "") or ""

    if cfg.get("add_source_link"):
        chat = None
        try:
            chat = getattr(msg, "chat", None)
        except Exception:
            chat = None
        username = getattr(chat, "username", None) if chat else None
        if username and getattr(msg, "id", None):
            link = f"\n\n🔗 [Оригинал](https://t.me/{username}/{msg.id})"
            text = (text + link).strip()
    return text


def _resolve_reply(msg, state: dict, dst_topic_id: int | None, cfg: dict) -> int | None:
    """
    Возвращает int для reply_to в Telethon (только Message.id или id темы).

    Telethon принимает reply_to: int | Message — НЕ InputReplyToMessage.
    Для форума: id темы = top_msg_id; reply на сообщение = id скопированного msg.
    """
    if not cfg.get("preserve_replies", True):
        return dst_topic_id

    try:
        rt = getattr(msg, "reply_to", None)
        if rt is not None:
            reply_msg_id = getattr(rt, "reply_to_msg_id", None)
            top_id       = getattr(rt, "reply_to_top_id", None)
            is_forum     = bool(getattr(rt, "forum_topic", False))

            if is_forum:
                if reply_msg_id and (top_id is None or reply_msg_id != top_id):
                    dst_reply = state["msg_id_map"].get(str(reply_msg_id))
                    if dst_reply:
                        return int(dst_reply)
                return dst_topic_id
            if reply_msg_id:
                dst_reply = state["msg_id_map"].get(str(reply_msg_id))
                if dst_reply:
                    return int(dst_reply)
    except Exception:
        pass

    return dst_topic_id


def cleanup_temp(cfg: dict) -> None:
    """Очищает папку временных файлов."""
    tmp = Path(cfg.get("media_temp_dir", "tmp_media"))
    if tmp.exists():
        try:
            shutil.rmtree(tmp)
        except Exception:
            pass
        try:
            tmp.mkdir(exist_ok=True)
        except Exception:
            pass
