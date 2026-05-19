"""
ui.py — терминальный интерфейс на Rich.

Главное правило: каждая страница чистит экран и рисует себя с нуля.
Прогресс-бар transient — исчезает после завершения, не оставляя «хвост».

Пока активен Progress, все status-сообщения идут через progress.console.log(),
иначе в Windows CMD строки наслаиваются поверх progress-бара.
"""

import os
import sys
import time
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar

from rich.console import Console, Group
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import (
    Progress, BarColumn, TextColumn,
    TimeRemainingColumn, SpinnerColumn,
    MofNCompleteColumn, TimeElapsedColumn,
)
from rich.text import Text
from rich.rule import Rule
from rich.align import Align
from rich.panel import Panel
from rich.live import Live
from rich import box

import i18n

def _enable_windows_vt() -> None:
    """Включает ANSI/VT100 в консоли Windows — без этого Rich «ломает» вывод."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        for handle_id in (-11, -12):  # stdout, stderr
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


_enable_windows_vt()

console = Console(force_terminal=True, legacy_windows=False)

_active_progress: ContextVar = ContextVar("active_progress", default=None)
_active_dashboard: ContextVar = ContextVar("active_dashboard", default=None)

# ── Палитра ──────────────────────────────────────────────────────
BLUE    = "#5B8AF0"
PURPLE  = "#A78BFA"
GREEN   = "#4ADE80"
YELLOW  = "#FBBF24"
RED     = "#F87171"
MUTED   = "#6B7280"
WHITE   = "bold white"

BANNER = r"""
 ████████╗ ██████╗     ███╗   ███╗██╗██████╗ ██████╗  ██████╗ ██████╗ 
    ██╔══╝██╔════╝     ████╗ ████║██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
    ██║   ██║  ███╗    ██╔████╔██║██║██████╔╝██████╔╝██║   ██║██████╔╝
    ██║   ██║   ██║    ██║╚██╔╝██║██║██╔══██╗██╔══██╗██║   ██║██╔══██╗
    ██║   ╚██████╔╝    ██║ ╚═╝ ██║██║██║  ██║██║  ██║╚██████╔╝██║  ██║
    ╚═╝    ╚═════╝     ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
