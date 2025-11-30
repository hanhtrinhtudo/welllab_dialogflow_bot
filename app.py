import os
import json
from pathlib import Path
from flask import Flask, request, jsonify

# ============ OPENAI ============
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

openai_client = None
if OpenAI and OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("[INFO] OpenAI client khởi tạo thành công – SẼ dùng NLP.")
    except Exception as e:
        print("[ERROR] Lỗi khởi tạo OpenAI client:", e)
else:
    print("[WARN] OpenAI client = None (thiếu thư viện hoặc thiếu OPENAI_API_KEY).")

app = Flask(__name__)


# ============ ENDPOINT TEST OPENAI ============

@app.route("/openai-status", methods=["GET"])
def openai_status():
    """
    Endpoint debug:
    - Cho biết server có thư viện OpenAI không
    - Có API key không
    - Client đã khởi tạo chưa
    - Gọi thử 1 request nhỏ tới model gpt-4o-mini
    """
    status = {
        "has_openai_class": OpenAI is not None,
        "has_api_key": bool(OPENAI_API_KEY),
        "client_initialized": openai_client is not None,
    }

    if openai_client:
        try:
            resp = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Bạn là hệ thống kiểm tra kết nối."},
                    {"role": "user", "content": "Trả lời đúng 1 từ: OK."},
                ],
                max_tokens=5,
                temperature=0,
            )
            status["test_call_ok"] = True
            status["test_content"] = resp.choices[0].message.content
        except Exception as e:
            status["test_call_ok"] = False
            status["error"] = str(e)
    else:
        status["test_call_ok"] = False

    return jsonify(status)


# ============ LOAD DATA TRIỆU CHỨNG ============

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SYMPTOMS_PATH = DATA_DIR / "symptoms_mapping.json"


