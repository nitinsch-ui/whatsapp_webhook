from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = "my_verify_token"

@app.route("/", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    else:
        return "Verification failed", 403

from datetime import date

# Store tasks in a simple in-memory dictionary (you can later move to DB/Google Sheet)
task_data = {}  # key = date, value = list of tasks with completion status

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print("📩 Received message data:", data, flush=True)

    try:
        value = data["entry"][0]["changes"][0]["value"]

        # Only parse if there are actual messages
        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]
            text = message.get("text", {}).get("body", "").strip()

            today = str(date.today())

            if text.lower().startswith("tasks"):
                tasks = [line.strip("- ").strip() for line in text.splitlines()[1:] if line.strip()]
                task_data[today] = [{"task": t, "done": False} for t in tasks]

                send_whatsapp_message(from_number, f"✅ Your tasks for {today} have been stored:\n" +
                                      "\n".join([f"- {t}" for t in tasks]))
        else:
            print("ℹ️ No messages to process, ignoring status update.", flush=True)

    except Exception as e:
        print("⚠️ Error parsing message:", e, flush=True)

    return "OK", 200





if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
