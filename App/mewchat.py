#!/usr/bin/env python3
import asyncio
import base64
import os
import sys
import random
from collections import deque
from getpass import getpass
from typing import Optional
import re
import json
import pathlib
import mimetypes
import webbrowser
import shutil
import time
import tempfile
import gzip
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon import TelegramClient, errors
from telethon.tl.functions.contacts import GetContactsRequest
try:
    from colorama import init as colorama_init
    colorama_init()
except Exception:
    pass

COLOR_RED   = "\x1b[31m"
COLOR_GREEN = "\x1b[32m"
COLOR_DARK_BLUE = "\x1b[34m"
COLOR_CYAN       = "\x1b[36m"
COLOR_YELLOW     = "\x1b[33m"
COLOR_RESET = "\x1b[0m"
API_ID = None
API_HASH = None
CHAT_USERNAME = None
SESSION_NAME = "tg_fast_session"
CONFIG_FILE = SESSION_NAME + ".config"
MAX_HISTORY = 200
PBKDF2_ITERS = 200_000
SALT_LEN = 16
NONCE_LEN = 12
AES_KEY_LEN = 32
INCOMING_DISPLAY_NAME = "fudcrypter"
OUTGOING_DISPLAY_NAME = "morphingpayload"

class UserCancelled(Exception):
    pass

def safe_input(prompt=""):
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        print(f"{COLOR_RED}\nExiting...{COLOR_RESET}")
        raise UserCancelled()

def safe_input_loop(prompt: str) -> str | None:
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print(f"\n{COLOR_RED}Force exit by user (Ctrl+C){COLOR_RESET}")
        sys.exit(0)
    except EOFError:
        print(f"\n{COLOR_RED}Input stream closed. Exiting...{COLOR_RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{COLOR_RED}Unexpected input error: {e}{COLOR_RESET}")
        sys.exit(1)

def safe_getpass(prompt=""):
    try:
        return getpass(prompt)
    except (KeyboardInterrupt, EOFError):
        print(f"{COLOR_RED}\nExiting...{COLOR_RESET}")
        sys.exit(0)

def derive_key(passphrase: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_LEN,
        salt=salt,
        iterations=PBKDF2_ITERS,
    )
    return kdf.derive(passphrase)

def clear_local_chat_storage():
    global recent_messages
    recent_messages = deque(maxlen=MAX_HISTORY)
    render_view()

def encrypt_message(passphrase: bytes, plaintext: str) -> str:
    salt = os.urandom(SALT_LEN)
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_LEN)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    blob = salt + nonce + ct
    return base64.b64encode(blob).decode("ascii")

def decrypt_message(passphrase: bytes, token_b64: str) -> Optional[str]:
    try:
        blob = base64.b64decode(token_b64)
        if len(blob) < SALT_LEN + NONCE_LEN + 1:
            return None
        salt = blob[:SALT_LEN]
        nonce = blob[SALT_LEN:SALT_LEN+NONCE_LEN]
        ct = blob[SALT_LEN+NONCE_LEN:]
        key = derive_key(passphrase, salt)
        aesgcm = AESGCM(key)
        pt = aesgcm.decrypt(nonce, ct, None)
        return pt.decode("utf-8")
    except Exception:
        return None

recent_messages = deque(maxlen=MAX_HISTORY)
history_lock = asyncio.Lock()
media_lock = asyncio.Lock()
media_dir = pathlib.Path(os.path.join(os.path.dirname(__file__), "media_cache"))
media_dir.mkdir(parents=True, exist_ok=True)
media_index = 0
media_deque = deque()
finalized_media_ids = set()

