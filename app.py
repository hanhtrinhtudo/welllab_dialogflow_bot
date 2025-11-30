import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# ================== DATA GIẢ LẬP (tạm thời) ==================
# Sau này mình tách ra file JSON / DB
SYMPTOM_TO_COMBO = {
    "đau đầu": {
        "combo_code": "COMBO_DAU_DAU_01",
        "title": "Combo hỗ trợ giảm đau đầu & tăng tuần hoàn máu não",
        "products": [
            {
                "code": "WL-101",
                "name": "Welllab Brain Support",
                "link": "https://example.com/wl-101"
            },
            {
                "code": "WL-202",
                "name": "Welllab Sleep Ease",
                "link": "https://example.com/wl-202"
            }
        ],
        "usage": "Uống sau ăn, ngày 2 lần, mỗi lần 1–2 viên. Dùng tối thiểu 2–3 tháng."
    },
    # sau này thêm: "mất ngủ": {...}, "đau dạ dày": {...}
}


def build_response_for_symptom(symptom_raw: str) -> str:
    """Ghép câu trả lời đẹp cho khách dựa trên triệu chứng."""
    if not symptom_raw:
        return (
            "Dạ em chưa nhận rõ triệu chứng ạ.\n"
            "Anh/chị mô tả giúp em đang gặp vấn đề gì (ví dụ: đau đầu, mất ngủ, đau dạ dày...) "
            "để em tư vấn combo phù hợp nhé."
        )

    symptom = symptom_raw.lower().strip()
    combo = SYMPTOM_TO_COMBO.get(symptom)

    if not combo:
        return (
            f"Dạ em chưa có combo tối ưu riêng cho tình trạng **{symptom_raw}** ạ.\n"
            "Anh/chị mô tả chi tiết hơn (thời gian bị, mức độ, bệnh nền) để em kiểm tra lại "
            "hoặc nhờ tuyến trên hỗ trợ tư vấn kỹ hơn cho mình ạ."
        )

    lines = []
    lines.append(
        f"Với tình trạng **{symptom_raw}**, bên em đang có **{combo['combo_code']}** – "
        f"{combo['title']} 👉"
    )

    for p in combo["products"]:
        lines.append(
            f"- {p['name']} (mã: {p['code']}) – xem chi tiết: {p['link']}"
        )

    lines.append("")
    lines.append(f"📌 Cách dùng khuyến nghị: {combo['usage']}")
    lines.append(
        "\nNếu anh/chị cho em thêm thông tin về tuổi, bệnh nền và thuốc đang dùng "
        "em sẽ điều chỉnh liều và thời gian dùng phù hợp hơn ạ."
    )
    lines.append(
        "\nAnh/chị muốn **được TVV gọi tư vấn thêm** hay **đặt luôn combo này** ạ?"
    )

    return "\n".join(lines)


# ================== DIALOGFLOW WEBHOOK ==================

@app.route("/dialogflow-webhook", methods=["POST"])
def dialogflow_webhook():
    """Endpoint nhận request từ Dialogflow."""
    data = request.get_json(silent=True, force=True) or {}

    query_result = data.get("queryResult", {})
    intent_name = query_result.get("intent", {}).get("displayName", "")
    parameters = query_result.get("parameters", {})

    # Mặc định trả lời nếu chưa xử lý intent
    fulfillment_text = (
        "Hiện em chưa xử lý intent này ạ, em sẽ báo kỹ thuật cập nhật thêm."
    )

    # Intent tư vấn đau đầu (và các triệu chứng dùng entity `trieu_chung`)
    if intent_name == "tuvan_dau_dau":
        symptom_value = parameters.get("trieu_chung")  # lấy từ entity @trieu_chung
        fulfillment_text = build_response_for_symptom(symptom_value)

    # Có thể thêm các intent khác ở đây...

    return jsonify({"fulfillmentText": fulfillment_text})


# ================== MAIN ==================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
