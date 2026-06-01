import os
import sys
import asyncio
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from cover_letter_generator import process_job, append_to_google_sheet

def format_result_message_for_profile(profile_name: str, profile_data: dict, header: str = "") -> str:
    job_eval = profile_data.get("job_evaluation", {})
    letter_parts = profile_data.get("letter_parts", {})
    screening = profile_data.get("screening_answers", "")
    hook_options = profile_data.get("hook_options", [])
    selected_hook = profile_data.get("selected_hook", "")

    blocks = []
    if header:
        blocks.append(f"*{header}*")
    if job_eval.get("decision") == "PASS":
        blocks.append(f"✅ *Решение:* PASS\n_{job_eval.get('reasoning')}_")
    else:
        blocks.append(f"❌ *Решение:* SKIP\n_{job_eval.get('reasoning')}_")

    obs = job_eval.get("observations", [])
    if obs:
        obs_text = ", ".join([f"{o['type']}" for o in obs])
        blocks.append(f"🏷️ *Наблюдения:* {obs_text}")

    if hook_options:
        lines = []
        for i, h in enumerate(hook_options, 1):
            marker = "✅" if h.get("text") == selected_hook else "  "
            lines.append(f"{marker} {i}. _(score: {h.get('specificity_score', '?')})_ {h.get('text', '')}")
        blocks.append("🪝 *Hook options (✅ = auto-selected):*\n" + "\n".join(lines))

    if letter_parts:
        parts = []
        for part_name in ['hook', 'bridge', 'case1_text', 'case2_text', 'closing', 'cta', 'signature']:
            text = letter_parts.get(part_name)
            print(text)
            if text:
                parts.append(text)
        cover_letter_text = "\n".join(parts)
        blocks.append(f"📝 *Письмо-отклик:*\n```{cover_letter_text}```")

    if screening:
        blocks.append(f"❓ *Ответы на вопросы:*\n```{screening}```")

    msg = "\n\n".join(blocks)
    if len(msg) > 4000:
        msg = msg[:3950] + "\n... (сообщение обрезано) + ```"
    return msg

def build_buttons_blocks() -> list:
    return [
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Save to Google Sheets"},
                    "style": "primary",
                    "action_id": "save_btn"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reset Session"},
                    "style": "danger",
                    "action_id": "reset_btn"
                }
            ]
        }
    ]

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    raise ValueError("Missing Slack tokens")

slack_app = App(token=SLACK_BOT_TOKEN)

user_sessions = {}
MAX_CONTEXT_CHARS = 150000

def get_user_session(user_id: str):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "history": [],
            "total_chars": 0,
            "saved_state": None,
            "last_result": None,
            "last_job_description": None,
            "original_job_description": None,
            "last_buttons_ts": None,
            "last_buttons_channel": None
        }
    return user_sessions[user_id]

def add_to_history(user_id: str, role: str, content: str):
    session = get_user_session(user_id)
    session["history"].append({"role": role, "content": content})
    session["total_chars"] += len(content)
    while session["total_chars"] > MAX_CONTEXT_CHARS and len(session["history"]) > 1:
        removed = session["history"].pop(0)
        session["total_chars"] -= len(removed["content"])

def reset_user_history(user_id: str):
    user_sessions[user_id] = {
        "history": [],
        "total_chars": 0,
        "saved_state": None,
        "last_result": None,
        "last_job_description": None,
        "original_job_description": None,
        "last_buttons_ts": None,
        "last_buttons_channel": None
    }
    logger.info(f"История для {user_id} сброшена")

def disable_previous_buttons(client, user_id):
    session = get_user_session(user_id)
    ts = session.get("last_buttons_ts")
    channel = session.get("last_buttons_channel")
    if not ts or not channel:
        return
    try:
        resp = client.conversations_history(channel=channel, oldest=ts, limit=1, inclusive=True)
        messages = resp.get("messages", [])
        if messages and messages[0].get("ts") == ts:
            original_blocks = messages[0].get("blocks", [])
            new_blocks = [block for block in original_blocks if block.get("type") != "actions"]
            if not new_blocks:
                new_blocks = None
            client.chat_update(
                channel=channel,
                ts=ts,
                text="(Действия устарели.)",
                blocks=new_blocks
            )
    except Exception as e:
        logger.warning(f"Не удалось обновить предыдущее сообщение с кнопками: {e}")
    finally:
        session["last_buttons_ts"] = None
        session["last_buttons_channel"] = None

def send_with_buttons(client, channel, user_id, text="", blocks=None):
    response = client.chat_postMessage(channel=channel, text=text, blocks=blocks)
    ts = response["ts"]
    session = get_user_session(user_id)
    session["last_buttons_ts"] = ts
    session["last_buttons_channel"] = channel
    return response