async def tamper_recent_messages(n: int = 10):
    async with history_lock:
        if len(recent_messages) == 0:
            print(f"{COLOR_YELLOW}[no messages to tamper]{COLOR_RESET}")
            return
        count = min(n, len(recent_messages))
        for i in range(-count, 0):
            entry = recent_messages[i]
            token_b64 = entry.get('token')
            if not token_b64:
                continue
            try:
                blob = base64.b64decode(token_b64)
            except Exception:
                continue

            if len(blob) > 2 and random.random() < 0.7:
                idx = random.randrange(len(blob))
                mutated = bytearray(blob)
                mutated[idx] ^= 0xFF
                new_blob = bytes(mutated)
            else:
                idx = random.randrange(len(blob)+1)
                mutated = bytearray(blob)
                mutated[idx:idx] = os.urandom(1)
                new_blob = bytes(mutated)

            entry['token'] = base64.b64encode(new_blob).decode('ascii')
        render_view()
        print(f"{COLOR_YELLOW}[Tampered last {count} messages — decrypt will fail]{COLOR_RESET}")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def render_view():
    clear_screen()
    print(f"{COLOR_CYAN}CloakPulse FUD crypter | encrypted terminal view | Cheat The AirPort Security{COLOR_RESET}")
    print("-" * 70)
    with_history = list(recent_messages)[-20:]
    for m in with_history:
        display = m['token']
        if m.get('plaintext_temp') is not None:
            display = f"[decrypted] {m['plaintext_temp']}"

        who = m.get('from', '?')
        if who == INCOMING_DISPLAY_NAME:
            color = COLOR_RED
        elif who == OUTGOING_DISPLAY_NAME:
            color = COLOR_GREEN
        else:
            color = COLOR_RESET

        print(f"{color}[{m.get('id','-')}] {who}: {display}{COLOR_RESET}")

    print("-" * 70)
    print(
        f"{COLOR_CYAN}"
        'Paste your payloads by section. It will Split with the custom algorithm & create AES-encrypted blobs\n'
        'After it will produce a final FUD dropper using selected requirements.\n'
        'Decryption and dropping also via Colckpulse Advanced multy C2 channels by default.\n'
        'Some times it may take days or weeks based on the environment to deploy..be patient\n'
        'Any AV or detection mechanisms are triggered,sandboxed environment or debuggers are detected..?\n'
        'the Dropper will automatically suicide and remove all evidences using morphing payloads or its advanced mutation engine :\n'
        f"{COLOR_RESET}"
    )
    print(f'{COLOR_YELLOW} "your meww here"  -> To send - type your text or payload in double quotes and hit Enter {COLOR_RESET}')
    print(f'{COLOR_YELLOW} "c"               -> Clear payloads{COLOR_RESET}')
    print(f'{COLOR_RED} Ctrl + c          -> Exit{COLOR_RESET}')
    print()

async def perform_logout(client):
    try:
        if client and client.is_connected():
            await client.log_out()
            await client.disconnect()
            print(f"{COLOR_YELLOW}[Session logged out successfully]{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}Logout error: {e}{COLOR_RESET}")

    try:
        if os.path.exists(SESSION_NAME + ".session"):
            os.remove(SESSION_NAME + ".session")
            print(f"{COLOR_YELLOW}[Local session file removed]{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}Could not delete session file: {e}{COLOR_RESET}")

    print(f"{COLOR_GREEN}You will be asked to log in again with API id, API hash & Phone number next time.{COLOR_RESET}")
    sys.exit(0)

async def store_encrypted_message(who: str, plaintext: str, passphrase: bytes, msg_id='-'):
    token = encrypt_message(passphrase, plaintext)
    async with history_lock:
        recent_messages.append({'id': msg_id, 'from': who, 'token': token, 'plaintext_temp': None})
    render_view()

async def store_media_entry(who: str, display: str, msg_id='-', file_path: str = None, html_path: str = None, orig_name: str = None):
    async with history_lock:
        recent_messages.append({'id': msg_id, 'from': who, 'token': display, 'media': True, 'media_file': file_path, 'media_html': html_path, 'orig_name': orig_name})
    render_view()

def _create_media_html(media_id: str, media_path: pathlib.Path) -> pathlib.Path:
    ext = media_path.suffix.lower()
    html_name = media_dir / f"{media_id}.html"
    url = media_path.name
    body = ""
    ctype, _ = mimetypes.guess_type(str(media_path))

    if ext == ".tgs":
        try:
            with gzip.open(media_path, "rb") as gz:
                data = gz.read()
            try:
                json_text = data.decode("utf-8")
            except Exception:
                json_text = data.decode("latin-1")
            safe_json = json_text.replace('</', r'<\/')
            body = (
                '<div id="lottie_container"></div>'
                '<script src="https://cdnjs.cloudflare.com/ajax/libs/bodymovin/5.9.6/lottie.min.js"></script>'
                f"<script id=\"animationData\" type=\"application/json\">{safe_json}</script>"
                "<script>"
                "try{"
                "const json = JSON.parse(document.getElementById('animationData').textContent);"
                "lottie.loadAnimation({container: document.getElementById('lottie_container'), renderer:'svg', loop:true, autoplay:true, animationData: json, rendererSettings:{preserveAspectRatio:'xMidYMid meet'}});"
                "}catch(e){console.error(e);document.getElementById('lottie_container').innerText='[animation render failed]';}"
                "</script>"
            )
        except Exception:
            body = f"<a href=\"{url}\">Download {media_path.name}</a>"

    elif ctype and ctype.startswith("image"):
        body = f"<img src=\"{url}\" style=\"max-width:100%;height:auto;\">"
    elif ctype and ctype.startswith("video"):
        body = f"<video controls src=\"{url}\" style=\"max-width:100%;height:auto;\"></video>"
    elif ctype and ctype.startswith("audio"):
        body = f"<audio controls src=\"{url}\"></audio>"
    else:
        body = f"<a href=\"{url}\">Download {media_path.name}</a>"

    css = (
        "<style>html,body{height:100%;margin:0;background:#000;color:#fff;}"
        "#wrap{display:flex;align-items:center;justify-content:center;height:100vh;padding:8px;box-sizing:border-box;}"
        "#content{max-width:100%;max-height:100%;display:flex;align-items:center;justify-content:center;}"
        "img,video,#lottie_container, lottie-player{max-width:100%;max-height:100vh;object-fit:contain;}"
        "audio{position:fixed;bottom:12px;left:12px;}"
        "</style>"
    )

    html = (
        f"<!doctype html><html><head><meta charset=\"utf-8\"><title>{media_id}</title>" + css + "</head>"
        f"<body><div id=\"wrap\"><div id=\"content\">{body}</div></div></body></html>"
    )
    with open(html_name, "w", encoding="utf-8") as f:
        f.write(html)
    return html_name