def load_symptoms():
    try:
        with open(SYMPTOMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Không load được file triệu chứng: {e}")
        data = []

    index = {}
    canonical_names = []

    for item in data:
        names = item.get("names", [])
        if not names:
            continue
        canonical = names[0].lower().strip()
        canonical_names.append(canonical)
        for name in names:
            index[name.lower().strip()] = item

    print(f"[INFO] Loaded {len(data)} triệu chứng, {len(index)} tên mapping.")
    return index, canonical_names


SYMPTOM_INDEX, SYMPTOM_CANONICAL_LIST = load_symptoms()


# ============ TỪ ĐỒNG NGHĨA BỔ SUNG ============

SYMPTOM_SYNONYMS = {
    "đau đầu": [
        "nhức đầu",
        "nhức nửa đầu",
        "đau nửa đầu",
        "nhói đầu",
        "migraine",
        "đau đầu chóng mặt",
        "nặng đầu",
    ],
    "mất ngủ": [
        "khó ngủ",
        "không ngủ được",
        "ngủ không sâu giấc",
        "hay tỉnh giữa đêm",
        "thức khuya nhiều",
    ],
    # sau này mình bổ sung tiếp các nhóm triệu chứng khác...
}


def map_synonym_to_symptom(text: str) -> str:
    """Dò các cách nói đời thường rồi map về triệu chứng chuẩn."""
    t = text.lower()
    for canon_symptom, phrases in SYMPTOM_SYNONYMS.items():
        for phrase in phrases:
            if phrase in t:
                return canon_symptom
    return ""


# ============ XỬ LÝ TRIỆU CHỨNG ============

def find_symptom_record(symptom_raw: str):
    if not symptom_raw:
        return None

    key = symptom_raw.lower().strip()
    if key in SYMPTOM_INDEX:
        return SYMPTOM_INDEX[key]

    for name_key, record in SYMPTOM_INDEX.items():
        if key in name_key or name_key in key:
            return record

    return None


def detect_symptom_from_text(text: str) -> str:
    """
    Thứ tự ưu tiên:
    1) Map từ đồng nghĩa (vd: 'nhức nửa đầu' -> 'đau đầu')
    2) Dò theo danh sách tên trong file JSON
    """
    if not text:
        return ""

    # 1) Đồng nghĩa
    s = map_synonym_to_symptom(text)
    if s:
        return s

    # 2) Dò trong SYMPTOM_INDEX
    t = text.lower()
    for name_key, record in SYMPTOM_INDEX.items():
        if name_key in t:
            names = record.get("names", [])
            return names[0] if names else name_key

    return ""


def build_response_for_symptom(symptom_raw: str) -> str:
    if not symptom_raw:
        return (
            "Dạ em chưa nhận rõ triệu chứng ạ.\n"
            "Anh/chị mô tả giúp em đang gặp vấn đề gì (vd: đau đầu, mất ngủ, đau dạ dày...) "
            "để em gợi ý combo phù hợp nhé."
        )

    record = find_symptom_record(symptom_raw)

    if not record:
        return (
            f"Dạ với tình trạng **{symptom_raw}** em chưa có combo tối ưu ạ.\n"
            "Anh/chị mô tả chi tiết hơn (thời gian bị, mức độ, bệnh nền) "
            "để em nhờ tuyến trên tư vấn kỹ hơn nhé."
        )

    combo_code = record.get("combo_code", "")
    title = record.get("title", "")
    products = record.get("products", [])
    usage = record.get("usage", "")
    note = record.get("note", "")

    lines = []
    lines.append(f"Với tình trạng **{symptom_raw}**, bên em có **{combo_code} – {title}**:")

    for p in products:
        lines.append(
            f"- {p.get('name')} (mã: {p.get('code')}) – xem chi tiết: {p.get('link')}"
        )

    if usage:
        lines.append("\n📌 Cách dùng: " + usage)

    if note:
        lines.append("💡 Lưu ý: " + note)

    lines.append(
        "\nAnh/chị cho em biết tuổi, bệnh nền và thuốc đang dùng để em tinh chỉnh combo nhé."
    )
    lines.append("\nAnh/chị muốn **TVV gọi lại** hay **đặt luôn combo này** ạ?")

    return "\n".join(lines)


# ============ NLP HIỂU NGÔN NGỮ TỰ NHIÊN ============

def nlp_understand_message(text: str) -> dict:
    """
    Phân tích câu nói:
    - intent: symptom_advice / product_question / smalltalk / unknown
    - symptom: tên triệu chứng
    - product_code: WL-xxx nếu có
    """
    base = {
        "intent": "unknown",
        "symptom": "",
        "product_code": ""
    }

    if not text:
        return base

    # Nếu chưa cấu hình OpenAI → chỉ dùng keyword + synonyms
    if not openai_client:
        print("[INFO] NLP fallback (không dùng OpenAI).")
        symptom = detect_symptom_from_text(text)
        if symptom:
            base["intent"] = "symptom_advice"
            base["symptom"] = symptom
        return base

    # Có OpenAI: yêu cầu nó map symptom về danh sách hợp lệ hoặc rỗng
    symptom_list_str = ", ".join(sorted(set(SYMPTOM_CANONICAL_LIST)))

    prompt = (
        "Bạn là module NLP cho chatbot Welllab (tư vấn combo sản phẩm sức khỏe).\n"
        "Hãy phân tích câu tiếng Việt của người dùng và TRẢ VỀ JSON với 3 khóa:\n"
        "  \"intent\": \"symptom_advice\" | \"product_question\" | \"smalltalk\" | \"unknown\",\n"
        "  \"symptom\": \"tên triệu chứng\" nếu câu nói liên quan tới sức khỏe,\n"
        "  \"product_code\": \"WL-xxx\" nếu có xuất hiện mã sản phẩm.\n\n"
        f"Danh sách triệu chứng hợp lệ, nếu câu nói gần nghĩa với một trong số này thì phải CHỌN một trong chúng:\n"
        f"{symptom_list_str}\n\n"
        "Ví dụ: 'nhức nửa đầu, nhìn màn hình là choáng' → symptom = 'đau đầu'.\n"
        "Ví dụ: 'dạo này stress, ngủ không sâu giấc, hay tỉnh giữa đêm' → symptom = 'mất ngủ'.\n"
        "Nếu không liên quan triệu chứng nào thì để symptom là \"\".\n"
        "Nếu chỉ chào hỏi (hello, chào em, em khoẻ không) thì intent = \"smalltalk\".\n"
        "Chỉ trả về JSON, không giải thích thêm."
    )

    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            max_tokens=200,
            temperature=0.1,
        )
        content = resp.choices[0].message.content
        print("[DEBUG] NLU raw:", content)

        parsed = json.loads(content)
        base.update({k: parsed.get(k, base[k]) for k in base.keys()})

        # Nếu GPT bảo intent = symptom_advice nhưng không trả symptom → fallback
        if base["intent"] == "symptom_advice" and not base["symptom"]:
            fb = detect_symptom_from_text(text)
            if fb:
                base["symptom"] = fb

        return base

    except Exception as e:
        print("[ERROR] NLP OpenAI:", e)
        symptom = detect_symptom_from_text(text)
        if symptom:
            base["intent"] = "symptom_advice"
            base["symptom"] = symptom
        return base