"""

def _field_labels() -> dict:
    return {
        "id": i18n.t("field_id"),
        "title": i18n.t("field_title"),
        "username": i18n.t("field_username"),
        "type": i18n.t("field_type"),
        "participants": i18n.t("field_participants"),
        "forum": i18n.t("field_forum"),
        "about": i18n.t("field_about"),
    }


# ── Базовые помощники ────────────────────────────────────────────

def clear():
    """Полная очистка терминала. Корректно работает и в Windows-консоли."""
    if sys.platform == "win32":
        os.system("cls")
    try:
        console.clear(home=True)
    except Exception:
        pass


@contextmanager
def progress_context(progress: Progress):
    """Привязывает Progress к status-выводу (ok/warn/err/…) на время зеркалирования."""
    token = _active_progress.set(progress)
    try:
        yield progress
    finally:
        _active_progress.reset(token)


def _status_print(markup: str) -> None:
    """Печать статуса: в dashboard / progress.log / обычный print."""
    dash = _active_dashboard.get()
    if dash is not None:
        dash.push_log(markup)
        return
    prog = _active_progress.get()
    if prog is not None:
        prog.console.log(markup, highlight=False)
    else:
        console.print(markup)


def print_banner():
    console.print(Align.center(Text(BANNER, style=f"bold {BLUE}")))
    console.print(Align.center(
        Text(i18n.t("app_subtitle"), style=f"italic {MUTED}")
    ))
    console.print(Rule(style=BLUE))


def screen(title: str | None = None):
    """Очищает экран, рисует баннер и опциональный заголовок раздела."""
    clear()
    print_banner()
    if title:
        section(title)


def section(title: str):
    console.print()
    console.print(Rule(f"[bold {BLUE}]{title}[/]", style=MUTED))


def ok(msg: str):    _status_print(f"  [bold {GREEN}]✓[/]  {msg}")
def warn(msg: str):  _status_print(f"  [bold {YELLOW}]⚠[/]  {msg}")
def err(msg: str):   _status_print(f"  [bold {RED}]✗[/]  {msg}")
def info(msg: str):  _status_print(f"  [bold {BLUE}]→[/]  {msg}")
def muted(msg: str): _status_print(f"     [{MUTED}]{msg}[/]")
def blank():
    if _active_progress.get() is None:
        console.print()


def wait_for_continue():
    """Единое нажатие Enter, чтобы не было разнобоя в стилях."""
    blank()
    try:
        Prompt.ask(f"  [{MUTED}]{i18n.t('press_enter')}[/]", default="", show_default=False)
    except EOFError:
        pass


# ── Главное меню ─────────────────────────────────────────────────

def main_menu() -> str:
    screen()
    blank()
    t = Table(show_header=False, box=box.ROUNDED, border_style=BLUE,
              padding=(0, 2), min_width=56)
    t.add_column("n", style=f"bold {PURPLE}", width=4)
    t.add_column("a", style="white")

    rows = [
        ("1", i18n.t("menu_mirror")),
        ("2", i18n.t("menu_channels")),
        ("3", i18n.t("menu_settings")),
        ("4", i18n.t("menu_history")),
        ("5", i18n.t("menu_relogin")),
        ("0", i18n.t("menu_exit")),
    ]
    for n, a in rows:
        t.add_row(n, a)

    console.print(Align.center(t))
    blank()
    return Prompt.ask(f"  [{BLUE}]{i18n.t('prompt_action')}[/]", choices=["0","1","2","3","4","5"])


# ── Выбор канала ─────────────────────────────────────────────────

def pick_channel(label: str, hint: str = "") -> str:
    screen(label)
    if hint:
        console.print(f"  [{MUTED}]{hint}[/]")
    return Prompt.ask(f"  [{BLUE}]@username / t.me/ссылка / ID[/]").strip()


def pick_from_list(channels: list[dict], label: str) -> str | None:
    """Показывает таблицу каналов, возвращает введённый пользователем идентификатор."""
    screen(label)
    if not channels:
        warn("Каналов не найдено (с учётом фильтра «обычные чаты» в настройках)")
        return None

    t = Table(box=box.SIMPLE_HEAVY, border_style=BLUE, min_width=72)
    t.add_column("#",     style=f"bold {PURPLE}", width=4)
    t.add_column("ID",    style=MUTED,            width=14)
    t.add_column("Название", style=WHITE,         min_width=28)
    t.add_column("Тип",   style=f"bold {BLUE}",   width=14)
    t.add_column("Участников", style=MUTED,       width=12)

    for i, ch in enumerate(channels, 1):
        t.add_row(
            str(i),
            str(ch["id"]),
            ch["title"],
            ch["type"],
            str(ch.get("participants_count", "?")),
        )
    console.print(t)
    blank()
    val = Prompt.ask(f"  [{BLUE}]Введите # из списка, @username или ID канала[/]").strip()
    if val.isdigit() and 1 <= int(val) <= len(channels):
        return str(channels[int(val) - 1]["id"])
    return val or None


def print_channels_table(channels: list[dict], *, redraw_screen: bool = True):
    """Таблица «Мои каналы и группы»."""
    if redraw_screen:
        screen("Мои каналы и группы")
    if not channels:
        warn("Ничего не найдено")
        return

    t = Table(box=box.SIMPLE_HEAVY, border_style=BLUE, min_width=76)
    t.add_column("ID",           style=MUTED,                width=14)
    t.add_column("Название",     style="bold white",         min_width=28)
    t.add_column("Тип",          style=f"bold {PURPLE}",     width=16)
    t.add_column("Темы",         style=GREEN,                width=6)
    t.add_column("Участников",   style=MUTED,                width=12)

    for ch in channels:
        t.add_row(
            str(ch["id"]),
            ch["title"],
            ch["type"],
            "✓" if ch.get("forum") else "",
            str(ch.get("participants_count", "?")),
        )
    console.print(t)


# ── Диапазон ─────────────────────────────────────────────────────

def ask_range() -> tuple[int | None, int | None]:
    section("Диапазон сообщений")
    console.print(f"  [{MUTED}]Оставьте пустым — скопируются ВСЕ сообщения (продолжение с места остановки).[/]")
    s = Prompt.ask(f"  [{BLUE}]ID с[/] (или Enter)", default="").strip()
    e = Prompt.ask(f"  [{BLUE}]ID по[/] (или Enter)", default="").strip()
    return (int(s) if s.isdigit() else None), (int(e) if e.isdigit() else None)


# ── Информация о канале ───────────────────────────────────────────

def print_channel_info(d: dict):
    t = Table(box=box.MINIMAL, show_header=False, border_style=MUTED, padding=(0,1))
    t.add_column("k", style=MUTED, width=22)
    t.add_column("v", style="white")
    for k, v in d.items():
        label = _field_labels().get(k, k)
        if isinstance(v, bool):
            v = i18n.t("yes") if v else i18n.t("no")
        t.add_row(label, str(v))
    console.print(t)


# ── Прогресс ─────────────────────────────────────────────────────

def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(style=f"bold {BLUE}"),
        TextColumn("[bold white]{task.description}"),
        BarColumn(bar_width=40, style=MUTED, complete_style=BLUE, finished_style=GREEN),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
        expand=True,
    )


# ── Панель зеркалирования (Live) ─────────────────────────────────

class MirrorDashboard:
    """Компактный экран прогресса: статистика + progress + последние события."""

    def __init__(
        self,
        src_info: dict,
        dst_info: dict,
        cfg: dict,
        *,
        resume_from: int = 0,
        topics_count: int = 0,
    ):
        self.src_info = src_info
        self.dst_info = dst_info
        self.cfg = cfg
        self.resume_from = resume_from
        self.topics_count = topics_count
        self.logs: deque[str] = deque(maxlen=7)
        self.stats: dict = {
            "sent": 0,
            "media": 0,
            "topics": 0,
            "errors": 0,
            "skipped": 0,
            "last_id": resume_from or "—",
            "current_topic": "—",
            "speed": 0.0,
        }
        self._started = time.monotonic()
        self._live: Live | None = None
        self.progress: Progress | None = None
        self.task_id = None
        self._skip_pending = 0
        self._skip_kind = ""

    def note_skip(self, count: int, last_msg_id: int, *, kind: str = "General") -> None:
        """Учитывает пакет пропущенных сообщений (без лишних перерисовок)."""
        self._skip_pending += count
        self._skip_kind = kind
        self.stats["skipped"] = self.stats.get("skipped", 0) + count
        self.stats["last_id"] = last_msg_id
        if self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                description=(
                    f"[yellow]Пропуск {kind}[/] … {self.stats['skipped']} "
                    f"(msg ≤ {last_msg_id})"
                ),
            )

    def flush_skip_status(self) -> None:
        if self._skip_pending > 0:
            self.push_log(
                f"  [{MUTED}]Пропущено ({self._skip_kind}): "
                f"+{self._skip_pending} сообщ.[/]"
            )
            self._skip_pending = 0
        self.update_stats()

    def push_log(self, markup: str) -> None:
        self.logs.append(markup)
        if self._live:
            self._live.update(self.render(), refresh=True)

    def update_stats(self, **kwargs) -> None:
        self.stats.update(kwargs)
        sent = int(self.stats.get("sent", 0) or 0)
        elapsed = max(time.monotonic() - self._started, 0.1)
        self.stats["speed"] = round(sent / elapsed, 2)
        if self._live:
            self._live.update(self.render(), refresh=True)

    def _info_table(self) -> Table:
        t = Table.grid(padding=(0, 2))
        t.add_column(style=MUTED)
        t.add_column(style="white")
        t.add_column(style=MUTED)
        t.add_column(style="white")
        fast = " [bold yellow]FAST[/]" if self.cfg.get("experimental_fast_mode") else ""
        dry = " [bold yellow]DRY-RUN[/]" if self.cfg.get("dry_run") else ""
        t.add_row(i18n.t("stat_source"), self.src_info.get("title", "?"), i18n.t("stat_dest"), self.dst_info.get("title", "?"))
        t.add_row(
            i18n.t("field_forum"), str(self.topics_count),
            "Mode", f"mirror{fast}{dry}",
        )
        if self.resume_from:
            t.add_row("msg_id", str(self.resume_from), "", "")
        if not self.cfg.get("copy_general_topic", True):
            t.add_row(
                "General", "[yellow]skip[/]",
                i18n.t("field_forum"), "[green]named only[/]",
            )
        return t

    def _stats_table(self) -> Table:
        s = self.stats
        t = Table(box=box.SIMPLE, border_style=MUTED, expand=True)
        t.add_column("—", style=MUTED)
        t.add_column("—", style=f"bold {BLUE}")
        t.add_row(i18n.t("stat_sent"), str(s.get("sent", 0)))
        t.add_row(i18n.t("stat_media"), str(s.get("media", 0)))
        t.add_row(i18n.t("stat_topics"), str(s.get("topics", 0)))
        t.add_row(i18n.t("stat_skipped"), str(s.get("skipped", 0)))
        t.add_row(i18n.t("stat_errors"), f"[{RED}]{s.get('errors', 0)}[/]")
        t.add_row(i18n.t("stat_last_id"), str(s.get("last_id", "—")))
        t.add_row(i18n.t("stat_topic"), str(s.get("current_topic", "—"))[:42])
        t.add_row(i18n.t("stat_speed"), f"~{s.get('speed', 0)} msg/s")
        return t

    def render(self) -> Group:
        parts = [
            Panel(self._info_table(), title=f"[bold]{i18n.t('dash_mirror')}[/]", border_style=BLUE),
            Panel(self._stats_table(), title=f"[bold]{i18n.t('dash_stats')}[/]", border_style=PURPLE),
        ]
        if self.progress:
            parts.append(Panel(self.progress, border_style=MUTED, title=f"[bold]{i18n.t('dash_progress')}[/]"))
        if self.logs:
            log_text = "\n".join(self.logs)
            parts.append(Panel(log_text, title=f"[bold]{i18n.t('dash_events')}[/]", border_style=MUTED))
        else:
            parts.append(Panel(f"[{MUTED}]{i18n.t('dash_waiting')}[/]", border_style=MUTED))
        return Group(*parts)

    @contextmanager
    def session(self):
        """Очищает экран и показывает только панель зеркалирования."""
        clear()
        print_banner()
        self.progress = make_progress()
        self.task_id = self.progress.add_task("Подготовка…", total=None)
        token_dash = _active_dashboard.set(self)
        self._live = Live(self.render(), console=console, refresh_per_second=4, transient=False)
        self._live.start()
        try:
            with progress_context(self.progress):
                yield self
        finally:
            _active_dashboard.reset(token_dash)
            self._live.stop()
            self._live = None


def mirror_prep_summary(
    src_info: dict, dst_info: dict, cfg: dict, *,
    topics: int, resume: int, general_ids: set | None = None,
    parallel: bool = False,
):
    """Краткая сводка перед стартом (один экран, без лишних строк)."""
    screen(i18n.t("prep_mirror"))
    t = Table(box=box.ROUNDED, border_style=BLUE, min_width=64)
    t.add_column("", style=MUTED, width=18)
    t.add_column("", style="white")
    t.add_row("Источник", f"{src_info['title']}  ({src_info['type']})")
    t.add_row("Цель", f"{dst_info['title']}  ({dst_info['type']})")
    t.add_row("Темы (форум)", "Да" if src_info.get("forum") else "Нет")
    if topics:
        t.add_row("Тем в источнике", str(topics))
    if resume:
        t.add_row("Продолжение", f"msg_id ≥ {resume}")
    if cfg.get("experimental_fast_mode"):
        t.add_row("Fast Mode", "[bold yellow]ВКЛ — возможен FloodWait[/]")
    if parallel:
        w = cfg.get("parallel_topic_workers", 3)
        t.add_row("Topic Copy", f"[bold purple]параллельно ({w} потоков)[/]")
    if not cfg.get("copy_general_topic", True) and src_info.get("forum"):
        named = max(0, topics - len(general_ids or {1}))
        t.add_row("General / болталка", "[yellow]пропуск[/]")
        t.add_row("Именованные темы", f"[green]~{named} будут скопированы[/]")
    if cfg.get("dry_run"):
        t.add_row("Dry-run", "[yellow]без отправки[/]")
    console.print(t)
    muted(i18n.t("prep_open_dashboard"))


# ── Settings (categories) ───────────────────────────────────────

_SETTINGS_CATEGORIES = [
    ("1", "cat_media", [
        ("download_photos", "bool"), ("download_videos", "bool"),
        ("download_documents", "bool"), ("media_max_size_mb", "int"),
    ]),
    ("2", "cat_speed", [
        ("delay_between_msgs", "float"), ("delay_after_media", "float"),
        ("delay_between_topics", "float"), ("concurrent_downloads", "int"),
        ("prefetch_count", "int"),
    ]),
    ("3", "cat_mirror", [
        ("copy_general_topic", "bool"), ("skip_forwards", "bool"),
        ("copy_pinned", "bool"), ("preserve_replies", "bool"),
        ("add_source_link", "bool"), ("silent_send", "bool"),
        ("hide_regular_chats", "bool"), ("stealth_mode", "bool"),
        ("dry_run", "bool"),
    ]),
    ("4", "cat_experiment", [
        ("experimental_fast_mode", "bool"),
        ("experimental_parallel_topics", "bool"),
        ("parallel_topic_workers", "int"),
    ]),
    ("5", "cat_other", [("log_to_file", "bool")]),
    ("6", "cat_language", []),
]


def _fmt_value(kind: str, val) -> str:
    if kind == "bool":
        return f"[{GREEN}]{i18n.t('yes')}[/]" if val else f"[{RED}]{i18n.t('no')}[/]"
    if kind == "lang":
        return f"[{BLUE}]{i18n.LANGUAGE_NAMES.get(val, val)}[/]"
    return f"[{BLUE}]{val}[/]"


def _edit_setting(cfg: dict, key: str, kind: str) -> None:
    label = i18n.setting_label(key)
    current = cfg.get(key)
    if kind == "bool":
        cfg[key] = Confirm.ask(f"  {label}?", default=bool(current))
        if key == "copy_general_topic" and not cfg[key]:
            warn(i18n.t("warn_general_off"))
        if key == "experimental_fast_mode" and cfg[key]:
            warn(i18n.t("warn_fast_mode"))
        if key == "experimental_parallel_topics" and cfg[key]:
            warn(i18n.t("warn_topic_copy"))
    elif kind == "int":
        try:
            cfg[key] = IntPrompt.ask(f"  {label}", default=int(current or 0))
        except (ValueError, TypeError):
            warn(i18n.t("invalid_value"))
    elif kind == "float":
        v = Prompt.ask(f"  {label}", default=str(current)).strip()
        try:
            cfg[key] = max(0.0, float(v))
        except ValueError:
            warn(i18n.t("invalid_value"))


def _language_picker(cfg: dict) -> None:
    screen(i18n.t("cat_language"))
    blank()
    codes = list(i18n.SUPPORTED)
    for i, code in enumerate(codes, 1):
        mark = f"  [{GREEN}]← {i18n.t('lang_current')}[/]" if cfg.get("language", "en") == code else ""
        console.print(f"  [{PURPLE}]{i}[/]  {i18n.LANGUAGE_NAMES[code]}{mark}")
    blank()
    choices = [str(i) for i in range(1, len(codes) + 1)] + ["0"]
    pick = Prompt.ask(f"  [{BLUE}]{i18n.t('lang_pick')}[/]", choices=choices, default="0")
    if pick != "0":
        code = codes[int(pick) - 1]
        cfg["language"] = code
        i18n.set_language(code)
        ok(f"{i18n.LANGUAGE_NAMES[code]}")


def _settings_category_table(cat_key: str, items: list, cfg: dict) -> None:
    t = Table(
        title=f"[bold {BLUE}]{i18n.t(cat_key)}[/]",
        box=box.SIMPLE_HEAVY, border_style=MUTED, min_width=72,
    )
    t.add_column("#", style=f"bold {PURPLE}", width=4)
    t.add_column("—", style="white")
    t.add_column("—", style="bold")
    for i, (key, kind) in enumerate(items, 1):
        t.add_row(str(i), i18n.setting_label(key), _fmt_value(kind, cfg.get(key)))
    t.add_row("0", i18n.t("settings_back_cats"), "")
    console.print(t)


def settings_menu(cfg: dict) -> dict:
    cat_choices = [c[0] for c in _SETTINGS_CATEGORIES] + ["0"]

    while True:
        screen(i18n.t("settings_title"))
        muted(i18n.t("settings_pick_section"))
        blank()

        menu = Table(box=box.ROUNDED, border_style=BLUE, min_width=52)
        menu.add_column("#", style=f"bold {PURPLE}", width=4)
        menu.add_column("—", style="white")
        for cid, cat_key, _ in _SETTINGS_CATEGORIES:
            menu.add_row(cid, i18n.t(cat_key))
        menu.add_row("0", i18n.t("settings_save_exit"))
        console.print(Align.center(menu))
        blank()

        pick = Prompt.ask(f"  [{BLUE}]{i18n.t('settings_section_prompt')}[/]", choices=cat_choices, default="0", show_choices=False)
        if pick == "0":
            break

        if pick == "6":
            _language_picker(cfg)
            continue

        cat_key, cat_items = next((k, items) for cid, k, items in _SETTINGS_CATEGORIES if cid == pick)

        while True:
            screen(f"{i18n.t('settings_title')} → {i18n.t(cat_key)}")
            _settings_category_table(cat_key, cat_items, cfg)
            blank()
            sub_choices = ["0"] + [str(i) for i in range(1, len(cat_items) + 1)]
            sub = Prompt.ask(f"  [{BLUE}]{i18n.t('settings_param_prompt')}[/]", choices=sub_choices, default="0", show_choices=False)
            if sub == "0":
                break
            key, kind = cat_items[int(sub) - 1]
            _edit_setting(cfg, key, kind)
            ok(f"{i18n.setting_label(key)} → {_fmt_value(kind, cfg.get(key))}")

    return cfg


# ── Итог ─────────────────────────────────────────────────────────

def print_summary(stats: dict):
    screen(i18n.t("done_title"))
    t = Table(box=box.ROUNDED, border_style=GREEN, min_width=50)
    t.add_column("Параметр", style=MUTED)
    t.add_column("Значение", style=f"bold {GREEN}")
    for k, v in stats.items():
        t.add_row(str(k), str(v))
    console.print(t)


# ── История синхронизаций ────────────────────────────────────────

def print_sync_history(states: list[dict]) -> int | None:
    """Печатает таблицу истории. Возвращает индекс выбранной записи
    для последующего удаления, либо None если пользователь не выбрал ничего."""
    screen("История синхронизаций")
    if not states:
        muted("Нет сохранённых синхронизаций")
        return None

    t = Table(box=box.SIMPLE_HEAVY, border_style=BLUE, min_width=84)
    t.add_column("#",         style=f"bold {PURPLE}", width=4)
    t.add_column("Файл",      style=MUTED,            width=30)
    t.add_column("Сообщений", style=f"bold {BLUE}",   width=12)
    t.add_column("Медиа",     style=PURPLE,           width=10)
    t.add_column("Тем",       style=PURPLE,           width=8)
    t.add_column("Обновлено", style=MUTED,            width=22)

    for i, s in enumerate(states, 1):
        t.add_row(
            str(i),
            s.get("file", ""),
            str(s.get("total_sent", 0)),
            str(s.get("total_media", 0)),
            str(s.get("total_topics", 0)),
            (s.get("updated_at", "") or "")[:19],
        )
    console.print(t)
    blank()

    choices = [""] + [str(i) for i in range(1, len(states) + 1)]
    val = Prompt.ask(
        f"  [{BLUE}]Введите #, чтобы удалить запись[/] (или Enter, чтобы вернуться)",
        choices=choices, default="", show_choices=False, show_default=False,
    ).strip()
    if val.isdigit():
        idx = int(val) - 1
        if 0 <= idx < len(states):
            if Confirm.ask(f"  Удалить «{states[idx].get('file','')}» ?", default=False):
                return idx
    return None
