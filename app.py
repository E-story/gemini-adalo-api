from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import google.generativeai as genai
import json
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, 
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

print("🚀 Flask 앱 초기화 중...")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("❌ GOOGLE_API_KEY 환경변수 없음. Render 환경변수 탭 확인 필요.")
    raise EnvironmentError("Missing GOOGLE_API_KEY environment variable.")
else:
    print("✅ GOOGLE_API_KEY 로드 성공")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("models/gemini-2.5-flash-lite")
    print("✅ Gemini 모델 불러오기 성공")
except Exception as e:
    print(f"❌ Gemini 모델 초기화 실패: {e}")

USAGE_FILE = "usage.json"
DAILY_LIMIT = 30
API_LIMIT = 1000   # Google Gemini 무료 한도

def load_usage():
    if not os.path.exists(USAGE_FILE):
        return {"date": "", "count": 0}

    with open(USAGE_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {"date": "", "count": 0}

def save_usage(data):
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

@app.route("/", methods=["GET"])
def home():
    print("📡 '/' 경로 호출됨")
    return jsonify({
        "message": "Gemini 교정 API 작동 중",
        "endpoint": "/api/correct",
        "method": "POST",
        "body_format": {"text": "문장 내용"}
    })

@app.route("/api/correct", methods=["POST"])
def correct():
    usage = load_usage()
    today = datetime.now().strftime("%Y-%m-%d")

    # 날짜 바뀌면 초기화
    if usage["date"] != today:
        usage = {"date": today, "count": 0}
        save_usage(usage)

    # 일일 30회 초과 시 차단
    if usage["count"] >= DAILY_LIMIT:
        print("⛔ 일일 30회 요청 초과됨")
        return jsonify({
            "error": "오늘의 무료 사용량(30회)을 모두 사용했습니다. 내일 다시 이용해주세요."
        }), 429

    # API 총 한도 초과 시 차단
    if usage["count"] >= API_LIMIT:
        print("⛔ API 전체 무료 한도(1000회) 초과")
        return jsonify({
            "error": "AI 무료 API 한도가 모두 소진되어 서비스가 중단되었습니다."
        }), 429

    # 여기까지 통과하면 정상 요청 → 카운트 증가
    usage["count"] += 1
    save_usage(usage)

    print(f"🔢 현재 요청 수: {usage['count']}회")

    print("📩 /api/correct 호출됨")
    try:
        data = request.get_json(force=True)
        text = (data.get("text") or "").strip()
        print(f"입력 받은 텍스트: {text}")
        if not text:
            print("⚠️ text 필드 누락됨")
            return jsonify({"error": "text 필드가 필요합니다."}), 400

        instruction = (
            "너는 문장을 교정하는 AI야. "
            "청소년 대화에서 비속어나 공격적 표현을 부드럽게 바꿔줘."
            "문장을 교정할 때는 너무 강하게 할 필요는 없고 청소년 대화 간 어색하지 않는 선에서 교정해"
            "이유와 대체 표현을 친근하게 설명해줘. 단 교정할 필요가 없으면 원문을 그래도 출력하고 교정 이유로는 교정할 문장이 없다고 해"
            "문화의 획일화를 예방하기 위해 신조어나 사투리 등은 교정할 필요 없어."
            "'교정 결과:' 같은 건 사용하지 말고 그냥 완성된 문장과 설명만을 출력해. 교정 문장과 설명 사이에는 반드시 '|' 기호를 넣고."
        )
        prompt = f"{instruction}\n\n사용자 입력: {text}\nAI 교정:"
        print("🧠 Gemini API 호출 시작...")

        response = model.generate_content(prompt)
        print("✅ Gemini 응답 수신 완료")

        result_text = ""
        if hasattr(response, "text") and response.text:
            result_text = response.text.strip()
        elif hasattr(response, "candidates"):
            result_text = response.candidates[0].content.parts[0].text.strip()
        else:
            result_text = "(응답 없음)"

        print(f"출력 결과(앞부분): {result_text[:120]}")

        if "|" in result_text:
            parts = result_text.split("|", 1)
            corrected_sentence = parts[0].strip()
            reason = parts[1].strip()
        else:
            corrected_sentence = result_text
            reason = "교정 이유를 찾을 수 없습니다."

        print(f"교정 문장: {corrected_sentence}")
        print(f"교정 이유: {reason}")

        return jsonify({
            "original": text,
            "corrected": corrected_sentence,
            "reason": reason
        })

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🏁 Flask 앱 실행 시작")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