async def _register_media_file(file_path: pathlib.Path):
    global media_index
    async with media_lock:
        media_index += 1
        idx = ((media_index - 1) % 10) + 1
        media_id = f"media{idx}"

        for item in list(media_deque):
            if item['id'] == media_id:
                try:
                    if item.get('file') and pathlib.Path(item['file']).exists():
                        pathlib.Path(item['file']).unlink()
                except Exception:
                    pass
                try:
                    if item.get('html') and pathlib.Path(item['html']).exists():
                        pathlib.Path(item['html']).unlink()
                except Exception:
                    pass
                try:
                    media_deque.remove(item)
                except ValueError:
                    pass
        orig_name = file_path.name
        dest = media_dir / f"{int(time.time())}_{orig_name}"
        try:
            shutil.move(str(file_path), str(dest))
        except Exception:
            shutil.copy2(str(file_path), str(dest))

        html_path = _create_media_html(media_id, dest)
        entry = {'id': media_id, 'file': str(dest), 'html': str(html_path), 'orig_name': orig_name}

        try:
            if len(media_deque) >= 10:
                old = media_deque.popleft()
                try:
                    if old.get('file') and pathlib.Path(old['file']).exists():
                        pathlib.Path(old['file']).unlink()
                except Exception:
                    pass
                try:
                    if old.get('html') and pathlib.Path(old['html']).exists():
                        pathlib.Path(old['html']).unlink()
                except Exception:
                    pass
        except Exception:
            pass

        media_deque.append(entry)
        return entry

def _open_media_in_browser(media_id: str):
    for item in media_deque:
        if item.get('id') == media_id:
            webbrowser.open(f"file:///{pathlib.Path(item['html']).resolve()}")
            return True
        if item.get('orig_name') == media_id:
            webbrowser.open(f"file:///{pathlib.Path(item['html']).resolve()}")
            return True
        if pathlib.Path(item.get('file', '')).name == media_id:
            webbrowser.open(f"file:///{pathlib.Path(item['html']).resolve()}")
            return True
    return False

async def handle_decrypt(passphrase: bytes):
    import sys, asyncio

    async with history_lock:
        n = min(5, len(recent_messages))
        if n == 0:
            print(f"{COLOR_YELLOW}[no messages to decrypt]{COLOR_RESET}")
            return
        for i in range(-n, 0):
            entry = recent_messages[i]
            if entry.get('media'):
                entry['plaintext_temp'] = None
                continue
            pt = decrypt_message(passphrase, entry['token'])
            entry['plaintext_temp'] = pt if pt is not None else "[decryption FAILED]"
    render_view()

    try:
        import msvcrt
        print(f"{COLOR_YELLOW}[press Enter to interrupt decrypted view & re-encrypt early]{COLOR_RESET}")
        start = asyncio.get_event_loop().time()
        interrupted = False
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b'\r', b'\n'):
                    interrupted = True
                    break
            if asyncio.get_event_loop().time() - start > 10:
                break
            await asyncio.sleep(0.1)
    except ImportError:
        import select
        r, _, _ = select.select([sys.stdin], [], [], 10)
        interrupted = bool(r)
        if interrupted:
            sys.stdin.readline()

    async with history_lock:
        for entry in recent_messages:
            entry['plaintext_temp'] = None
    render_view()
    print(f"{COLOR_GREEN}[re-encrypted]{COLOR_RESET}" if not interrupted else f"{COLOR_GREEN}[re-encrypted]{COLOR_RESET}")

