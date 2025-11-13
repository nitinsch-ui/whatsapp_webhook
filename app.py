from flask import Flask, request
import json
import os
from datetime import datetime
import requests

app = Flask(__name__)

# ✅ Your Verify Token (same as in Meta Developer Console)
VERIFY_TOKEN = "my_verify_token"

# ✅ Health check / Verification endpoint for Meta
@app.route("/", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verified successfully", flush=True)
        return challenge, 200
    else:
        print("❌ Verification failed", flush=True)
        return "Verification failed", 403


# -------------------------------
# 🧠 To-Do logic
# -------------------------------

task_data = {}  # stores { date_str: [ {"task": "Gym", "done": False}, ... ] }

# ✅ helper: send text + optional buttons
def send_whatsapp_message(to, text, buttons=None):
    phone_number_id = os.getenv("PHONE_NUMBER_ID")
    token = os.getenv("WHATSAPP_TOKEN")

    if not phone_number_id or not token:
        print("⚠️ Missing PHONE_NUMBER_ID or WHATSAPP_TOKEN environment variables", flush=True)
        return

    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {"messaging_product": "whatsapp", "to": to}

    if buttons:
        payload["type"] = "interactive"
        payload["interactive"] = {
            "type": "button",
            "body": {"text": text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b.lower(), "title": b}} for b in buttons
                ]
            },
        }
    else:
        payload["type"] = "text"
        payload["text"] = {"body": text}

    r = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent message to {to}: {r.status_code} {r.text}", flush=True)


# ✅ helper: return today's todo list
def get_day_todo_list():
    today = datetime.now().strftime("%A, %d %B %Y")
    if today not in task_data:
        preset = [
            "Meditation",
            "Lemon water",
            "Eat nuts",
            "Go to office",
            "Office tasks",
            "Eat fruit",
            "Gym",
            "Daily steps",
            "Maintain diet",
            "Watch 2 lectures"
        ]
        task_data[today] = [{"task": t, "done": False} for t in preset]
    return today, task_data[today]


# ✅ helper: update or add task
def update_task(today, number, new_text):
    todo = task_data[today]
    if number <= len(todo):
        todo[number - 1]["task"] = new_text
    else:
        todo.append({"task": new_text, "done": False})


# ✅ helper: mark tasks as done
def mark_done(today, numbers):
    todo = task_data[today]
    for n in numbers:
        if 1 <= n <= len(todo):
            todo[n - 1]["done"] = True


# ✅ helper: calculate progress
def get_progress(today):
    todo = task_data[today]
    total = len(todo)
    done = sum(1 for t in todo if t["done"])
    return done, total


# ✅ main webhook (handles incoming WhatsApp messages)
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print("📩 Received:", json.dumps(data, indent=2), flush=True)

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]
            text = message.get("text", {}).get("body", "").strip()
            today, todo = get_day_todo_list()

            # HI → show list
            if text.lower() == "hi":
                tasks_text = "\n".join(
                    [f"{i+1}. {'✅' if t['done'] else '⬜'} {t['task']}" for i, t in enumerate(todo)]
                )
                send_whatsapp_message(
                    from_number,
                    f"Here is your to-do list for {today}:\n\n{tasks_text}",
                    buttons=["Update", "Progress"]
                )

            # BUTTON or command: Update
            elif text.lower() in ["update", "reply:update"]:
                send_whatsapp_message(
                    from_number,
                    "Please send the item number and new task (e.g. '3. Go for a walk')."
                )

            # Update task (e.g. 3. Go for a walk)
            elif "." in text and text.split(".")[0].isdigit():
                number = int(text.split(".")[0])
                new_text = text.split(".", 1)[1].strip()
                update_task(today, number, new_text)
                send_whatsapp_message(from_number, f"✅ Task {number} updated to: {new_text}")

            # Mark done (e.g. 1,2,3 done)
            elif text.lower().endswith("done"):
                nums = [
                    int(n)
                    for n in text.lower().replace("done", "").replace(" ", "").split(",")
                    if n.isdigit()
                ]
                mark_done(today, nums)
                done, total = get_progress(today)
                send_whatsapp_message(
                    from_number, f"✅ Marked {len(nums)} tasks done.\nProgress: {done}/{total}"
                )

            # BUTTON or command: Progress
            elif text.lower() in ["progress", "reply:progress"]:
                done, total = get_progress(today)
                send_whatsapp_message(from_number, f"📊 Progress: {done}/{total} tasks done.")

    except Exception as e:
        print("⚠️ Error:", e, flush=True)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
