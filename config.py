"""
config.py — конфигурация, состояние синхронизации, .env-загрузка,
настройка логирования.
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

CONFIG_PATH = Path("tg_mirror_config.json")
STATE_DIR   = Path("sync_states")
LOG_PATH    = Path("tg_mirror.log")

DEFAULT_CONFIG = {
    # Telegram API
    "api_id":               "",
    "api_hash":             "",
    "session_name":         "tg_mirror_session",

    # Медиа
    "download_photos":      True,
    "download_videos":      True,
    "download_documents":   True,
    "media_max_size_mb":    500,
    "media_temp_dir":       "tmp_media",

    # Скорость / антифлуд
    "delay_between_msgs":   1.5,        # секунд между сообщениями
    "delay_after_media":    2.5,        # секунд после тяжёлых медиа
    "delay_between_topics": 3.0,        # секунд при создании новой темы
    "batch_size":           50,
    "concurrent_downloads": 2,          # сколько items одновременно скачивать вперёд
    "prefetch_count":       3,          # размер буфера pipeline (готовых items)

    # Поведение
    "skip_forwards":        False,      # пропускать пересылки
    "copy_pinned":          True,       # закреплять сообщения в dst
    "add_source_link":      False,      # добавлять ссылку на оригинал
    "silent_send":          True,       # не уведомлять подписчиков при отправке
    "preserve_replies":     True,       # сохранять reply-цепочки
    "hide_regular_chats":   True,       # скрывать обычные чаты из списка диалогов
    "copy_general_topic":   True,       # копировать сообщения из темы General / общего чата
    "stealth_mode":         True,       # не маркировать прочитанным, без typing/онлайн
    "dry_run":              False,      # превью без отправки
    "experimental_fast_mode": False,    # минимальные задержки (риск FloodWait)
    "experimental_parallel_topics": False,  # параллельное создание и копирование тем
    "parallel_topic_workers": 3,        # сколько тем обрабатывать одновременно
    "language":               "en",     # en | ru | zh | es | de

    # Логирование
    "log_to_file":          True,
    "log_level":            "INFO",     # DEBUG | INFO | WARNING | ERROR
}


# ── .env loader (опционально) ────────────────────────────────────

def load_dotenv(path: Path = Path(".env")) -> dict:
    """Простой парсер .env без внешних зависимостей.
    Загружает переменные TG_API_ID/TG_API_HASH (с фоллбэком на API_ID/API_HASH)
    и возвращает то, что нашёл, в виде dict для merge с конфигом.
    """
    result: dict = {}
    if not path.exists():
        return result
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip("'").strip('"')
                os.environ.setdefault(key, val)
    except OSError:
        return result

    env_api_id   = os.environ.get("TG_API_ID")   or os.environ.get("API_ID")
    env_api_hash = os.environ.get("TG_API_HASH") or os.environ.get("API_HASH")
    if env_api_id and env_api_id.isdigit():
        result["api_id"] = env_api_id
    if env_api_hash:
        result["api_hash"] = env_api_hash
    return result


# ── Конфиг ────────────────────────────────────────────────────────

def load_config() -> dict:
    data: dict = DEFAULT_CONFIG.copy()

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                file_data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                file_data.setdefault(k, v)
            data = file_data
        except (json.JSONDecodeError, OSError):
            # Битый файл — используем дефолт, но не падаем
            pass

    # .env переопределяет api_id/api_hash, если они там заданы
    env_overrides = load_dotenv()
    data.update(env_overrides)
    return data


def save_config(cfg: dict) -> None:
    tmp = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    tmp.replace(CONFIG_PATH)


# ── Логирование ───────────────────────────────────────────────────

_logger_configured = False


def setup_logging(cfg: dict) -> logging.Logger:
    """Однократно настраивает логирование в файл (rotating)."""
    global _logger_configured
    logger = logging.getLogger("tg_mirror")
    if _logger_configured:
        return logger

    level_name = (cfg.get("log_level") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    logger.propagate = False  # не сорим в корневой логгер (Rich сам справляется)

    if cfg.get("log_to_file", True):
        try:
            handler = RotatingFileHandler(
                LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))
            logger.addHandler(handler)
        except OSError:
            # Не смогли открыть файл — продолжаем без файла
            pass

    _logger_configured = True
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("tg_mirror")


# Профиль задержек для Experimental Fast Mode
_FAST_MODE = {
    "delay_between_msgs":   0.12,
    "delay_after_media":    0.2,
    "delay_between_topics": 0.4,
    "prefetch_count":       8,
    "concurrent_downloads": 4,
    "parallel_topic_workers": 5,
}


def cfg_value(cfg: dict, key: str, default=None):
    """Значение из конфига с учётом Fast Mode (переопределяет только перечисленные ключи)."""
    if cfg.get("experimental_fast_mode") and key in _FAST_MODE:
        return _FAST_MODE[key]
    if default is not None:
        return cfg.get(key, default)
    return cfg.get(key)


# ── Состояние синхронизации ──────────────────────────────────────

def _state_path(src_id: int, dst_id: int) -> Path:
    STATE_DIR.mkdir(exist_ok=True)
    return STATE_DIR / f"{abs(src_id)}_to_{abs(dst_id)}.json"


def _default_state() -> dict:
    return {
        "last_msg_id":  0,
        "topic_map":    {},
        "msg_id_map":   {},
        "pinned_src":   [],
        "started_at":   datetime.now().isoformat(),
        "updated_at":   "",
        "total_sent":   0,
        "total_media":  0,
        "total_topics": 0,
        "topic_last_msg": {},
    }


def load_state(src_id: int, dst_id: int) -> dict:
    p = _state_path(src_id, dst_id)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return _default_state()
        defaults = _default_state()
        for k, v in defaults.items():
            data.setdefault(k, v)
        return data
    return _default_state()


_MSG_MAP_MAX = 10_000  # не раздуваем state-файл на длинных каналах


def _trim_msg_id_map(state: dict) -> None:
    """Оставляет только последние N записей reply-маппинга."""
    msg_map: dict = state.get("msg_id_map") or {}
    if len(msg_map) <= _MSG_MAP_MAX:
        return
    # ключи — id сообщений; сортируем численно, оставляем хвост
    try:
        items = sorted(msg_map.items(), key=lambda kv: int(kv[0]))
    except ValueError:
        items = list(msg_map.items())
    state["msg_id_map"] = dict(items[-_MSG_MAP_MAX:])


def save_state(src_id: int, dst_id: int, state: dict) -> None:
    _trim_msg_id_map(state)
    state["updated_at"] = datetime.now().isoformat()
    p = _state_path(src_id, dst_id)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(p)


def delete_state_file(filename: str) -> bool:
    """Удаляет файл состояния по имени (из STATE_DIR)."""
    p = STATE_DIR / filename
    if not p.exists() or p.parent.resolve() != STATE_DIR.resolve():
        return False
    try:
        p.unlink()
        return True
    except OSError:
        return False


def list_state_files() -> list[Path]:
    if not STATE_DIR.exists():
        return []
    return sorted(STATE_DIR.glob("*.json"))


def temp_dir(cfg: dict) -> Path:
    p = Path(cfg.get("media_temp_dir", "tmp_media"))
    p.mkdir(exist_ok=True)
    return p