async def handle_decrypt_extended(passphrase: bytes):
    import sys, asyncio

    async with history_lock:
        n = min(10, len(recent_messages))
        if n == 0:
            print(f"{COLOR_YELLOW}[no messages to decrypt]{COLOR_RESET}")
            return

        for i in range(-n, 0):
            entry = recent_messages[i]
            if entry.get('media'):
                entry['plaintext_temp'] = None
                continue
            pt = decrypt_message(passphrase, entry['token'])
            entry['plaintext_temp'] = pt if pt is not None else "[decryption FAILED]"

    render_view()

    print(f"{COLOR_YELLOW}[Expanded decryption mode] Showing last 10 messages decrypted for 15 seconds.{COLOR_RESET}")
    print(f"{COLOR_YELLOW}[Press Enter to re-encrypt early]{COLOR_RESET}")

    interrupted = False
    start = asyncio.get_event_loop().time()

    try:
        import msvcrt
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b'\r', b'\n'):
                    interrupted = True
                    break
            if asyncio.get_event_loop().time() - start > 15:
                break
            await asyncio.sleep(0.1)
    except ImportError:
        import select
        r, _, _ = select.select([sys.stdin], [], [], 15)
        interrupted = bool(r)
        if interrupted:
            sys.stdin.readline()

    async with history_lock:
        for entry in recent_messages:
            entry['plaintext_temp'] = None

    render_view()
    print(f"{COLOR_GREEN}[re-encrypted]{COLOR_RESET}")

async def fetch_last_messages(passphrase: bytes, client: TelegramClient, entity, limit=5):
    try:
        msgs = await client.get_messages(entity, limit=limit)
    except Exception as e:
        print(f"{COLOR_YELLOW}[fetch error]{COLOR_RESET} {e}")
        return
    msgs = list(reversed(msgs))

    for m in msgs:
        text = m.message or ""
        msg_id = getattr(m, "id", "-")

        if m.out:
            who = OUTGOING_DISPLAY_NAME
        else:
            who = INCOMING_DISPLAY_NAME

        if getattr(m, 'media', None) is not None:
            try:
                await download_and_register_media(m, client)
            except Exception as e:
                print(f"{COLOR_YELLOW}[media fetch failed]{COLOR_RESET} {e}")
            continue

        await store_encrypted_message(who, text, passphrase, msg_id=msg_id)

    print(f"[Fetched {len(msgs)} messages]")

async def fetch_last_messages2(passphrase: bytes, client: TelegramClient, entity, limit=10):
    try:
        msgs = await client.get_messages(entity, limit=limit)
    except Exception as e:
        print(f"{COLOR_YELLOW}[fetch error]{COLOR_RESET} {e}")
        return
    msgs = list(reversed(msgs))

    for m in msgs:
        text = m.message or ""
        msg_id = getattr(m, "id", "-")

        if m.out:
            who = OUTGOING_DISPLAY_NAME
        else:
            who = INCOMING_DISPLAY_NAME

        if getattr(m, 'media', None) is not None:
            try:
                await download_and_register_media(m, client)
            except Exception as e:
                print(f"{COLOR_YELLOW}[media fetch failed]{COLOR_RESET} {e}")
            continue

        await store_encrypted_message(who, text, passphrase, msg_id=msg_id)

    print(f"[Fetched {len(msgs)} messages]")       


async def download_and_register_media(msg, client: TelegramClient):
    msg_id = getattr(msg, 'id', '-')
    msg_id = str(msg_id)

    async with history_lock:
        recent_messages.append({'id': msg_id, 'from': INCOMING_DISPLAY_NAME, 'token': f"{INCOMING_DISPLAY_NAME} downloading 0%", 'media': True, 'media_file': None, 'media_html': None})
    render_view()

    tmp_dir = pathlib.Path(tempfile.gettempdir())
    base_name = f"msg_{msg_id}"
    tmp_file = tmp_dir / base_name

    def _progress(downloaded, total):
        try:
            pct = int(downloaded * 100 / total) if total else 0
        except Exception:
            pct = 0
        try:
            async def _update():
                async with media_lock:
                    if msg_id in finalized_media_ids:
                        return
                async with history_lock:
                    for entry in reversed(recent_messages):
                        if str(entry.get('id')) == msg_id and entry.get('media'):
                            entry['token'] = f"{INCOMING_DISPLAY_NAME} downloading {pct}%"
                            break
                render_view()
            asyncio.get_event_loop().create_task(_update())
        except Exception:
            pass

    try:
        out_path = await msg.download_media(file=str(tmp_file), progress_callback=_progress)
        if not out_path:
            async with history_lock:
                for entry in reversed(recent_messages):
                    if entry.get('id') == msg_id and entry.get('media'):
                        entry['token'] = f"{INCOMING_DISPLAY_NAME} [media download failed]"
                        break
            render_view()
            return

        entry = await _register_media_file(pathlib.Path(out_path))

        async with history_lock:
            for e in reversed(recent_messages):
                if str(e.get('id')) == msg_id and e.get('media'):
                    e['token'] = f"{INCOMING_DISPLAY_NAME} downloading 100% {entry['id']}"
                    e['media_file'] = entry['file']
                    e['orig_name'] = entry.get('orig_name')
                    e['media_html'] = entry['html']
                    break
        async with media_lock:
            finalized_media_ids.add(msg_id)
        render_view()
    except Exception as ex:
        async with history_lock:
            for entry in reversed(recent_messages):
                if str(entry.get('id')) == msg_id and entry.get('media'):
                    entry['token'] = f"{INCOMING_DISPLAY_NAME} [media download error]"
                    break
        render_view()
        raise

