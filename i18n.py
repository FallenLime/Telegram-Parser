"""
i18n.py — UI translations. Default language: English (en).
"""

from __future__ import annotations

SUPPORTED = ("en", "ru", "zh", "es", "de")

LANGUAGE_NAMES = {
    "en": "English",
    "ru": "Русский",
    "zh": "中文",
    "es": "Español",
    "de": "Deutsch",
}

_lang = "en"

# fmt: off
_STRINGS: dict[str, dict[str, str]] = {
    # ── App / banner ──
    "app_subtitle": {
        "en": "Telegram Channel Mirror  •  v3.6.1  •  Full channel mirroring",
        "ru": "Telegram Channel Mirror  •  v3.6  •  Полное зеркалирование с темами",
        "zh": "Telegram Channel Mirror  •  v3.6  •  完整论坛镜像",
        "es": "Telegram Channel Mirror  •  v3.6  •  Espejo completo con temas",
        "de": "Telegram Channel Mirror  •  v3.6  •  Vollständige Forum-Spiegelung",
    },
    # ── Main menu ──
    "menu_mirror": {
        "en": "▸  Start channel mirroring",
        "ru": "▸  Запустить зеркалирование канала",
        "zh": "▸  开始频道镜像",
        "es": "▸  Iniciar espejo del canal",
        "de": "▸  Kanal-Spiegelung starten",
    },
    "menu_channels": {
        "en": "▸  My channels & groups",
        "ru": "▸  Мои каналы и группы",
        "zh": "▸  我的频道和群组",
        "es": "▸  Mis canales y grupos",
        "de": "▸  Meine Kanäle & Gruppen",
    },
    "menu_settings": {
        "en": "▸  Settings",
        "ru": "▸  Настройки",
        "zh": "▸  设置",
        "es": "▸  Ajustes",
        "de": "▸  Einstellungen",
    },
    "menu_history": {
        "en": "▸  Sync history",
        "ru": "▸  История синхронизаций",
        "zh": "▸  同步历史",
        "es": "▸  Historial de sincronización",
        "de": "▸  Sync-Verlauf",
    },
    "menu_relogin": {
        "en": "▸  Switch account",
        "ru": "▸  Сменить аккаунт",
        "zh": "▸  切换账号",
        "es": "▸  Cambiar cuenta",
        "de": "▸  Konto wechseln",
    },
    "menu_exit": {
        "en": "▸  Exit",
        "ru": "▸  Выход",
        "zh": "▸  退出",
        "es": "▸  Salir",
        "de": "▸  Beenden",
    },
    "prompt_action": {
        "en": "Choose action",
        "ru": "Выберите действие",
        "zh": "选择操作",
        "es": "Elija una acción",
        "de": "Aktion wählen",
    },
    "press_enter": {
        "en": "Press Enter to continue",
        "ru": "Нажмите Enter, чтобы продолжить",
        "zh": "按 Enter 继续",
        "es": "Pulse Enter para continuar",
        "de": "Enter drücken zum Fortfahren",
    },
    "goodbye": {
        "en": "Goodbye! 👋",
        "ru": "До свидания! 👋",
        "zh": "再见！👋",
        "es": "¡Hasta luego! 👋",
        "de": "Auf Wiedersehen! 👋",
    },
    "exit_dim": {
        "en": "Exit.",
        "ru": "Выход.",
        "zh": "退出。",
        "es": "Salida.",
        "de": "Beenden.",
    },
    # ── Settings categories ──
    "settings_title": {
        "en": "Settings",
        "ru": "Настройки",
        "zh": "设置",
        "es": "Ajustes",
        "de": "Einstellungen",
    },
    "settings_pick_section": {
        "en": "Pick a section — then change a parameter",
        "ru": "Выберите раздел — затем параметр",
        "zh": "选择分类 — 然后修改参数",
        "es": "Elija sección — luego un parámetro",
        "de": "Bereich wählen — dann Parameter",
    },
    "settings_save_exit": {
        "en": "Save & exit",
        "ru": "Сохранить и выйти",
        "zh": "保存并退出",
        "es": "Guardar y salir",
        "de": "Speichern & beenden",
    },
    "cat_media": {"en": "Media", "ru": "Медиа", "zh": "媒体", "es": "Medios", "de": "Medien"},
    "cat_speed": {"en": "Speed", "ru": "Скорость", "zh": "速度", "es": "Velocidad", "de": "Geschwindigkeit"},
    "cat_mirror": {"en": "Mirroring", "ru": "Зеркалирование", "zh": "镜像", "es": "Espejo", "de": "Spiegelung"},
    "cat_experiment": {"en": "Experimental", "ru": "Эксперимент", "zh": "实验", "es": "Experimental", "de": "Experimentell"},
    "cat_language": {"en": "Language", "ru": "Язык", "zh": "语言", "es": "Idioma", "de": "Sprache"},
    "cat_other": {"en": "Other", "ru": "Прочее", "zh": "其他", "es": "Otros", "de": "Sonstiges"},
    "settings_section_prompt": {"en": "Section", "ru": "Раздел", "zh": "分类", "es": "Sección", "de": "Bereich"},
    "settings_param_prompt": {"en": "Parameter (0 — back)", "ru": "Параметр (0 — назад)", "zh": "参数 (0 — 返回)", "es": "Parámetro (0 — atrás)", "de": "Parameter (0 — zurück)"},
    "settings_back_cats": {"en": "← Back to sections", "ru": "← Назад к разделам", "zh": "← 返回分类", "es": "← Volver a secciones", "de": "← Zurück zu Bereichen"},
    "settings_saved": {"en": "Settings saved", "ru": "Настройки сохранены", "zh": "设置已保存", "es": "Ajustes guardados", "de": "Einstellungen gespeichert"},
    "lang_pick": {"en": "Choose language", "ru": "Выберите язык", "zh": "选择语言", "es": "Elija idioma", "de": "Sprache wählen"},
    "lang_current": {"en": "Current", "ru": "Текущий", "zh": "当前", "es": "Actual", "de": "Aktuell"},
    "invalid_value": {"en": "Invalid value", "ru": "Неверное значение", "zh": "无效值", "es": "Valor no válido", "de": "Ungültiger Wert"},
    # ── Setting labels (keys match config keys) ──
    "set_download_photos": {"en": "Copy photos", "ru": "Копировать фото", "zh": "复制照片", "es": "Copiar fotos", "de": "Fotos kopieren"},
    "set_download_videos": {"en": "Copy videos", "ru": "Копировать видео", "zh": "复制视频", "es": "Copiar vídeos", "de": "Videos kopieren"},
    "set_download_documents": {"en": "Copy documents", "ru": "Копировать документы", "zh": "复制文件", "es": "Copiar documentos", "de": "Dokumente kopieren"},
    "set_media_max_size_mb": {"en": "Max file size (MB)", "ru": "Макс. размер файла (МБ)", "zh": "最大文件 (MB)", "es": "Tamaño máx. (MB)", "de": "Max. Dateigröße (MB)"},
    "set_delay_between_msgs": {"en": "Delay between messages (s)", "ru": "Задержка между сообщениями (с)", "zh": "消息间隔 (秒)", "es": "Pausa entre mensajes (s)", "de": "Pause zwischen Nachrichten (s)"},
    "set_delay_after_media": {"en": "Delay after media (s)", "ru": "Задержка после медиа (с)", "zh": "媒体后延迟 (秒)", "es": "Pausa tras medios (s)", "de": "Pause nach Medien (s)"},
    "set_delay_between_topics": {"en": "Delay when creating topics (s)", "ru": "Задержка при создании тем (с)", "zh": "创建主题延迟 (秒)", "es": "Pausa al crear temas (s)", "de": "Pause beim Erstellen von Themen (s)"},
    "set_concurrent_downloads": {"en": "Parallel media downloads", "ru": "Параллельная закачка медиа", "zh": "并行下载媒体", "es": "Descargas paralelas", "de": "Parallele Medien-Downloads"},
    "set_prefetch_count": {"en": "Pipeline buffer size", "ru": "Буфер pipeline", "zh": "管道缓冲区", "es": "Tamaño del búfer", "de": "Pipeline-Puffer"},
    "set_copy_general_topic": {"en": "Copy General / casual chat", "ru": "Копировать General / обычный чат", "zh": "复制 General / 闲聊", "es": "Copiar General / chat casual", "de": "General / Casual-Chat kopieren"},
    "set_skip_forwards": {"en": "Skip forwards", "ru": "Пропускать пересылки", "zh": "跳过转发", "es": "Omitir reenvíos", "de": "Weiterleitungen überspringen"},
    "set_copy_pinned": {"en": "Pin messages", "ru": "Закреплять сообщения", "zh": "置顶消息", "es": "Fijar mensajes", "de": "Nachrichten anheften"},
    "set_preserve_replies": {"en": "Preserve reply chains", "ru": "Сохранять reply-цепочки", "zh": "保留回复链", "es": "Conservar respuestas", "de": "Antwortketten erhalten"},
    "set_add_source_link": {"en": "Add link to original", "ru": "Ссылка на оригинал", "zh": "添加原文链接", "es": "Enlace al original", "de": "Link zum Original"},
    "set_silent_send": {"en": "Silent send", "ru": "Тихая отправка", "zh": "静默发送", "es": "Envío silencioso", "de": "Stilles Senden"},
    "set_hide_regular_chats": {"en": "Hide casual chats in list", "ru": "Скрыть обычные чаты в списке", "zh": "列表中隐藏普通聊天", "es": "Ocultar chats casuales", "de": "Casual-Chats in Liste ausblenden"},
    "set_stealth_mode": {"en": "Stealth mode", "ru": "Скрытный режим", "zh": "隐身模式", "es": "Modo sigiloso", "de": "Stealth-Modus"},
    "set_dry_run": {"en": "Dry-run (no sending)", "ru": "Dry-run (без отправки)", "zh": "试运行 (不发送)", "es": "Dry-run (sin enviar)", "de": "Dry-run (kein Senden)"},
    "set_experimental_fast_mode": {"en": "Experimental Fast Mode ⚡", "ru": "Experimental Fast Mode ⚡", "zh": "Experimental Fast Mode ⚡", "es": "Experimental Fast Mode ⚡", "de": "Experimental Fast Mode ⚡"},
    "set_experimental_parallel_topics": {"en": "Experimental Topic Copy 📋", "ru": "Experimental Topic Copy 📋", "zh": "Experimental Topic Copy 📋", "es": "Experimental Topic Copy 📋", "de": "Experimental Topic Copy 📋"},
    "set_parallel_topic_workers": {"en": "Topic Copy workers", "ru": "Потоков Topic Copy", "zh": "Topic Copy 线程数", "es": "Workers Topic Copy", "de": "Topic-Copy-Worker"},
    "set_log_to_file": {"en": "Log to tg_mirror.log", "ru": "Лог в tg_mirror.log", "zh": "写入 tg_mirror.log", "es": "Log en tg_mirror.log", "de": "Log in tg_mirror.log"},
    "set_language": {"en": "Interface language", "ru": "Язык интерфейса", "zh": "界面语言", "es": "Idioma de la interfaz", "de": "Oberflächensprache"},
    # ── Warnings ──
    "warn_general_off": {
        "en": "General/casual chat will NOT be read — only named forum topics",
        "ru": "General/обычный чат не читается — только именованные темы",
        "zh": "不会读取 General/闲聊 — 仅命名主题",
        "es": "No se leerá General/chat casual — solo temas con nombre",
        "de": "General/Casual-Chat wird nicht gelesen — nur benannte Themen",
    },
    "warn_fast_mode": {
        "en": "Minimal delays — higher FloodWait risk",
        "ru": "Минимальные паузы — выше риск FloodWait",
        "zh": "最短延迟 — FloodWait 风险更高",
        "es": "Pausas mínimas — más riesgo de FloodWait",
        "de": "Minimale Pausen — höheres FloodWait-Risiko",
    },
    "warn_topic_copy": {
        "en": "Topics are created and copied in parallel (forum required)",
        "ru": "Темы создаются и копируются параллельно (нужен форум)",
        "zh": "主题将并行创建和复制 (需要论坛)",
        "es": "Temas en paralelo (requiere foro)",
        "de": "Themen parallel (Forum erforderlich)",
    },
    # ── Mirror / errors ──
    "err_source_not_found": {"en": "Source not found: {e}", "ru": "Источник не найден: {e}", "zh": "未找到来源: {e}", "es": "Origen no encontrado: {e}", "de": "Quelle nicht gefunden: {e}"},
    "err_dest_not_found": {"en": "Destination not found: {e}", "ru": "Цель не найдена: {e}", "zh": "未找到目标: {e}", "es": "Destino no encontrado: {e}", "de": "Ziel nicht gefunden: {e}"},
    "err_no_forum_topics": {
        "en": "No named topics to copy. Enable General or check the source.",
        "ru": "Нет именованных тем. Включите General или проверьте источник.",
        "zh": "没有可复制的命名主题。请启用 General 或检查来源。",
        "es": "No hay temas con nombre. Active General o revise el origen.",
        "de": "Keine benannten Themen. General aktivieren oder Quelle prüfen.",
    },
    "err_non_forum_general_off": {
        "en": "Source has no forum topics. Enable «Copy General» or pick a forum source.",
        "ru": "Источник без форума. Включите «General» или выберите форум.",
        "zh": "来源无论坛主题。请启用「复制 General」或选择论坛来源。",
        "es": "Origen sin foro. Active «General» o elija un foro.",
        "de": "Quelle ohne Forum. «General» aktivieren oder Forum wählen.",
    },
    "prep_mirror": {"en": "Mirror preparation", "ru": "Подготовка зеркалирования", "zh": "镜像准备", "es": "Preparación", "de": "Spiegel-Vorbereitung"},
    "prep_open_dashboard": {"en": "Opening progress panel…", "ru": "Открываю панель прогресса…", "zh": "正在打开进度面板…", "es": "Abriendo panel…", "de": "Fortschrittspanel wird geöffnet…"},
    "dash_mirror": {"en": "Mirroring", "ru": "Зеркалирование", "zh": "镜像中", "es": "Espejo", "de": "Spiegelung"},
    "dash_stats": {"en": "Statistics", "ru": "Статистика", "zh": "统计", "es": "Estadísticas", "de": "Statistik"},
    "dash_progress": {"en": "Progress", "ru": "Прогресс", "zh": "进度", "es": "Progreso", "de": "Fortschritt"},
    "dash_events": {"en": "Events", "ru": "События", "zh": "事件", "es": "Eventos", "de": "Ereignisse"},
    "dash_waiting": {"en": "Waiting for events…", "ru": "Ожидание событий…", "zh": "等待事件…", "es": "Esperando eventos…", "de": "Warte auf Ereignisse…"},
    "stat_sent": {"en": "Sent", "ru": "Отправлено", "zh": "已发送", "es": "Enviados", "de": "Gesendet"},
    "stat_media": {"en": "Media", "ru": "Медиа", "zh": "媒体", "es": "Medios", "de": "Medien"},
    "stat_topics": {"en": "Topics created", "ru": "Тем создано", "zh": "已创建主题", "es": "Temas creados", "de": "Themen erstellt"},
    "stat_skipped": {"en": "Skipped", "ru": "Пропущено", "zh": "已跳过", "es": "Omitidos", "de": "Übersprungen"},
    "stat_errors": {"en": "Errors", "ru": "Ошибок", "es": "Errores", "de": "Fehler", "zh": "错误"},
    "stat_last_id": {"en": "Last msg_id", "ru": "Последний msg_id", "zh": "最后 msg_id", "es": "Último msg_id", "de": "Letzte msg_id"},
    "stat_topic": {"en": "Current topic", "ru": "Текущая тема", "zh": "当前主题", "es": "Tema actual", "de": "Aktuelles Thema"},
    "stat_speed": {"en": "Speed", "ru": "Скорость", "zh": "速度", "es": "Velocidad", "de": "Geschwindigkeit"},
    "skip_casual": {"en": "casual chat", "ru": "обычный чат", "zh": "闲聊", "es": "chat casual", "de": "Casual-Chat"},
    "skip_forward": {"en": "forward", "ru": "пересылка", "zh": "转发", "es": "reenvío", "de": "Weiterleitung"},
    "topic_copy_start": {"en": "Topic Copy: {n} topics in parallel", "ru": "Topic Copy: {n} тем параллельно", "zh": "Topic Copy: {n} 个主题并行", "es": "Topic Copy: {n} temas en paralelo", "de": "Topic Copy: {n} Themen parallel"},
    "topics_ready": {"en": "Topics ready in destination: {n}", "ru": "Тем в цели: {n}", "zh": "目标中主题: {n}", "es": "Temas en destino: {n}", "de": "Themen im Ziel: {n}"},
    "topic_skip_invalid": {"en": "Skipped topic «{title}»: invalid top message", "ru": "Пропуск темы «{title}»: нет top_message", "zh": "跳过主题 «{title}»: 无效顶消息", "es": "Tema omitido «{title}»: sin top_message", "de": "Thema übersprungen «{title}»: kein top_message"},
    "topic_copy_failed": {"en": "Topic «{title}» failed: {e}", "ru": "Тема «{title}» ошибка: {e}", "zh": "主题 «{title}» 失败: {e}", "es": "Tema «{title}» error: {e}", "de": "Thema «{title}» Fehler: {e}"},
    "only_named_topics": {"en": "Only named topics — General is not read", "ru": "Только именованные темы — General не читается", "zh": "仅命名主题 — 不读取 General", "es": "Solo temas con nombre — General no se lee", "de": "Nur benannte Themen — General wird nicht gelesen"},
    "done_title": {"en": "Done", "ru": "Готово", "zh": "完成", "es": "Listo", "de": "Fertig"},
    "stat_source": {"en": "Source", "ru": "Источник", "zh": "来源", "es": "Origen", "de": "Quelle"},
    "stat_dest": {"en": "Destination", "ru": "Цель", "zh": "目标", "es": "Destino", "de": "Ziel"},
    "field_id": {"en": "ID", "ru": "ID", "zh": "ID", "es": "ID", "de": "ID"},
    "field_title": {"en": "Title", "ru": "Название", "zh": "名称", "es": "Título", "de": "Titel"},
    "field_username": {"en": "Username", "ru": "Username", "zh": "用户名", "es": "Usuario", "de": "Benutzername"},
    "field_type": {"en": "Type", "ru": "Тип", "zh": "类型", "es": "Tipo", "de": "Typ"},
    "field_participants": {"en": "Members", "ru": "Участников", "zh": "成员", "es": "Miembros", "de": "Mitglieder"},
    "field_forum": {"en": "Topics", "ru": "Темы", "zh": "主题", "es": "Temas", "de": "Themen"},
    "field_about": {"en": "About", "ru": "Описание", "zh": "简介", "es": "Descripción", "de": "Beschreibung"},
    "type_channel": {"en": "Channel", "ru": "Канал", "zh": "频道", "es": "Canal", "de": "Kanal"},
    "type_group": {"en": "Group", "ru": "Группа", "zh": "群组", "es": "Grupo", "de": "Gruppe"},
    "type_supergroup": {"en": "Supergroup", "ru": "Супергруппа", "zh": "超级群组", "es": "Supergrupo", "de": "Supergruppe"},
    "yes": {"en": "Yes", "ru": "Да", "zh": "是", "es": "Sí", "de": "Ja"},
    "no": {"en": "No", "ru": "Нет", "zh": "否", "es": "No", "de": "Nein"},
    "mirror_interrupted": {"en": "Mirroring interrupted. Progress saved.", "ru": "Зеркалирование прервано. Прогресс сохранён.", "zh": "镜像已中断。进度已保存。", "es": "Espejo interrumpido. Progreso guardado.", "de": "Spiegelung unterbrochen. Fortschritt gespeichert."},
    "warn_zero_sent": {
        "en": "No messages copied ({topics}/{total} topics had messages). Check settings or source access.",
        "ru": "Ничего не скопировано ({topics}/{total} тем с сообщениями). Проверьте настройки и доступ.",
        "zh": "未复制消息（{topics}/{total} 个主题有内容）。请检查设置和权限。",
        "es": "Nada copiado ({topics}/{total} temas con mensajes). Revise ajustes y acceso.",
        "de": "Keine Nachrichten kopiert ({topics}/{total} Themen mit Inhalt). Einstellungen prüfen.",
    },
    "mirror_complete": {
        "en": "Done — {sent} messages mirrored",
        "ru": "Готово — скопировано {sent} сообщений",
        "zh": "完成 — 已镜像 {sent} 条消息",
        "es": "Listo — {sent} mensajes copiados",
        "de": "Fertig — {sent} Nachrichten gespiegelt",
    },
    "unexpected_error": {"en": "Unexpected error: {e}", "ru": "Неожиданная ошибка: {e}", "zh": "意外错误: {e}", "es": "Error inesperado: {e}", "de": "Unerwarteter Fehler: {e}"},
    "read_error": {"en": "Read error: {e}", "ru": "Ошибка чтения: {e}", "zh": "读取错误: {e}", "es": "Error de lectura: {e}", "de": "Lesefehler: {e}"},
    "copying": {"en": "Copying", "ru": "Копирование", "zh": "复制中", "es": "Copiando", "de": "Kopieren"},
    "skipping": {"en": "Skipping", "ru": "Пропуск", "zh": "跳过", "es": "Omitiendo", "de": "Überspringe"},
}
# fmt: on

_SETTING_KEYS = {
    "download_photos", "download_videos", "download_documents", "media_max_size_mb",
    "delay_between_msgs", "delay_after_media", "delay_between_topics",
    "concurrent_downloads", "prefetch_count", "copy_general_topic", "skip_forwards",
    "copy_pinned", "preserve_replies", "add_source_link", "silent_send",
    "hide_regular_chats", "stealth_mode", "dry_run", "experimental_fast_mode",
    "experimental_parallel_topics", "parallel_topic_workers", "log_to_file", "language",
}


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in SUPPORTED else "en"


def get_language() -> str:
    return _lang


def t(key: str, **kwargs) -> str:
    block = _STRINGS.get(key, {})
    text = block.get(_lang) or block.get("en") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text


def setting_label(key: str) -> str:
    return t(f"set_{key}") if f"set_{key}" in _STRINGS else key
