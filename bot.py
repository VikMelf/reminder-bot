import discord
import asyncio
import re
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

REMINDERS_FILE = "reminders.json"
active_reminders = defaultdict(list)

UA = {
    "no_reminders": "{mention}, у тебе немає активних нагадувань 😊",
    "your_reminders": "**Твої нагадування ({count}):**",
    "reminder_line": "{num}. **{text}** — {time}",
    "added": "Ок! Нагадаю в приват {human_time}: **{text}** ⏰\nПереглянути: `!моїнагадування`\nСкасувати: `!скасувати [номер]`",
    "canceled": "Нагадування №{num} скасовано.",
    "no_such_number": "Немає нагадування з номером {num}. Перевір список: `!моїнагадування`",
    "cleared": "Усі твої нагадування очищено! Тепер чистий аркуш ✂️",
    "already_empty": "У тебе вже немає активних нагадувань 😊",
    "no_text": "Вкажи текст після часу!",
    "invalid_time": "Не зрозумів час. Приклади: 10хв, 30с, о 18:30",
    "invalid_clock": "Час некоректний (00:00–23:59).",
    "pls_open_dm": "{mention}, відкрий ЛС від ботів, щоб я міг писати в приват.",
    "remind_now": "НАГАДУЮ: **{text}** 🚨",
    "examples": "Приклади:\n`!нагадай 10хв Пити воду`\n`!нагадай о 18:30 Вечеря`\nПереглянути: `!моїнагадування`"
}

EN = {
    "no_reminders": "{mention}, you have no active reminders 😊",
    "your_reminders": "**Your reminders ({count}):**",
    "reminder_line": "{num}. **{text}** — {time}",
    "added": "Got it! Reminding in DM {human_time}: **{text}** ⏰\nView: `!reminders`\nCancel: `!cancel [number]`",
    "canceled": "Reminder #{num} canceled.",
    "no_such_number": "No reminder with number {num}. Check list: `!reminders`",
    "cleared": "All your reminders cleared! Fresh start ✂️",
    "already_empty": "You already have no active reminders 😊",
    "no_text": "Please add reminder text after the time!",
    "invalid_time": "Didn't understand the time. Examples: 10min, 30s, at 18:30",
    "invalid_clock": "Invalid time (00:00–23:59).",
    "pls_open_dm": "{mention}, please enable DMs from bots/server members.",
    "remind_now": "REMINDER: **{text}** 🚨",
    "examples": "Examples:\n`!remind 10min Drink water`\n`!remind at 18:30 Dinner`\nView: `!reminders`"
}

def detect_language(text: str) -> str:
    ua_chars = "абвгґджзклмнпрстуфхцчшщьйіїє"
    if any(c.lower() in ua_chars for c in text):
        return "ua"
    return "en"

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for user_id, rems in data.items():
                    active_reminders[int(user_id)] = [
                        (datetime.fromisoformat(r[0]), r[1]) for r in rems
                    ]
            print("Нагадування завантажено з файлу")
        except Exception as e:
            print(f"Помилка завантаження нагадувань: {e}")

