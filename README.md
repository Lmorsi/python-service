# AvaliaEdu — Serviço OpenCV

Serviço Python + Flask + OpenCV para leitura automática de cartões-resposta.
**Custo: R$ 0** — hospedado no plano gratuito do Render.com ou Railway.

---

## 🚀 Como fazer o deploy (Render.com — recomendado)

1. Copie **apenas a pasta `python-service`** para um repositório GitHub separado
2. Acesse https://render.com → **New → Web Service**
3. Conecte o repositório
4. Escolha **Docker** como runtime
5. O Render detecta o `render.yaml` automaticamente e configura tudo
6. Após o deploy (~3 min), copie:
   - A **URL** gerada (ex: `https://avaliaedu-opencv.onrender.com`)
   - A variável **`OPENCV_API_KEY`** gerada (em Environment → Reveal)
7. No seu app (Anything), adicione como variáveis de ambiente:
   - `OPENCV_SERVICE_URL` = URL do Render
   - `OPENCV_API_KEY`     = chave copiada

---

## 🐳 Alternativa: Railway

```bash
npm install -g @railway/cli
railway login
# dentro da pasta python-service:
railway init
railway up
```

---

## 🧪 Testar localmente

```bash
pip install -r requirements.txt
python app.py
# Servidor sobe em http://localhost:8000
```

Teste:
```bash
# Health check
curl http://localhost:8000/health

# Scan (substitua <base64> pela imagem real)
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua-chave" \
  -d '{"image": "<base64>", "num_questions": 10, "num_alternatives": 5}'
```

---

## 📋 Requisitos do cartão-resposta para melhor precisão

| ✅ Recomendado | ❌ Evitar |
|---|---|
| Caneta azul ou preta | Lápis fraco |
| Fundo branco | Papel amarelado |
| Bolhas bem preenchidas | Marcações parciais |
| Foto plana, bem iluminada | Foto torta ou com sombra |
| Cartão sem dobras | Cartão amassado |

---

## 🔁 Fluxo da API

```
POST /scan
Headers: X-API-Key: <sua-chave>
Body: {
  "image":            "<base64 da foto>",
  "num_questions":    10,
  "num_alternatives": 5
}

Response 200: {
  "answers":    { "1": "A", "2": "C", "3": null, ... },
  "confidence": { "1": 0.87, "2": 0.92, "3": 0.0, ... },
  "warnings":   ["Questão 3: nenhuma marcação detectada"]
}
```

- `answers[q]` = `null` → questão sem marcação clara (professor corrige manualmente)
- `confidence[q]` < 0.40 → marcação duvidosa (app pede confirmação)
