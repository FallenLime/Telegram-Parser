"""
main.py — точка входа: авторизация, меню, запуск зеркалирования.
"""

import asyncio
import json
import sys
from pathlib import Path

from rich.prompt import Prompt, Confirm

from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError,
)

import ui
import i18n
from config import (
    load_config, save_config, setup_logging, get_logger,
    STATE_DIR, list_state_files, delete_state_file,
)
from reader import list_dialogs
from mirror import run_mirror


# ── Авторизация ──────────────────────────────────────────────────

async def ensure_auth(cfg: dict) -> TelegramClient | None:
    log = get_logger()
    api_id   = str(cfg.get("api_id",   "")).strip()
    api_hash = str(cfg.get("api_hash", "")).strip()

    if not api_id or not api_hash or not api_id.isdigit():
        ui.screen("Подключение к Telegram API")
        ui.console.print(f"""
  [{ui.MUTED}]Нужны API-ключи вашего аккаунта (бесплатно):
  1. Откройте [link=https://my.telegram.org]https://my.telegram.org[/link]
  2. Войдите своим номером телефона
  3. «API development tools» → создайте приложение
  4. Скопируйте App api_id и App api_hash

  Можно также положить их в .env рядом с main.py:
      TG_API_ID=12345
      TG_API_HASH=abcdef...[/]
""")
        while True:
            api_id   = Prompt.ask(f"  [{ui.BLUE}]API ID[/]").strip()
            api_hash = Prompt.ask(f"  [{ui.BLUE}]API Hash[/]").strip()
            if api_id.isdigit() and api_hash:
                break
            ui.err("API ID должен быть числом, API Hash непустой строкой. Попробуйте снова.")
        cfg["api_id"]   = api_id
        cfg["api_hash"] = api_hash
        save_config(cfg)

    stealth = bool(cfg.get("stealth_mode", True))
    client = TelegramClient(
        cfg.get("session_name", "tg_mirror_session"),
        int(api_id),
        api_hash,
        system_version="4.16.30-vxCUSTOM",
        device_model="Desktop",
        app_version="1.0",
        # В stealth-режиме не катчимся за апдейтами и не принимаем их в основной поток —
        # клиент остаётся пассивным «снаружи».
        catch_up=not stealth,
        receive_updates=not stealth,
    )

    ui.info("Подключение…")
    try:
        await client.connect()
    except Exception as e:
        ui.err(f"Не удалось подключиться: {e}")
        log.error("connect failed: %s", e)
        return None

    if not await client.is_user_authorized():
        ui.section("Вход в аккаунт")
        phone = Prompt.ask(f"  [{ui.BLUE}]Номер телефона[/] (+7XXXXXXXXXX)").strip()
        try:
            await client.send_code_request(phone)
            for _ in range(3):
                code = Prompt.ask(f"  [{ui.BLUE}]Код из Telegram[/]").strip()
                try:
                    await client.sign_in(phone, code)
                    break
                except PhoneCodeInvalidError:
                    ui.err("Неверный код, попробуйте снова.")
                except PhoneCodeExpiredError:
                    ui.err("Код устарел. Запрашиваю новый…")
                    await client.send_code_request(phone)
                except SessionPasswordNeededError:
                    pwd = Prompt.ask(f"  [{ui.BLUE}]Пароль 2FA[/]", password=True)
                    await client.sign_in(password=pwd)
                    break
            else:
                ui.err("Слишком много неверных попыток. Выход.")
                await client.disconnect()
                return None
        except FloodWaitError as e:
            ui.err(f"FloodWait при входе: подождите {e.seconds}с и попробуйте снова.")
            await client.disconnect()
            return None
        except Exception as e:
            ui.err(f"Ошибка входа: {e}")
            log.exception("auth flow error")
            await client.disconnect()
            return None

    me = await client.get_me()
    if me is None:
        ui.err("Не удалось получить информацию о пользователе.")
        await client.disconnect()
        return None
    ui.ok(f"Вошли как [bold]{me.first_name or ''} {me.last_name or ''}[/bold]  (@{me.username or '—'})")
    log.info("authorized as %s (@%s)", (me.first_name or "").strip(), me.username or "")
    return client


# ── Действия ─────────────────────────────────────────────────────

