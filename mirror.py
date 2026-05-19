"""
mirror.py — оркестратор зеркалирования.
"""

import asyncio
from pathlib import Path
from typing import AsyncIterator

from telethon import TelegramClient

import ui
import i18n
from reader import (
    get_entity_info, fetch_topics,
    get_topic_id, get_general_topic_ids, get_named_topic_ids,
    topic_top_message_id, _topic_title,
    iter_messages_asc, iter_topic_messages_asc,
    filter_topics_with_valid_top,
)
from sender import (
    ensure_topic, ensure_topics_parallel, download_msg_media,
    send_one, send_album, pin_message, cleanup_temp,
)
from config import load_state, save_state, temp_dir, get_logger, cfg_value

SAVE_EVERY = 25
_SKIP_UI_EVERY = 40
_END = object()


def _item_anchor(item):
    return item[0] if isinstance(item, list) else item


def _topics_for_mirror(src_topics: dict, cfg: dict) -> dict[int, dict]:
    if cfg.get("copy_general_topic", True):
        base = dict(src_topics)
    else:
        named = get_named_topic_ids(src_topics)
        base = {tid: src_topics[tid] for tid in named if tid in src_topics}
    return filter_topics_with_valid_top(base)


def _use_topic_only_reading(src_info: dict, cfg: dict) -> bool:
    """Не читать общий поток — только отдельные темы (быстрее, без General)."""
    return bool(src_info.get("forum")) and not cfg.get("copy_general_topic", True)


async def run_mirror(
    client: TelegramClient,
    src_input,
    dst_input,
    cfg: dict,
    min_id: int | None = None,
    max_id: int | None = None,
) -> dict:
    try:
        src = await client.get_entity(_normalize_input(src_input))
    except Exception as e:
        raise RuntimeError(i18n.t("err_source_not_found", e=e))

    try:
        dst = await client.get_entity(_normalize_input(dst_input))
    except Exception as e:
        raise RuntimeError(i18n.t("err_dest_not_found", e=e))

    src_info = await get_entity_info(client, src)
    dst_info = await get_entity_info(client, dst)

    parallel = (
        cfg.get("experimental_parallel_topics")
        and src_info.get("forum")
        and dst_info.get("forum")
        and not cfg.get("dry_run")
    )

    if parallel or _use_topic_only_reading(src_info, cfg):
        if not src_info.get("forum"):
            raise RuntimeError(i18n.t("err_non_forum_general_off"))
        return await _run_mirror_by_topics(
            client, src, dst, src_info, dst_info, cfg, min_id, max_id,
            parallel=parallel,
        )

    return await _run_mirror_sequential(
        client, src, dst, src_info, dst_info, cfg, min_id, max_id,
    )