async def interactive(passphrase: bytes, client: TelegramClient):
    global CHAT_USERNAME

    if not await client.is_user_authorized():
        print(f"{COLOR_RED}[Session found but not authorized! rebuilding session]{COLOR_RESET}")
        await client.disconnect()
        os.remove(SESSION_NAME + ".session")

        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()

        phone = safe_input(f"{COLOR_DARK_BLUE}Enter Telegram number for login (e.g. +919876543210){COLOR_RESET}: ").strip()
        await client.send_code_request(phone)
        code = safe_input(f"{COLOR_DARK_BLUE}Enter the code you received{COLOR_RESET}: ").strip()
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            pw = safe_getpass(f"{COLOR_RED}Two-step password{COLOR_RESET}: ")
            await client.sign_in(password=pw)

        print(f"{COLOR_GREEN}[Login success | session saved locally]{COLOR_RESET}")
    else:
        print(f"{COLOR_YELLOW}[Session authorized | continuing normally]{COLOR_RESET}")

    entity = await client.get_entity(CHAT_USERNAME)
    print(f"{COLOR_YELLOW}Connected to chat {CHAT_USERNAME} (display names masked).{COLOR_RESET}")

    @client.on(events.NewMessage(chats=entity))
    async def on_new(ev):
        if ev.message and getattr(ev.message, 'media', None) is not None:
            try:
                asyncio.create_task(download_and_register_media(ev.message, client))
            except Exception:
                await store_media_entry(INCOMING_DISPLAY_NAME, f"{INCOMING_DISPLAY_NAME} [media incoming]", msg_id=getattr(ev.message, "id", "-"))
            return

        text = ev.message.text if ev.message and ev.message.text else ""
        await store_encrypted_message(INCOMING_DISPLAY_NAME, text, passphrase, msg_id=getattr(ev.message, "id", "-"))

    await client.start()
    render_view()

    loop = asyncio.get_event_loop()

    def blocking_input(prompt="> "):
        try:
            return input(prompt)
        except EOFError:
            return ""

    try:
        while True:
            try:
                cmd = await loop.run_in_executor(None, blocking_input, f"{COLOR_GREEN}[re-encrypted]\n{COLOR_RESET}> ")
            except KeyboardInterrupt:
                print(f"{COLOR_RED}\nKeyboardInterrupt detected ! exiting program.{COLOR_RESET}")
                sys.exit(0)

            if cmd is None:
                continue
            cmd = cmd.strip()
            if not cmd:
                continue

            if cmd.lower() in ("q", "quit", "exit"):
                print(f"{COLOR_YELLOW}Exiting chat and returning to target selection...{COLOR_RESET}\n")
                return
            
            if cmd.lower() == "c":
                clear_local_chat_storage()
                print(f"{COLOR_YELLOW}cleared... (local view).{COLOR_RESET}")
                continue

            if cmd.lower() == "t":
                await tamper_recent_messages(n=10)
                continue

            if cmd.lower() == "d":
                await handle_decrypt(passphrase)
                continue

            if cmd.lower() == "dd":
                await handle_decrypt_extended(passphrase)
                continue

            if cmd.lower() == "f":
                try:
                    clear_local_chat_storage()
                    await fetch_last_messages(passphrase, client, entity, limit=5)
                except Exception as e:
                    print(f"{COLOR_YELLOW}[fetch failed]{COLOR_RESET} {e}")
                continue

            if cmd.lower() == "ff":
                try:
                    clear_local_chat_storage()
                    await fetch_last_messages2(passphrase, client, entity, limit=10)
                except Exception as e:
                    print(f"{COLOR_YELLOW}[fetch failed]{COLOR_RESET} {e}")
                continue

            if cmd.lower() == "l":
                confirm = safe_input_loop(f"{COLOR_RED}Logout and delete session? (y/N){COLOR_RESET}: ")
                if confirm and confirm.strip().lower() == "y":
                    await perform_logout(client)
                else:
                    print(f"{COLOR_YELLOW}[Logout cancelled]{COLOR_RESET}")
                continue

            m = re.match(r'^"(.+)"\s*$', cmd, flags=re.DOTALL)
            if m:
                plaintext = m.group(1)
                try:
                    sent = await client.send_message(entity, plaintext)
                    await store_encrypted_message(OUTGOING_DISPLAY_NAME, plaintext, passphrase, msg_id=getattr(sent, "id", "-"))
                except Exception as e:
                    print(f"{COLOR_RED}[send failed] {e}{COLOR_RESET}")
                continue

            if cmd.lower().startswith('v '):
                parts = cmd.split()
                if len(parts) >= 2:
                    media_id = parts[1].strip()
                    if _open_media_in_browser(media_id):
                        print(f"{COLOR_YELLOW}Opening {media_id} in browser...{COLOR_RESET}")
                    else:
                        print(f"{COLOR_YELLOW}Media id {media_id} not found.{COLOR_RESET}")
                    continue

            print(f"{COLOR_YELLOW}Unknown command. Usage examples{COLOR_RESET} :")
            print(' "hello there"')
            print('  c   clear payloads')
            print(f'{COLOR_RED}  Ctrl + c   exit{COLOR_RESET}')

    finally:
        pass

