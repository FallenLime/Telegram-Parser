# 📡 TG Mirror — Telegram Channel Mirror

Complete mirroring of Telegram channels into your channel/group with automatic
creation of topics (Topics/Forum).

---

## 📁 Project Structure

```text
tg_parser/
├── main.py          # Entry point, authorization, main menu
├── mirror.py        # Orchestrator: connects reader and sender
├── reader.py        # Source reading: topics, messages, albums
├── sender.py        # Sending to destination: creating topics, forwarding media
├── config.py        # Configuration and synchronization state
├── ui.py            # Terminal interface (Rich)
├── requirements.txt # Dependencies
└── README.md        # This instruction
```

---

## ⚙️ Installation

### 1. Python 3.11+
```bash
python --version  # must be 3.11 or higher
```

### 2. Dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) .env
You can create a `.env` file next to `main.py` so API keys are not stored in `tg_mirror_config.json`:
```env
TG_API_ID=12345
TG_API_HASH=abcdef...
```

### 4. Telegram API keys (free, 2 minutes)
1. Open https://my.telegram.org
2. Log in with your phone number
3. Go to “API development tools”
4. Fill out the form (name and platform can be anything)
5. Copy **App api_id** and **App api_hash**

The program will ask for them on first launch and save them into `tg_mirror_config.json`.

---

## 🚀 Launch

```bash
python main.py
```

On first launch:
1. Enter API ID and API Hash
2. Enter your phone number (`+1XXXXXXXXXX`)
3. Enter the code from Telegram
4. If needed — enter your 2FA password

The session is saved in `tg_mirror_session.session`. Re-login is not required.

---

## 🎯 Preparing the Target Channel

For topics to work correctly, the target channel must be a **supergroup with “Topics” enabled**:

1. Create a group (or use an existing supergroup)
2. Open “Manage Group” → “Topics” → Enable
3. Assign the bot/account as administrator with permissions:
   - Send messages
   - Manage topics (Topics)
   - Pin messages (if needed)

> A regular channel also works — messages will go into the general feed without topics.

---

## 📖 Main Menu

```text
1 ▸  Start channel mirroring
2 ▸  My channels and groups
3 ▸  Settings
4 ▸  Synchronization history
5 ▸  Switch account
0 ▸  Exit
```

### Mirroring (Option 1)

1. Select the **source** from the list (or enter @username / ID manually)
2. Select the **destination** — your group/channel
3. Optionally specify a message ID range (or Enter = all)
4. The program automatically:
   - Reads all source topics
   - Creates the same topics in the destination
   - Sends messages into the correct topics in chronological order
   - Preserves albums (groups of photos) in one batch
   - Preserves reply chains, including inside topics
   - Pins pinned messages

---

## 🔄 Resume

If mirroring was interrupted (Ctrl+C, network error) — simply restart
with the same channels. The program will automatically continue from where it stopped.

Progress is stored in `sync_states/<src_id>_to_<dst_id>.json`.

---

## ⚙️ Settings

| Parameter | Description | Default |
|---|---|---|
| Copy photos | Download and forward photos | Yes |
| Copy videos | Download and forward videos | Yes |
| Copy documents | Download and forward files | Yes |
| Max file size | Skip files larger than N MB | 500 MB |
| Delay between messages | Anti-flood pause (seconds) | 1.5 |
| Delay after media | Pause after large files (seconds) | 2.5 |
| Delay when creating topics | Anti-flood pause when creating topics | 3.0 |
| Skip forwards | Do not copy forwarded messages | No |
| Pin messages | Pin pinned messages in destination | Yes |
| Add original link | Append t.me/... link at the end | No |
| Silent sending | No notifications for subscribers | Yes |
| Preserve reply chains | Restore replies to copied messages | Yes |
| Hide regular chats | Do not show regular groups/legacy chats in the list | Yes |
| Stealth mode | Do not catch updates or receive incoming events | Yes |
| Dry-run | Preview: count without actual sending | No |
| Parallel media downloading | How many files in an album to download simultaneously | 2 |
| Pipeline buffer | How many items to prepare ahead | 3 |
| Log to tg_mirror.log | RotatingFileHandler, 5 MB × 3 | Yes |

---

## 📦 What Gets Copied

- ✅ Text messages with formatting (**bold**, _italic_, `code`, ~~strikethrough~~, links)
- ✅ Photos
- ✅ Videos
- ✅ Documents and files
- ✅ Albums (multiple photos/videos in one message)
- ✅ Topics (Topics/Forum) — automatically created in destination
- ✅ Reply chains (reply threads), including inside topics
- ✅ Pinned messages (including pinned albums)
- ✅ Links and inline buttons (text links)
- ⏭️ Stickers / GIFs — sent as files (API limitation)
- ⏭️ Voice / video messages — as documents

---

## 🕵️ Stealth

The program does not “expose” your account to the source:
- **Does not increase views** (no `GetMessagesViewsRequest` calls)
- **Does not mark messages as read** (`telethon.iter_messages` does not do this)
- **Does not signal online / typing** (no `SetTyping`, no `updateOnline`)
- **Stealth mode** additionally disables `catch_up` and `receive_updates` on the client

For the source, everything looks like “this user is offline”.

---

## ⚡ Speed

- **Pipeline producer/consumer**: while message N is being sent, N+1 and N+2 are downloaded in the background (buffer `prefetch_count`).
- **Parallel downloading inside albums** via `asyncio.gather` (limited by `concurrent_downloads`).
- **Dry-run** before the actual run — see how much will be sent and whether there are access issues.

Typical delay values (1.5–3 sec) can be reduced in Settings, but be careful — overly
aggressive settings will trigger FloodWait.

---

## ❗ Important

- **Private channels**: copying works if you are a **member**
- **Forward Protection**: forwarding protection does not interfere — data is read directly through the MTProto API
- **FloodWait**: if Telegram imposes restrictions, the program automatically pauses and continues
- **Permissions in destination**: the account must be an administrator with topic management rights
- **Session file** (`*.session`) contains authorization — keep it secure

---

## 🐛 Common Problems

**`Could not find the input entity`** — channel not found. For private channels: make sure
you are a member.

**`ChatAdminRequiredError`** — insufficient permissions in the target group. Assign the account as administrator
with topic management rights.

**`Topics are not being created`** — make sure “Topics” are enabled in the target supergroup.

**`FloodWaitError`** — Telegram asks you to wait. The program pauses automatically.
If errors occur frequently, increase delays in Settings.