async def _run_mirror_sequential(
    client, src, dst, src_info, dst_info, cfg, min_id, max_id,
) -> dict:
    """Полный поток канала (когда копируется General или источник без форума)."""
    log = get_logger()
    state = load_state(src_info["id"], dst_info["id"])
    resume_from = state.get("last_msg_id", 0) or 0
    effective_min = max(resume_from, int(min_id or 0))

    src_topics: dict = {}
    if src_info["forum"]:
        src_topics = await fetch_topics(client, src)

    general_ids = get_general_topic_ids(src_topics) if src_info["forum"] else set()

    ui.mirror_prep_summary(
        src_info, dst_info, cfg,
        topics=len(src_topics), resume=resume_from, general_ids=general_ids,
    )
    await asyncio.sleep(0.6)

    dst_general_topic: int | None = None
    stats = _empty_stats(src_info, dst_info, state)

    prefetch = max(1, int(cfg_value(cfg, "prefetch_count", 3)))
    dl_sem = asyncio.Semaphore(max(1, int(cfg_value(cfg, "concurrent_downloads", 2))))
    item_queue: asyncio.Queue = asyncio.Queue(maxsize=prefetch)

    dashboard = ui.MirrorDashboard(src_info, dst_info, cfg, resume_from=resume_from, topics_count=len(src_topics))
    dashboard.update_stats(sent=state["total_sent"], media=state["total_media"], topics=state["total_topics"])

    async def producer():
        try:
            async for item in _group_stream(
                iter_messages_asc(client, src, min_id=effective_min, max_id=max_id)
            ):
                paths = await _download_for_item(client, item, cfg, dl_sem)
                await item_queue.put((item, paths))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("producer error: %s", e)
            ui.err(i18n.t("read_error", e=e))
        finally:
            await item_queue.put(_END)

    saved_count = 0

    async def consumer():
        nonlocal saved_count, dst_general_topic
        while True:
            entry = await item_queue.get()
            if entry is _END:
                dashboard.flush_skip_status()
                return
            item, paths = entry
            try:
                await _process_item(
                    item, paths,
                    client=client, dst=dst, dst_info=dst_info, src_info=src_info,
                    src_topics=src_topics, dst_general_topic=dst_general_topic,
                    state=state, stats=stats, cfg=cfg, dashboard=dashboard,
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.exception("consumer error: %s", e)
                stats["errors"] += 1
                dashboard.update_stats(errors=stats["errors"])
            saved_count += len(item) if isinstance(item, list) else 1
            if saved_count >= SAVE_EVERY:
                save_state(src_info["id"], dst_info["id"], state)
                saved_count = 0
            _cleanup_stale_tmp(cfg)

    try:
        with dashboard.session():
            if (
                not src_info["forum"] and dst_info["forum"]
                and cfg.get("copy_general_topic", True) and not cfg.get("dry_run")
            ):
                dst_general_topic = await ensure_topic(
                    client, dst, topic_title=src_info["title"] or "Source",
                    state=state, src_topic_id=0, cfg=cfg,
                )
            dashboard.progress.update(dashboard.task_id, description=f"[bold]{i18n.t('copying')}[/]")
            await asyncio.gather(producer(), consumer())
            if stats["sent"] == 0 and not cfg.get("dry_run"):
                dashboard.push_log(f"  [{ui.YELLOW}]{i18n.t('warn_zero_sent', topics=0, total=0)}[/]")
            else:
                dashboard.push_log(f"  [{ui.GREEN}]{i18n.t('mirror_complete', sent=stats['sent'])}[/]")
            await asyncio.sleep(0.8)
    finally:
        save_state(src_info["id"], dst_info["id"], state)
        cleanup_temp(cfg)

    return _stats_output(stats, src_info, dst_info)


async def _run_mirror_by_topics(
    client, src, dst, src_info, dst_info, cfg, min_id, max_id, *, parallel: bool,
) -> dict:
    """Читает только выбранные темы — General/обычный чат не загружается."""
    log = get_logger()
    state = load_state(src_info["id"], dst_info["id"])
    src_topics = await fetch_topics(client, src)
    general_ids = get_general_topic_ids(src_topics)
    mirror_topics = _topics_for_mirror(src_topics, cfg)

    if not mirror_topics:
        raise RuntimeError(i18n.t("err_no_forum_topics"))

    all_named = {tid: src_topics[tid] for tid in get_named_topic_ids(src_topics) if tid in src_topics}
    if cfg.get("copy_general_topic", True):
        all_named = dict(src_topics)
    invalid_count = max(0, len(all_named) - len(mirror_topics))

    ui.mirror_prep_summary(
        src_info, dst_info, cfg,
        topics=len(mirror_topics), resume=0, general_ids=general_ids, parallel=parallel,
    )
    await asyncio.sleep(0.6)

    stats = _empty_stats(src_info, dst_info, state)
    dashboard = ui.MirrorDashboard(src_info, dst_info, cfg, topics_count=len(mirror_topics))
    topic_sem = asyncio.Semaphore(max(1, int(cfg_value(cfg, "parallel_topic_workers", 3))))
    state_lock = asyncio.Lock()

    try:
        with dashboard.session():
            dashboard.push_log(f"  [{ui.PURPLE}]{i18n.t('topic_copy_start', n=len(mirror_topics))}[/]")
            if not cfg.get("copy_general_topic", True):
                dashboard.push_log(f"  [{ui.MUTED}]{i18n.t('only_named_topics')}[/]")
            if invalid_count:
                dashboard.push_log(
                    f"  [{ui.YELLOW}]{invalid_count} topic(s) skipped (no valid anchor message)[/]"
                )

            if not cfg.get("dry_run"):
                await ensure_topics_parallel(client, dst, mirror_topics, state, cfg)
                dashboard.push_log(
                    f"  [{ui.GREEN}]{i18n.t('topics_ready', n=len(state['topic_map']))}[/]"
                )

            topics_done = 0
            topics_with_msgs = 0

            async def copy_one_topic(tid: int, info: dict):
                nonlocal topics_done, topics_with_msgs
                title = _topic_title(info)
                top_msg = topic_top_message_id(src_topics, tid)

                topic_last = state.setdefault("topic_last_msg", {})
                t_min = max(int(topic_last.get(str(tid), 0) or 0), int(min_id or 0))
                dl_sem = asyncio.Semaphore(max(1, int(cfg_value(cfg, "concurrent_downloads", 2))))
                had_msgs = False

                async with topic_sem:
                    dashboard.update_stats(current_topic=title[:42])
                    try:
                        async for item in _group_stream(
                            iter_topic_messages_asc(
                                client, src, top_msg,
                                min_id=t_min, max_id=max_id, topic_id=tid,
                            )
                        ):
                            had_msgs = True
                            paths = await _download_for_item(client, item, cfg, dl_sem)
                            async with state_lock:
                                await _process_item(
                                    item, paths,
                                    client=client, dst=dst,
                                    dst_info=dst_info, src_info=src_info,
                                    src_topics=src_topics,
                                    dst_general_topic=None,
                                    state=state, stats=stats, cfg=cfg,
                                    dashboard=dashboard,
                                    force_topic_id=tid,
                                )
                                msgs = item if isinstance(item, list) else [item]
                                topic_last[str(tid)] = msgs[-1].id
                                state["last_msg_id"] = max(
                                    state.get("last_msg_id", 0) or 0, msgs[-1].id,
                                )
                    except Exception as e:
                        log.exception("topic %s failed: %s", tid, e)
                        dashboard.push_log(
                            f"  [{ui.RED}]{i18n.t('topic_copy_failed', title=title, e=e)}[/]"
                        )
                        stats["errors"] += 1
                    finally:
                        topics_done += 1
                        if had_msgs:
                            topics_with_msgs += 1
                        dashboard.progress.update(
                            dashboard.task_id,
                            description=(
                                f"[bold]{i18n.t('copying')}[/] "
                                f"{topics_done}/{len(mirror_topics)} topics"
                            ),
                        )

            if parallel:
                results = await asyncio.gather(
                    *[copy_one_topic(tid, info) for tid, info in mirror_topics.items()],
                    return_exceptions=True,
                )
                for r in results:
                    if isinstance(r, Exception):
                        log.exception("parallel topic gather: %s", r)
                        stats["errors"] += 1
            else:
                for tid, info in mirror_topics.items():
                    await copy_one_topic(tid, info)

            if stats["sent"] == 0 and not cfg.get("dry_run"):
                dashboard.push_log(
                    f"  [{ui.YELLOW}]{i18n.t('warn_zero_sent', topics=topics_with_msgs, total=len(mirror_topics))}[/]"
                )
            else:
                dashboard.push_log(
                    f"  [{ui.GREEN}]{i18n.t('mirror_complete', sent=stats['sent'])}[/]"
                )
            await asyncio.sleep(0.8)

    finally:
        save_state(src_info["id"], dst_info["id"], state)
        cleanup_temp(cfg)

    return _stats_output(stats, src_info, dst_info)


def _empty_stats(src_info, dst_info, state) -> dict:
    return {
        "source": src_info["title"],
        "dest": dst_info["title"],
        "sent": state["total_sent"],
        "media": state["total_media"],
        "topics": state["total_topics"],
        "skipped_chat": 0,
        "skipped_fwd": 0,
        "errors": 0,
    }


def _stats_output(stats: dict, src_info, dst_info) -> dict:
    """UI-friendly stats dict with translated keys."""
    return {
        i18n.t("stat_source"): src_info["title"],
        i18n.t("stat_dest"): dst_info["title"],
        i18n.t("stat_sent"): stats["sent"],
        i18n.t("stat_media"): stats["media"],
        i18n.t("stat_topics"): stats["topics"],
        i18n.t("stat_skipped"): stats["skipped_chat"] + stats["skipped_fwd"],
        i18n.t("stat_errors"): stats["errors"],
    }


async def _process_item(
    item, paths,
    *,
    client, dst, dst_info, src_info, src_topics,
    dst_general_topic, state, stats, cfg, dashboard,
    force_topic_id: int | None = None,
):
    is_album = isinstance(item, list)
    msgs = item if is_album else [item]
    anchor = msgs[0]
    progress = dashboard.progress
    task_msg = dashboard.task_id

    def _sync(**extra):
        dashboard.update_stats(
            sent=state["total_sent"], media=state["total_media"],
            topics=state["total_topics"], errors=stats["errors"],
            skipped=stats["skipped_chat"] + stats["skipped_fwd"],
            last_id=state.get("last_msg_id") or "—", **extra,
        )

    if cfg.get("skip_forwards") and getattr(anchor, "forward", None):
        state["last_msg_id"] = max(state.get("last_msg_id", 0) or 0, msgs[-1].id)
        stats["skipped_fwd"] += len(msgs)
        if progress and task_msg is not None:
            progress.advance(task_msg, len(msgs))
        dashboard.note_skip(len(msgs), msgs[-1].id, kind=i18n.t("skip_forward"))
        return

    dst_topic = dst_general_topic
    src_tid = force_topic_id or get_topic_id(anchor)

    if src_info["forum"] and dst_info["forum"] and src_tid and not cfg.get("dry_run"):
        title = _topic_title(src_topics.get(src_tid, {}))
        dashboard.update_stats(current_topic=(title or f"#{src_tid}")[:42])
        dst_topic = await ensure_topic(
            client, dst, topic_title=title or f"Topic #{src_tid}",
            state=state, src_topic_id=src_tid, cfg=cfg,
            quiet=bool(cfg.get("experimental_parallel_topics")),
        )

    had_media = bool(paths) if not is_album else any(paths)

    if cfg.get("dry_run"):
        if had_media:
            state["total_media"] += sum(1 for p in (paths if is_album else [paths]) if p)
        state["total_sent"] += len(msgs)
        state["last_msg_id"] = max(state.get("last_msg_id", 0) or 0, msgs[-1].id)
        stats["sent"] = state["total_sent"]
        stats["media"] = state["total_media"]
        if progress and task_msg is not None:
            progress.advance(task_msg, len(msgs))
        _sync()
        return

    new_id = None
    if is_album:
        for p in paths:
            if p:
                state["total_media"] += 1
        new_id = await send_album(client, dst, msgs, dst_topic, state, cfg, paths)
        stats["media"] = state["total_media"]
        if new_id is None:
            stats["errors"] += 1
        else:
            state["total_sent"] += len(msgs)
            if cfg.get("copy_pinned") and any(getattr(m, "pinned", False) for m in msgs):
                await pin_message(client, dst, new_id)
    else:
        msg = anchor
        if paths:
            state["total_media"] += 1
            stats["media"] = state["total_media"]
        new_id = await send_one(client, dst, msg, dst_topic, state, cfg, paths)
        if new_id is None:
            if msg.media or (getattr(msg, "raw_text", None) or "").strip():
                stats["errors"] += 1
        else:
            state["total_sent"] += 1
            if cfg.get("copy_pinned") and getattr(msg, "pinned", False):
                await pin_message(client, dst, new_id)

    state["last_msg_id"] = max(state.get("last_msg_id", 0) or 0, msgs[-1].id)
    stats["sent"] = state["total_sent"]
    stats["topics"] = state["total_topics"]
    if progress and task_msg is not None:
        progress.advance(task_msg, len(msgs))
    _sync()

    delay = cfg_value(cfg, "delay_after_media" if had_media else "delay_between_msgs", 2.5 if had_media else 1.5)
    if delay > 0:
        await asyncio.sleep(delay)


async def _group_stream(source: AsyncIterator):
    album_buf: list = []
    current_gid: int | None = None
    async for msg in source:
        gid = getattr(msg, "grouped_id", None)
        if gid is None:
            if album_buf:
                yield album_buf if len(album_buf) > 1 else album_buf[0]
                album_buf, current_gid = [], None
            yield msg
        else:
            if current_gid is None or gid == current_gid:
                current_gid = gid
                album_buf.append(msg)
            else:
                yield album_buf if len(album_buf) > 1 else album_buf[0]
                album_buf, current_gid = [msg], gid
    if album_buf:
        yield album_buf if len(album_buf) > 1 else album_buf[0]


async def _download_for_item(client, item, cfg, sem):
    if cfg.get("dry_run"):
        if isinstance(item, list):
            return [bool(m.media) for m in item]
        return bool(item.media)
    if isinstance(item, list):
        async def dl(m):
            async with sem:
                return await download_msg_media(client, m, cfg)
        return await asyncio.gather(*[dl(m) for m in item])
    if not item.media:
        return None
    async with sem:
        return await download_msg_media(client, item, cfg)


def _normalize_input(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.lstrip("-").isdigit():
            try:
                return int(s)
            except ValueError:
                return s
        return s
    return value


def _cleanup_stale_tmp(cfg):
    try:
        tmp = temp_dir(cfg)
        for f in sorted(tmp.glob("*"), key=lambda f: f.stat().st_mtime)[:-10]:
            try:
                f.unlink()
            except Exception:
                pass
    except Exception:
        pass
