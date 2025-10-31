from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

print("🚀 Flask 앱 초기화 중...")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("❌ GOOGLE_API_KEY 환경변수 없음. Render 환경변수 탭 확인 필요.")
    raise EnvironmentError("Missing GOOGLE_API_KEY environment variable.")
else:
    print("✅ GOOGLE_API_KEY 로드 성공")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("models/gemini-2.5-flash")
    print("✅ Gemini 모델 불러오기 성공")
except Exception as e:
    print(f"❌ Gemini 모델 초기화 실패: {e}")

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
            "청소년 대화에서 비속어나 공격적 표현을 부드럽게 바꿔줘. "
            "이유와 대체 표현을 친근하게 설명해줘. "
            "교정 문장과 설명 사이에는 반드시 '|' 기호를 넣어."
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

        # -------------------------------
        # | 기호를 기준으로 분리
        # -------------------------------
        if "|" in result_text:
            parts = result_text.split("|", 1)
            corrected_sentence = parts[0].strip()
            reason = parts[1].strip()
        else:
            corrected_sentence = result_text
            reason = "교정 이유를 찾을 수 없습니다."

        print(f"교정 문장: {corrected_sentence}")
        print(f"교정 이유: {reason}")

        # JSON 형태로 Adalo에서 쉽게 처리 가능하도록 반환
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