def save_reminders():
    data = {}
    for user_id, rems in active_reminders.items():
        data[str(user_id)] = [
            (target.isoformat(), text) for target, text in rems
        ]
    try:
        with open(REMINDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Помилка збереження нагадувань: {e}")

@client.event
async def on_ready():
    load_reminders()
    print(f'Бот запущено! Я — {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    text = message.content.strip()
    lower = text.lower()
    lang = detect_language(text)
    t = UA if lang == "ua" else EN

    # Допомога
    if lower in ['!help', '!допомога', '!start', '!початок']:
        help_text = (
            "**Команди нагадувача:**\n\n"
            "`!нагадай 10хв Текст` / `!remind 10min Text` — нагадати через час\n"
            "`!нагадай о 18:30 Текст` / `!remind at 18:30 Text` — нагадати о певний час\n"
            "`!моїнагадування` / `!reminders` — показати твої нагадування\n"
            "`!скасувати 1` / `!cancel 1` — скасувати нагадування №1\n"
            "`!очиститинагадування` / `!clearreminders` — видалити всі твої нагадування\n\n"
            "Нагадування приходять у приват. Якщо не приходять — перевір налаштування приватних повідомлень у Discord."
        )
        await message.channel.send(help_text)
        return

    # Перегляд нагадувань
    if lower in ['!моїнагадування', '!нагадування', '!reminders', '!myreminders']:
        reminders = active_reminders[message.author.id]
        if not reminders:
            await message.channel.send(t["no_reminders"].format(mention=message.author.mention))
            return
        lines = [t["your_reminders"].format(count=len(reminders))]
        now = datetime.now()
        for i, (target, r_text) in enumerate(reminders, 1):
            secs = (target - now).total_seconds()
            if secs <= 0:
                continue
            if secs < 60:
                time_str = "менше хвилини" if lang == "ua" else "less than a minute"
            elif secs < 3600:
                mins = int(secs // 60)
                time_str = f"через {mins} хв" if lang == "ua" else f"in {mins} min"
            else:
                time_str = target.strftime('%H:%M')
            lines.append(t["reminder_line"].format(num=i, text=r_text, time=time_str))
        await message.channel.send("\n".join(lines))
        return

    # Скасування
    if lower.startswith(('!скасувати ', '!cancel ')):
        try:
            num = int(lower.split()[1])
            reminders = active_reminders[message.author.id]
            if 1 <= num <= len(reminders):
                reminders.pop(num - 1)
                save_reminders()
                await message.channel.send(t["canceled"].format(num=num))
            else:
                await message.channel.send(t["no_such_number"].format(num=num))
        except:
            await message.channel.send("Вкажи номер: `!скасувати 2` або `!cancel 3`")
        return

    # Очистити всі
    if lower in ['!очиститинагадування', '!clearreminders', '!очистити нагадування', '!clear reminders']:
        if not active_reminders[message.author.id]:
            await message.channel.send(t["already_empty"])
        else:
            active_reminders[message.author.id].clear()
            save_reminders()
            await message.channel.send(t["cleared"])
        return

    # Створення нагадування
    prefixes = ['!нагадай ', '!нагадати ', '!нагадування ', '!remind ', '!reminder ']
    for p in prefixes:
        if lower.startswith(p):
            full_text = text[len(p):].strip()
            break
    else:
        return

    if not full_text:
        await message.channel.send(t["examples"])
        return

    # Парсинг часу
    clock = re.search(r'(?:о|в|на|at|a)?\s*(\d{1,2}):(\d{2})', full_text, re.I)
    if clock:
        h, m = int(clock.group(1)), int(clock.group(2))
        now = datetime.now()
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        seconds = (target - now).total_seconds()
        reminder_text = full_text.replace(clock.group(0), '', 1).strip()
        human_time = f"о {h:02d}:{m:02d}" if lang == "ua" else f"at {h:02d}:{m:02d}"
        if target.date() > now.date():
            human_time += " завтра" if lang == "ua" else " tomorrow"
    else:
        match = re.search(r'(\d+)\s*([сsecsecondsхвminminutesгодhoursдdays]+)?', full_text, re.I)
        if not match:
            await message.channel.send(t["invalid_time"])
            return
        value = int(match.group(1))
        unit_raw = (match.group(2) or 'хв').lower()

        if unit_raw.startswith(('с', 'sec', 's')):
            seconds = value
            unit_display = "с" if lang == "ua" else "s"
        elif unit_raw.startswith(('хв', 'min', 'm')):
            seconds = value * 60
            unit_display = "хв" if lang == "ua" else "min"
        elif unit_raw.startswith(('год', 'h', 'hr')):
            seconds = value * 3600
            unit_display = "год" if lang == "ua" else "h"
        elif unit_raw.startswith(('д', 'day', 'd')):
            seconds = value * 86400
            unit_display = "д" if lang == "ua" else "day"
        else:
            seconds = value * 60
            unit_display = "хв" if lang == "ua" else "min"

        reminder_text = full_text.replace(match.group(0), '', 1).strip()
        human_time = f"через {value} {unit_display}" if lang == "ua" else f"in {value} {unit_display}"

    if not reminder_text:
        await message.channel.send(t["no_text"])
        return

    target_time = datetime.now() + timedelta(seconds=seconds)
    active_reminders[message.author.id].append((target_time, reminder_text))
    save_reminders()

    await message.channel.send(t["added"].format(human_time=human_time, text=reminder_text))

    await asyncio.sleep(seconds)

    active_reminders[message.author.id] = [r for r in active_reminders[message.author.id] if r[0] != target_time]
    save_reminders()

    try:
        await message.author.send(t["remind_now"].format(text=reminder_text))
    except:
        await message.channel.send(t["pls_open_dm"].format(mention=message.author.mention))

client.run(os.getenv('DISCORD_TOKEN'))
