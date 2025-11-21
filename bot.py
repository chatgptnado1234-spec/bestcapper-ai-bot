
import os
import json
import math
import random
from flask import Flask, request, abort

import telebot
from telebot.types import Message

# load token from env
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required")

bot = telebot.TeleBot(TOKEN, parse_mode=None)
app = Flask(__name__)

MATCHES_FILE = "matches.json"
BETS_FILE = "bets.json"

# --- helpers for persistence ---
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# initialize storage
matches = load_json(MATCHES_FILE, {})  # id -> {teamA,teamB,lambdaA,lambdaB}
bets = load_json(BETS_FILE, {})  # chat_id -> list of bets

def next_match_id():
    if not matches:
        return "1"
    ids = [int(i) for i in matches.keys() if i.isdigit()]
    return str(max(ids) + 1)

# simple Poisson sampler (Knuth)
def poisson_sample(lmbda):
    L = math.exp(-lmbda)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1

# run N simulations and collect stats
def run_simulation(lambda_a, lambda_b, n=10000):
    wins_a = wins_b = draws = 0
    total_goals_a = 0
    total_goals_b = 0
    for _ in range(n):
        ga = poisson_sample(lambda_a)
        gb = poisson_sample(lambda_b)
        total_goals_a += ga
        total_goals_b += gb
        if ga > gb:
            wins_a += 1
        elif gb > ga:
            wins_b += 1
        else:
            draws += 1
    return {
        "wins_a_pct": wins_a / n * 100,
        "wins_b_pct": wins_b / n * 100,
        "draws_pct": draws / n * 100,
        "avg_goals_a": total_goals_a / n,
        "avg_goals_b": total_goals_b / n,
        "simulations": n,
    }

# --- Telegram handlers ---
@bot.message_handler(commands=["start"])
def handle_start(message: Message):
    bot.reply_to(message, "Привет! Я бот анализа матчей. /help для команд.")

@bot.message_handler(commands=["help"])
def handle_help(message: Message):
    bot.reply_to(message,
                 "/addmatch НазваниеA НазваниеB lambdaA lambdaB — добавить матч\n"
                 "/list — список матчей\n"
                 "/simulate ID [N] — симуляция (по умолчанию 10000)\n"
                 "/bet ID выбор(1/X/2) сумма — поставить\n"
                 "/mybets — мои ставки\n"
                 "/status — статус сервиса")

@bot.message_handler(commands=["addmatch"])
def handle_addmatch(message: Message):
    parts = message.text.split(maxsplit=4)
    if len(parts) < 5:
        bot.reply_to(message, "Использование: /addmatch КомандаA КомандаB lambdaA lambdaB")
        return
    _, teamA, teamB, la, lb = parts
    try:
        la = float(la); lb = float(lb)
    except:
        bot.reply_to(message, "lambdaA и lambdaB должны быть числами (например 1.2)")
        return
    mid = next_match_id()
    matches[mid] = {"teamA": teamA, "teamB": teamB, "lambdaA": la, "lambdaB": lb}
    save_json(MATCHES_FILE, matches)
    bot.reply_to(message, f"Матч добавлен id={mid}: {teamA} — {teamB} (λA={la} λB={lb})")

@bot.message_handler(commands=["list"])
def handle_list(message: Message):
    if not matches:
        bot.reply_to(message, "Нет добавленных матчей.")
        return
    lines = []
    for k, v in matches.items():
        lines.append(f"{k}: {v['teamA']} — {v['teamB']} (λA={v['lambdaA']} λB={v['lambdaB']})")
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=["simulate"])
def handle_simulate(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Использование: /simulate ID [N]")
        return
    mid = parts[1]
    n = 10000
    if len(parts) >= 3:
        try:
            n = int(parts[2])
        except:
            bot.reply_to(message, "N должно быть целым числом")
            return
    if mid not in matches:
        bot.reply_to(message, "Матч с таким ID не найден.")
        return
    m = matches[mid]
    res = run_simulation(m["lambdaA"], m["lambdaB"], n=n)
    reply = (f"Результаты симуляции для {m['teamA']} — {m['teamB']} ({n} прогонов):\n"
             f"Победа {m['teamA']}: {res['wins_a_pct']:.2f}%\n"
             f"Ничья: {res['draws_pct']:.2f}%\n"
             f"Победа {m['teamB']}: {res['wins_b_pct']:.2f}%\n"
             f"Средние голы: {m['teamA']} {res['avg_goals_a']:.2f}, {m['teamB']} {res['avg_goals_b']:.2f}")
    bot.reply_to(message, reply)

@bot.message_handler(commands=["bet"])
def handle_bet(message: Message):
    parts = message.text.split()
    if len(parts) < 4:
        bot.reply_to(message, "Использование: /bet ID выбор(1/X/2) сумма")
        return
    mid, pick, amount = parts[1], parts[2].upper(), parts[3]
    if mid not in matches:
        bot.reply_to(message, "Матч не найден.")
        return
    if pick not in ("1", "X", "2"):
        bot.reply_to(message, "Выбор должен быть 1, X или 2")
        return
    try:
        amount = float(amount)
    except:
        bot.reply_to(message, "Сумма должна быть числом.")
        return
    cid = str(message.chat.id)
    bets.setdefault(cid, [])
    bets[cid].append({"match_id": mid, "pick": pick, "amount": amount})
    save_json(BETS_FILE, bets)
    bot.reply_to(message, f"Ставка добавлена на матч {mid}, выбор {pick}, сумма {amount}")

@bot.message_handler(commands=["mybets"])
def handle_mybets(message: Message):
    cid = str(message.chat.id)
    my = bets.get(cid, [])
    if not my:
        bot.reply_to(message, "У вас нет ставок.")
        return
    lines = []
    for b in my:
        m = matches.get(b["match_id"], {})
        name = f"{m.get('teamA','?')}—{m.get('teamB','?')}"
        lines.append(f"{b['match_id']} ({name}): {b['pick']} {b['amount']}")
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=["status"])
def handle_status(message: Message):
    msg = f"Матчей: {len(matches)}, пользователей со ставками: {len(bets)}"
    bot.reply_to(message, msg)

# --- webhook route for Telegram ---
@app.route("/" + TOKEN, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    else:
        abort(403)

# minimal index
@app.route("/", methods=["GET"])
def index():
    return "Bot is running"

# optional helper to set webhook programmatically (call once)
def set_webhook(url_base):
    url = url_base.rstrip("/") + "/" + TOKEN
    return bot.set_webhook(url)

# run (not used on Render with gunicorn)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))