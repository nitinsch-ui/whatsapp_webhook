from flask import Flask, request
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "tasks.json"
VERIFY_TOKEN = "my_verify_token"

# Load tasks from JSON file at startup
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        task_data = json.load(f)
else:
    task_data = {}

# Function to save tasks to JSON file
def save_tasks():
    with open(DATA_FILE, "w") as f:
        json.dump(task_data, f)

# Function to send WhatsApp messages
def send_whatsapp_message(to, text, buttons=None):
    phone_number_id = os.getenv("PHONE_NUMBER_ID")
    token = os.getenv("WHATSAPP_TOKEN")

    if not phone_number_id or not token:
        print("⚠️ Missing PHONE_NUMBER_ID or WHATSAPP_TOKEN environment variables")
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
    print(f"📤 Sent message to {to}: {r.status_code} {r.text}")

# Load or initialize today's to-do list
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
        save_tasks()
    return today, task_data[today]

# Update task and save
def update_task(today, number, new_text):
    todo = task_data[today]
    if number <= len(todo):
        todo[number - 1]["task"] = new_text
    else:
        todo.append({"task": new_text, "done": False})
    save_tasks()

# Mark tasks as done and save
def mark_done(today, numbers):
    todo = task_data[today]
    for n in numbers:
        if 1 <= n <= len(todo):
            todo[n - 1]["done"] = True
    save_tasks()

# Webhook verification
@app.route("/", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verified successfully")
        return challenge, 200
    else:
        print(f"❌ Verification failed: mode={mode}, token={token}")
        return "Verification failed", 403

# Webhook to receive messages
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print("📩 Received:", data)

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]
            text = message.get("text", {}).get("body", "").strip()
            today, todo = get_day_todo_list()

            # Handle “hi” command
            if text.lower() == "hi":
                tasks_text = "\n".join(
                    [f"{i+1}. {'✅' if t['done'] else '⬜'} {t['task']}" for i, t in enumerate(todo)]
                )
                send_whatsapp_message(
                    from_number,
                    f"Here is your to-do list for {today}:\n\n{tasks_text}",
                    buttons=["Update", "Progress"]
                )

            # Handle update command
            elif text.lower() in ["update", "reply:update"]:
                send_whatsapp_message(
                    from_number,
                    "Please send the item number and new task (e.g. '3. Go for a walk')."
                )

            # Handle task update
            elif "." in text and text.split(".")[0].isdigit():
                number = int(text.split(".")[0])
                new_text = text.split(".", 1)[1].strip()
                update_task(today, number, new_text)
                send_whatsapp_message(from_number, f"✅ Task {number} updated to: {new_text}")

            # Handle marking tasks done
            elif text.lower().endswith("done"):
                numbers = [int(n) for n in text.lower().replace("done", "").replace(" ", "").split(",") if n.isdigit()]
                mark_done(today, numbers)
                done, total = len([t for t in todo if t["done"]]), len(todo)
                send_whatsapp_message(
                    from_number, f"✅ Marked {len(numbers)} tasks done.\nProgress: {done}/{total}"
                )

    except Exception as e:
        print("⚠️ Error:", e)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
