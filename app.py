# -------------------------------------------
# Adalo 연동용 Gemini 교정 REST API 서버
# -------------------------------------------
from flask import Flask, request, jsonify
import os
import google.generativeai as genai

app = Flask(__name__)

# -------- 1. API 키 설정 --------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise EnvironmentError("환경변수 GOOGLE_API_KEY가 설정되어 있지 않습니다. Replit Secrets에서 추가하세요.")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")

# -------- 2. 교정 엔드포인트 --------
@app.route("/api/correct", methods=["POST"])
def correct_text():
    try:
        data = request.get_json()
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "text 필드가 비어 있습니다."}), 400

        instruction = (
            "너는 문장을 교정하는 AI야. "
            "청소년 대화에서 비속어나 공격적 표현을 부드럽게 바꿔줘. "
            "이유와 대체 표현을 친근하게 설명해줘. "
            "교정 문장과 설명 사이에는 '|' 기호를 넣어."
        )

        prompt = f"{instruction}\n\n사용자 입력: {text}\nAI 교정:"
        response = model.generate_content(prompt)

        result = ""
        if hasattr(response, "text") and response.text:
            result = response.text.strip()
        elif hasattr(response, "candidates"):
            result = response.candidates[0].content.parts[0].text.strip()
        else:
            result = "(응답 없음)"

        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------- 3. 테스트용 기본 루트 --------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Gemini 교정 API 작동 중",
        "endpoint": "/api/correct",
        "method": "POST",
        "body_format": {"text": "문장 내용"}
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