async def ensure_login():
    api_id = 0
    api_hash = ""

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                api_id = int(data.get("api_id", 0))
                api_hash = data.get("api_hash", "")
        except Exception:
            api_id = 0
            api_hash = ""

    if os.path.exists(SESSION_NAME + ".session"):
        client = TelegramClient(SESSION_NAME, api_id, api_hash)
        await client.connect()

        if not client.is_connected():
            await client.connect()

        try:
            if await client.is_user_authorized():
                me = await client.get_me()
                print(f"[{COLOR_GREEN}Session active as{COLOR_RESET}] @{me.username or me.first_name}")
                return client, api_id, api_hash
            else:
                print(f"{COLOR_RED}[Session present but not authorized]{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_RED}[Session check failed: {e}]{COLOR_RESET}")

        try:
            await client.disconnect()
        except Exception:
            pass

        try:
            client.session.delete()
        except Exception:
            pass

        try:
            os.remove(SESSION_NAME + ".session")
            print(f"{COLOR_YELLOW}[Old session removed — starting re-login]{COLOR_RESET}")
        except FileNotFoundError:
            pass
        except PermissionError:
            print(f"{COLOR_YELLOW}[Session file busy, retrying removal]{COLOR_RESET}")
            import time
            time.sleep(1)
            try:
                os.remove(SESSION_NAME + ".session")
            except Exception as e:
                print(f"{COLOR_RED}[Failed to remove session file: {e}]{COLOR_RESET}")

    print(f"{COLOR_DARK_BLUE}[First time setup | Telegram API login required]{COLOR_RESET}")
    try:
        while True:
            api_id_in = safe_input(f"{COLOR_DARK_BLUE}Enter your Telegram API ID{COLOR_RESET}: ").strip()
            if api_id_in.isdigit():
                api_id = int(api_id_in)
                break
            print(f"{COLOR_RED}Invalid API ID. Enter numbers only{COLOR_RESET}.")

        while True:
            api_hash = safe_input(f"{COLOR_DARK_BLUE}Enter your Telegram API HASH{COLOR_RESET}: ").strip()
            if len(api_hash) >= 10:
                break
            print(f"{COLOR_RED}API HASH looks too short, try again{COLOR_RESET}.")

        while True:
            phone = safe_input(f"{COLOR_DARK_BLUE}Enter your phone number (e.g. +919876543210){COLOR_RESET}: ").strip()
            if phone.startswith("+") and phone[1:].isdigit():
                break
            print(f"{COLOR_RED}Invalid phone format. Must start with + and contain digits{COLOR_RESET}.")
    except UserCancelled:
        print(f"{COLOR_RED}\nExiting setup...{COLOR_RESET}")
        sys.exit(0)

    client = TelegramClient(SESSION_NAME, api_id, api_hash)
    await client.connect()

    for attempt in range(3):
        try:
            await client.send_code_request(phone)
            code = safe_input(f"{COLOR_YELLOW}Enter the login code{COLOR_RESET}: ").strip()
            await client.sign_in(phone=phone, code=code)
            if await client.is_user_authorized():
                break
        except errors.SessionPasswordNeededError:
            pw = safe_getpass(f"{COLOR_RED}Two-step verification password{COLOR_RESET}: ").strip()
            await client.sign_in(password=pw)
            break
        except Exception as e:
            print(f"{COLOR_RED}Login attempt failed:{COLOR_RESET} {e}")

    if not await client.is_user_authorized():
        print(f"{COLOR_RED}Login failed. Restarting setup...{COLOR_RESET}")
        return await ensure_login()

    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"api_id": api_id, "api_hash": api_hash}, f)
    except Exception as e:
        print(f"{COLOR_YELLOW}[Warning] Failed to write config: {e}{COLOR_RESET}")

    me = await client.get_me()
    print(f"{COLOR_GREEN}[Login successful | Logged in as{COLOR_RESET}] @{me.username or me.first_name}")
    return client, api_id, api_hash

