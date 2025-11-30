import os
import json
from pathlib import Path
from flask import Flask, request, jsonify

app = Flask(__name__)

# ============ LOAD DATA TỪ FILE JSON ============
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SYMPTOMS_PATH = DATA_DIR / "symptoms_mapping.json"


def load_symptoms():
    try:
        with open(SYMPTOMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Không đọc được {SYMPTOMS_PATH}: {e}")
        data = []

    # Tạo index: mỗi tên (name) → 1 record
    index = {}
    for item in data:
        for name in item.get("names", []):
            key = name.lower().strip()
            index[key] = item
    print(f"[INFO] Đã load {len(data)} triệu chứng, {len(index)} tên mapping.")
    return index


SYMPTOM_INDEX = load_symptoms()


def find_symptom_record(symptom_raw: str):
    """Tìm record theo tên triệu chứng người dùng nói."""
    if not symptom_raw:
        return None

    key = symptom_raw.lower().strip()
    # Tìm đúng trước
    if key in SYPMTOM_INDEX:
        return SYPMTOM_INDEX[key]

    # Nếu không thấy, thử dò gần giống (bắt đầu bằng…)
    for name_key, record in SYPMTOM_INDEX.items():
        if key in name_key or name_key in key:
            return record
    return None


def build_response_for_symptom(symptom_raw: str) -> str:
    if not symptom_raw:
        return (
            "Dạ em chưa nhận rõ triệu chứng ạ.\n"
            "Anh/chị mô tả giúp em đang gặp vấn đề gì (ví dụ: đau đầu, mất ngủ, đau dạ dày...) "
            "để em tư vấn combo phù hợp nhé."
        )

    record = find_symptom_record(symptom_raw)
    if not record:
        return (
            f"Dạ với tình trạng **{symptom_raw}** em chưa có combo tối ưu sẵn ạ.\n"
            "Anh/chị mô tả chi tiết hơn (thời gian bị, mức độ, bệnh nền) để em nhờ tuyến trên "
            "hoặc chuyên gia hỗ trợ tư vấn kỹ hơn cho mình nhé."
        )

    combo_code = record.get("combo_code", "")
    title = record.get("title", "")
    products = record.get("products", [])
    usage = record.get("usage", "")
    note = record.get("note", "")

    lines = []
    lines.append(
        f"Với tình trạng **{symptom_raw}**, bên em đang có **{combo_code}** – {title}:"
    )

    for p in products:
        lines.append(
            f"- {p.get('name')} (mã: {p.get('code')}) – xem chi tiết: {p.get('link')}"
        )

    if usage:
        lines.append("")
        lines.append(f"📌 Cách dùng khuyến nghị: {usage}")

    if note:
        lines.append(f"💡 Lưu ý thêm: {note}")

    lines.append(
        "\nAnh/chị cho em thêm thông tin về tuổi, bệnh nền và thuốc đang dùng "
        "để em điều chỉnh tư vấn phù hợp hơn ạ."
    )
    lines.append(
        "\nAnh/chị muốn **được TVV gọi tư vấn thêm** hay **đặt luôn combo này** ạ?"
    )

    return "\n".join(lines)


# ============ DIALOGFLOW WEBHOOK ============

@app.route("/dialogflow-webhook", methods=["POST"])
def dialogflow_webhook():
    data = request.get_json(silent=True, force=True) or {}
    query_result = data.get("queryResult", {})
    intent_name = query_result.get("intent", {}).get("displayName", "")
    params = query_result.get("parameters", {})

    print(f"[INFO] Nhận intent: {intent_name}, params: {params}")

    text = "Em chưa xử lý intent này ạ, sẽ nhờ kỹ thuật bổ sung sau."

    if intent_name in ["tuvan_dau_dau", "tuvan_mat_ngu", "tuvan_dau_da_day"]:
    symptom_value = parameters.get("trieu_chung")
    text = build_response_for_symptom(symptom_value)

    return jsonify({"fulfillmentText": text})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)