# ============ API CHO WEBCHAT ============

@app.route("/webchat", methods=["POST", "OPTIONS"])
def webchat():
    if request.method == "OPTIONS":
        return jsonify({"ok": True})

    data = request.get_json(silent=True, force=True) or {}
    user_text = data.get("message", "")

    print(f"[INFO] Webchat nhận: {user_text}")

    nlu = nlp_understand_message(user_text)
    print("[INFO] NLP:", nlu)

    intent = nlu.get("intent", "")
    symptom = nlu.get("symptom", "")
    product_code = nlu.get("product_code", "")

    # 1) Tư vấn triệu chứng
    if intent == "symptom_advice" and (symptom or detect_symptom_from_text(user_text)):
        if not symptom:
            symptom = detect_symptom_from_text(user_text)
        reply = build_response_for_symptom(symptom)

    # 2) Hỏi mã sản phẩm
    elif intent == "product_question" and product_code:
        reply = (
            f"Anh/chị hỏi về sản phẩm **{product_code}**.\n"
            "Hiện bản này ưu tiên tư vấn theo triệu chứng.\n"
            "Anh/chị mô tả vấn đề sức khỏe để em gợi ý combo chính xác hơn nhé."
        )

    # 3) Smalltalk
    elif intent == "smalltalk":
        reply = (
            "Dạ em chào anh/chị 😊\n"
            "Anh/chị đang gặp vấn đề gì về sức khỏe để em hỗ trợ ạ?"
        )

    # 4) Không hiểu rõ
    else:
        reply = (
            "Dạ em chưa hiểu rõ nhu cầu của anh/chị ạ.\n"
            "Anh/chị mô tả giúp em triệu chứng (đau đầu, mất ngủ, dạ dày...) nhé."
        )

    return jsonify({"reply": reply})


# ============ WEBHOOK DIALOGFLOW (GIỮ LẠI) ============

@app.route("/dialogflow-webhook", methods=["POST"])
def dialogflow_webhook():
    data = request.get_json(silent=True, force=True) or {}
    query_result = data.get("queryResult", {})
    intent_name = query_result.get("intent", {}).get("displayName", "")
    params = query_result.get("parameters", {})

    print(f"[INFO] Dialogflow nhận intent: {intent_name}")

    if intent_name in ["tuvan_dau_dau", "tuvan_mat_ngu", "tuvan_dau_da_day"]:
        symptom_value = params.get("trieu_chung")
        if isinstance(symptom_value, list):
            symptom_value = symptom_value[0]
        reply = build_response_for_symptom(symptom_value)
    else:
        reply = "Em chưa xử lý intent này."

    return jsonify({"fulfillmentText": reply})


# ============ CORS ============

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