async def main():
    print(f"{COLOR_CYAN}CloakPulseMorphingFUD | (local display) client{COLOR_RESET}")

    global CHAT_USERNAME
    client = None
    API_ID = None
    API_HASH = None

    async def ensure_connected():
        nonlocal client, API_ID, API_HASH
        if client is None or not client.is_connected():
            print(f"{COLOR_YELLOW}[Reconnecting Telegram client...]{COLOR_RESET}")
            try:
                client, API_ID, API_HASH = await ensure_login()
                if not client.is_connected():
                    await client.connect()
            except Exception as e:
                print(f"{COLOR_RED}[Reconnect failed]{COLOR_RESET} {e}")
                await asyncio.sleep(2)
                return await ensure_connected()
        return client

    client, API_ID, API_HASH = await ensure_login()

    try:
        while True:
            CHAT_USERNAME = None
            while True:
                print(f"{COLOR_YELLOW}\n[Target Selection Mode]{COLOR_RESET}")
                print("Enter one of:")
                print(f"{COLOR_CYAN}  @username1234      → search globally by username{COLOR_RESET}")
                print(f"{COLOR_CYAN}  +919876543210      → search by contact phone number{COLOR_RESET}")
                print(f"{COLOR_CYAN}  name               → search your existing chats by name{COLOR_RESET}")
                print(f"{COLOR_RED}  l                  → logout,delete session & Exit\n{COLOR_RESET}")

                user_input = safe_input_loop(f"{COLOR_YELLOW}Enter target (username / number / name){COLOR_RESET}: ")
                if user_input and user_input.strip().lower() == "l":
                    confirm = safe_input_loop(f"{COLOR_RED}Logout and delete session? (y/N){COLOR_RESET}: ")
                    if confirm and confirm.strip().lower() == "y":
                        await perform_logout(client)
                    else:
                        print(f"{COLOR_YELLOW}[Logout cancelled]{COLOR_RESET}")
                    continue

                if user_input is None:
                    print(f"{COLOR_RED}\nExiting...{COLOR_RESET}")
                    return
                user_input = user_input.strip()
                if not user_input:
                    continue

                if user_input.lower() == "b":
                    print(f"{COLOR_YELLOW}Already at top selection.{COLOR_RESET}")
                    continue

                await ensure_connected()

                if user_input.startswith("@"):
                    try:
                        entity = await client.get_entity(user_input)
                    except Exception:
                        print(f"{COLOR_RED}User not found. Try again.{COLOR_RESET}")
                        continue

                    print(f"{COLOR_DARK_BLUE}Found user{COLOR_RESET}: {entity.first_name or ''} {entity.last_name or ''} ({entity.username})")
                    confirm = safe_input_loop(f"{COLOR_YELLOW}Press Enter to confirm, or 'b' to cancel{COLOR_RESET}: ")
                    if confirm is None:
                        print(f"{COLOR_RED}\nExiting...{COLOR_RESET}")
                        return
                    if confirm.lower() == "b":
                        print(f"{COLOR_YELLOW}Cancelled. Returning to target selection...{COLOR_RESET}")
                        continue
                    if confirm.strip() != "":
                        print(f"{COLOR_YELLOW}Invalid input. Just press Enter to confirm.{COLOR_RESET}")
                        continue

                    CHAT_USERNAME = entity.username or getattr(entity, "id", None)
                    if isinstance(CHAT_USERNAME, str) and CHAT_USERNAME.startswith("@"):
                        CHAT_USERNAME = CHAT_USERNAME[1:]
                    break

                elif user_input.startswith("+"):
                    try:
                        result = await client(GetContactsRequest(hash=0))
                        users = getattr(result, "users", []) or []
                    except Exception as e:
                        print(f"{COLOR_RED}Contacts lookup failed: {e}{COLOR_RESET}")
                        continue

                    def norm(s): return re.sub(r"\D", "", str(s or ""))
                    target = norm(user_input)
                    match = None
                    for u in users:
                        phone = getattr(u, "phone", None)
                        if phone and target.endswith(norm(phone)):
                            match = u
                            break

                    if not match:
                        try:
                            ent = await client.get_entity(user_input)
                            match = ent
                        except Exception:
                            match = None

                    if not match:
                        print(f"{COLOR_YELLOW}No matching contact or global user found. Try again.{COLOR_RESET}")
                        continue

                    display_name = (getattr(match, "first_name", "") or "") + " " + (getattr(match, "last_name", "") or "")
                    display_name = display_name.strip() or getattr(match, "username", "") or str(getattr(match, "id", ""))
                    phone_display = getattr(match, "phone", "unknown")
                    print(f"{COLOR_DARK_BLUE}Found contact{COLOR_RESET}: {display_name} ({phone_display})")

                    confirm = safe_input_loop(f"{COLOR_YELLOW}Press Enter to confirm, or type 'b'and hit Enter to cancel{COLOR_RESET}: ")
                    if confirm is None:
                        print(f"{COLOR_RED}\nExiting...{COLOR_RESET}")
                        return
                    if confirm.lower() == "b":
                        print(f"{COLOR_YELLOW}Cancelled. Returning to target selection Menu...{COLOR_RESET}")
                        continue
                    if confirm.strip() != "":
                        print(f"{COLOR_YELLOW}Invalid input. Just press Enter to confirm.{COLOR_RESET}")
                        continue

                    CHAT_USERNAME = getattr(match, "username", None) or getattr(match, "id", None)
                    if isinstance(CHAT_USERNAME, str) and CHAT_USERNAME.startswith("@"):
                        CHAT_USERNAME = CHAT_USERNAME[1:]
                    break

                else:
                    try:
                        dialogs = await client.get_dialogs()
                    except Exception as e:
                        print(f"{COLOR_RED}Could not fetch dialogs: {e}{COLOR_RESET}")
                        continue

                    matches = [d for d in dialogs if user_input.lower() in (d.name or "").lower()]
                    if not matches:
                        print(f"{COLOR_YELLOW}No matching chats found. Try again.{COLOR_RESET}")
                        continue

                    print(f"{COLOR_YELLOW}\nMatching chats{COLOR_RESET}:")
                    for i, d in enumerate(matches, start=1):
                        print(f" {i}. {d.name}")

                    while True:
                        pick = safe_input_loop(f"{COLOR_YELLOW}\nType number to pick chat or Type 'b' and hit Enter to go back{COLOR_RESET}: ")
                        if pick is None:
                            print(f"{COLOR_RED}\nExiting...{COLOR_RESET}")
                            return
                        pick = pick.strip()
                        if pick.lower() == "b":
                            print(f"{COLOR_YELLOW}Returning to target selection Menu...{COLOR_RESET}")
                            break

                        if not pick.isdigit() or not (1 <= int(pick) <= len(matches)):
                            print(f"{COLOR_YELLOW}Invalid selection. Try again (pick a number from the list or 'b').{COLOR_RESET}")
                            continue

                        sel = matches[int(pick) - 1]
                        CHAT_USERNAME = getattr(getattr(sel, "entity", None), "id", None) or getattr(sel, "id", None) or getattr(sel, "name", None)
                        break 

                    if not CHAT_USERNAME:
                        continue
                    break

            if not CHAT_USERNAME:
                print(f"{COLOR_RED}No chat selected  returning to target selection Menu.{COLOR_RESET}")
                continue
            print(f"{COLOR_DARK_BLUE}Selected chat: {CHAT_USERNAME}{COLOR_RESET}")
            passphrase = safe_getpass(f"{COLOR_RED}Enter a local passphrase (used to derive keys.Type some random words){COLOR_RESET}: ").strip()
            if not passphrase:
                print(f"{COLOR_RED}Passphrase required...{COLOR_RESET}")
                continue

            passphrase_bytes = passphrase.encode("utf-8")
            try:
                await ensure_connected()
                await interactive(passphrase_bytes, client)
            except KeyboardInterrupt:
                print(f"{COLOR_RED}\nKeyboardInterrupt ! exiting program.{COLOR_RESET}")
                return
            except Exception as e:
                print(f"{COLOR_RED}Chat session ended with error: {e}{COLOR_RESET}")
                try:
                    if client and client.is_connected():
                        await client.disconnect()
                except Exception:
                    pass
                await asyncio.sleep(1)
                client = await ensure_connected()
                continue
    finally:
        try:
            if client and client.is_connected():
                await client.disconnect()
                print(f"{COLOR_GREEN}Client disconnected.{COLOR_RESET}")
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print(f"{COLOR_RED}\nExiting...{COLOR_RESET}")
