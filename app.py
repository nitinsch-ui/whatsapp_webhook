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

@app.route("/", methods=["POST"])
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print("📩 Received message data:")
    print(data)  # 👈 This will show the full message payload in Render logs
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
