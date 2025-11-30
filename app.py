import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/dialogflow-webhook", methods=["POST"])
def dialogflow_webhook():
    data = request.get_json(silent=True, force=True) or {}
    query_result = data.get("queryResult", {})
    intent_name = query_result.get("intent", {}).get("displayName", "")
    params = query_result.get("parameters", {})

    # Mặc định
    text = f"Em nhận được intent: {intent_name}. Đây là câu trả lời từ WEBHOOK nha ông chủ."

    if intent_name == "tuvan_dau_dau":
        trieu_chung = params.get("trieu_chung")
        text = (
            f"Đây là câu trả lời từ WEBHOOK cho triệu chứng: {trieu_chung}.\n"
            "Sau này em sẽ tra trong dữ liệu combo thật, còn giờ demo thế này trước ạ."
        )

    return jsonify({"fulfillmentText": text})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
