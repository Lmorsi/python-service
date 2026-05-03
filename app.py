# app.py — Copie este conteúdo para `app.py`

```python
"""
AvaliaEdu — Serviço Flask/OpenCV de leitura de cartão-resposta
POST /scan  →  detecta respostas marcadas numa foto de cartão-resposta
"""
import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from detector import detect_answers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app     = Flask(__name__)
CORS(app)
API_KEY = os.environ.get("OPENCV_API_KEY", "")


@app.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return
    if API_KEY:
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "AvaliaEdu OpenCV"})


@app.route("/scan", methods=["POST"])
def scan():
    """
    Body JSON:
    {
      "image":            "<base64 da foto do cartão>",
      "num_questions":    10,
      "num_alternatives": 5     (opcional, padrão 5)
    }

    Resposta 200:
    {
      "answers":    {"1": "A", "2": "C", "3": null, ...},
      "confidence": {"1": 0.87, "2": 0.92, "3": 0.0, ...},
      "warnings":   ["Questão 3: nenhuma marcação detectada"]
    }
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Body JSON inválido"}), 400

        image_b64        = data.get("image")
        num_questions    = data.get("num_questions")
        num_alternatives = int(data.get("num_alternatives", 5))

        if not image_b64:
            return jsonify({"error": "Campo 'image' obrigatório"}), 400
        if not num_questions or not isinstance(num_questions, int):
            return jsonify({"error": "Campo 'num_questions' obrigatório (inteiro)"}), 400
        if not (2 <= num_alternatives <= 5):
            return jsonify({"error": "num_alternatives deve ser entre 2 e 5"}), 400

        logger.info(f"Scan: {num_questions}Q × {num_alternatives}A")
        answers, confidence, error = detect_answers(image_b64, num_questions, num_alternatives)

        if error:
            return jsonify({"error": error}), 422

        warnings = []
        for q_str, answer in answers.items():
            conf = (confidence or {}).get(q_str, 0)
            if answer is None:
                warnings.append(f"Questão {q_str}: nenhuma marcação detectada")
            elif conf < 0.40:
                warnings.append(f"Questão {q_str}: marcação pouco clara (confiança {int(conf*100)}%)")

        return jsonify({"answers": answers, "confidence": confidence or {}, "warnings": warnings})

    except Exception as e:
        logger.exception("Erro inesperado")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
```