async def action_mirror(client: TelegramClient, cfg: dict):
    """Выбор источника, цели и запуск зеркалирования."""
    ui.screen("Запуск зеркалирования")
    ui.info("Загружаю список ваших каналов и групп…")
    dialogs = await list_dialogs(
        client,
        hide_regular_chats=bool(cfg.get("hide_regular_chats", True)),
    )

    if not dialogs:
        ui.warn("Каналов/групп не найдено.")
        if cfg.get("hide_regular_chats"):
            ui.muted("Подсказка: в Настройках выключите «Скрывать обычные чаты», если вы ожидали увидеть здесь группы общения.")
        ui.wait_for_continue()
        return

    # Источник
    src_input = ui.pick_from_list(dialogs, "Источник — канал для копирования")
    if not src_input:
        return

    # Цель
    dst_input = ui.pick_from_list(dialogs, "Цель — ваш канал/группа для записи")
    if not dst_input:
        return

    if str(src_input) == str(dst_input):
        ui.err("Источник и цель не могут совпадать!")
        ui.wait_for_continue()
        return

    min_id, max_id = ui.ask_range()

    # Превью-режим
    if cfg.get("dry_run"):
        ui.warn("DRY-RUN включён в настройках: ничего не будет отправлено в цель.")

    ui.blank()
    try:
        stats = await run_mirror(client, src_input, dst_input, cfg, min_id=min_id, max_id=max_id)
        ui.print_summary(stats)
    except RuntimeError as e:
        ui.err(str(e))
    except KeyboardInterrupt:
        ui.warn(i18n.t("mirror_interrupted"))
    except Exception as e:
        ui.err(i18n.t("unexpected_error", e=e))
        get_logger().exception("action_mirror unexpected: %s", e)


async def action_list_channels(client: TelegramClient, cfg: dict):
    ui.screen("Мои каналы и группы")
    ui.info("Загружаю каналы и группы…")
    # При просмотре всегда показываем всё (фильтр касается только pick_from_list)
    dialogs = await list_dialogs(client, hide_regular_chats=False)
    ui.print_channels_table(dialogs, redraw_screen=False)


async def action_history():
    """Показывает все сохранённые синхронизации + возможность удалить."""
    while True:
        states_info = []
        for p in list_state_files():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    s = json.load(f)
                s["file"] = p.name
                states_info.append(s)
            except Exception:
                pass

        delete_idx = ui.print_sync_history(states_info)
        if delete_idx is None:
            return
        target = states_info[delete_idx]
        if delete_state_file(target["file"]):
            ui.ok(f"Удалено: {target['file']}")
        else:
            ui.err(f"Не удалось удалить файл: {target['file']}")
        ui.wait_for_continue()


async def action_settings(cfg: dict) -> dict:
    cfg = ui.settings_menu(cfg)
    save_config(cfg)
    i18n.set_language(cfg.get("language", "en"))
    ui.ok(i18n.t("settings_saved"))
    ui.wait_for_continue()
    return cfg


async def action_relogin(cfg: dict) -> TelegramClient | None:
    ui.screen("Сменить аккаунт")
    session = Path(cfg.get("session_name", "tg_mirror_session") + ".session")
    if session.exists():
        if Confirm.ask("  Удалить текущую сессию и войти заново?", default=False):
            try:
                session.unlink()
                ui.ok("Сессия удалена")
            except OSError as e:
                ui.err(f"Не удалось удалить файл сессии: {e}")
    return await ensure_auth(cfg)


# ── Главный цикл ─────────────────────────────────────────────────

async def main():
    cfg = load_config()
    i18n.set_language(cfg.get("language", "en"))
    setup_logging(cfg)
    log = get_logger()
    log.info("starting tg_mirror v3.6.1")

    client = await ensure_auth(cfg)
    if not client:
        ui.err("Не удалось войти. Выход.")
        return

    try:
        while True:
            choice = ui.main_menu()

            if choice == "1":
                await action_mirror(client, cfg)
                ui.wait_for_continue()
            elif choice == "2":
                await action_list_channels(client, cfg)
                ui.wait_for_continue()
            elif choice == "3":
                cfg = await action_settings(cfg)
            elif choice == "4":
                await action_history()
            elif choice == "5":
                try:
                    await client.disconnect()
                except Exception:
                    pass
                client = await action_relogin(cfg)
                if not client:
                    ui.err("Авторизация не удалась. Выход.")
                    break
                ui.wait_for_continue()
            elif choice == "0":
                ui.blank()
                ui.info(i18n.t("goodbye"))
                break

    finally:
        try:
            if client and client.is_connected():
                await client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        ui.console.print(f"\n  [dim]{i18n.t('exit_dim')}[/dim]")
        sys.exit(0)