@slack_app.action("save_btn")
def handle_save(ack, body, client, logger):
    ack()
    user_id = body["user"]["id"]
    session = get_user_session(user_id)
    result = session.get("last_result")   # словарь {имя_профиля: данные}
    original_job_description = session.get("original_job_description")
    if not result or not original_job_description:
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=user_id,
            text="⚠️ Нет данных для сохранения. Сначала отправьте вакансию."
        )
        return

    def save_worker():
        for profile_name, profile_data in result.items():
            job_eval = profile_data.get("job_evaluation", {})
            if job_eval.get("decision") == "PASS":
                # Собираем полный текст письма из letter_parts
                letter_parts = profile_data.get("letter_parts", {})
                full_letter = "\n\n".join([
                    part for part in [
                        letter_parts.get("hook"),
                        letter_parts.get("bridge"),
                        letter_parts.get("case1_text"),
                        letter_parts.get("case2_text"),
                        letter_parts.get("closing"),
                        letter_parts.get("cta"),
                        letter_parts.get("signature")
                    ] if part
                ]).strip()
                # Если letter_parts пуст (старый формат), пробуем cover_letter
                if not full_letter:
                    full_letter = profile_data.get("cover_letter", "")
                screening_answers = profile_data.get("screening_answers", "")
                append_to_google_sheet(
                    original_job_description,
                    profile_name,
                    full_letter,
                    screening_answers
                )
    import threading
    threading.Thread(target=save_worker, daemon=True).start()
    client.chat_postEphemeral(
        channel=body["channel"]["id"],
        user=user_id,
        text="✅ Данные отправлены на сохранение в Google Sheets."
    )


@slack_app.action("reset_btn")
def handle_reset(ack, body, client, logger):
    ack()
    user_id = body["user"]["id"]
    session = get_user_session(user_id)
    # Обновляем сообщение с кнопками, которое было отправлено ранее (если есть)
    ts = session.get("last_buttons_ts")
    channel = session.get("last_buttons_channel")
    if ts and channel:
        try:
            client.chat_update(
                channel=channel,
                ts=ts,
                text="",
                blocks=None
            )
        except Exception as e:
            logger.warning(f"Не удалось обновить сообщение после сброса: {e}")
    reset_user_history(user_id)
    client.chat_postEphemeral(
        channel=body["channel"]["id"],
        user=user_id,
        text="🔄 Сессия сброшена. История и сохранённые данные удалены."
    )

@slack_app.message("")
def handle_direct_message(message, say):
    logger.info(f"📨 Получено сообщение: {message}")
    if message.get("channel_type") != "im":
        return
    if "bot_id" in message or message.get("subtype"):
        return
    user_text = message.get("text", "").strip()
    user_id = message.get("user")
    if not user_id:
        say("Не удалось идентифицировать пользователя.")
        return
    channel = message.get("channel")

    # Удаляем кнопки из предыдущего сообщения
    disable_previous_buttons(say.client, user_id)

    # Обработка команды RESET (текстовая)
    if user_text.upper().startswith("RESET"):
        rest = user_text[5:].strip()
        reset_user_history(user_id)
        say("🔄 История диалога сброшена. Я забыл предыдущие сообщения.")
        if not rest:
            return
        user_text = rest

    if not user_text:
        say("Пожалуйста, отправьте описание вакансии.")
        return

    session = get_user_session(user_id)
    is_first_request = len(session["history"]) == 0

    add_to_history(user_id, "user", user_text)
    say("⏳ Обрабатываю ваш запрос... Это может занять до минуты.")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        history = session["history"]
        saved_state = session.get("saved_state")
        result, new_saved_state = loop.run_until_complete(
            process_job(
                job_description=user_text,
                conversation_history=history,
                saved_state=saved_state
            )
        )
        print(result)
        if new_saved_state is not None:
            # При редактировании сохраняем только PASS профили? Здесь new_saved_state уже содержит отфильтрованные данные (в process_job мы фильтруем)
            session["saved_state"] = new_saved_state
    except Exception as e:
        logger.exception("Ошибка при вызове process_job")
        say(f"❌ Внутренняя ошибка: {str(e)}")
        return
    finally:
        loop.close()

    if "error" in result:
        say(f"❌ Ошибка: {result['error']}")
        return

    session["last_result"] = result
    session["last_job_description"] = user_text
    if is_first_request:
        session["original_job_description"] = user_text

    # Формируем ответное сообщение (для каждого профиля отдельно)
    # Если результат — словарь с профилями
    for profile_name, profile_data in result.items():
        decision = profile_data.get("job_evaluation", {}).get("decision", "UNKNOWN")
        header = f"{profile_name} ({decision})"
        msg_text = format_result_message_for_profile(profile_name, profile_data, header=header)
        say(msg_text)

    # Отправляем кнопки один раз для всех профилей (одни и те же кнопки)
    send_with_buttons(say.client, channel, user_id, text="Действия с результатами:", blocks=build_buttons_blocks())

    # Добавляем в историю краткий лог (не обязательно)
    add_to_history(user_id, "assistant", f"Сгенерированы ответы для {len(result)} профилей")

if __name__ == "__main__":
    handler = SocketModeHandler(slack_app, SLACK_APP_TOKEN)
    logger.info("⚡️ Slack‑бот запущен и слушает сообщения...")
    handler.start()
