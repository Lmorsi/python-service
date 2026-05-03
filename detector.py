# detector.py — Copie este conteúdo para `detector.py`

```python
"""
AvaliaEdu — Módulo de detecção de cartão-resposta via OpenCV
"""
import cv2
import numpy as np
import base64
import logging

logger = logging.getLogger(__name__)
ALTERNATIVES = ["A", "B", "C", "D", "E"]


def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s    = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    widthA   = np.sqrt(((br[0]-bl[0])**2)+((br[1]-bl[1])**2))
    widthB   = np.sqrt(((tr[0]-tl[0])**2)+((tr[1]-tl[1])**2))
    maxWidth = max(int(widthA), int(widthB))
    heightA   = np.sqrt(((tr[0]-br[0])**2)+((tr[1]-br[1])**2))
    heightB   = np.sqrt(((tl[0]-bl[0])**2)+((tl[1]-bl[1])**2))
    maxHeight = max(int(heightA), int(heightB))
    dst = np.array([[0,0],[maxWidth-1,0],[maxWidth-1,maxHeight-1],[0,maxHeight-1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxWidth, maxHeight))


def grid_fallback(thresh, num_questions, num_alternatives):
    """Fallback: divide imagem em grade e mede preenchimento por célula."""
    h, w = thresh.shape
    margin_x = int(w * 0.08)
    margin_y = int(h * 0.05)
    grid_w = w - 2 * margin_x
    grid_h = h - 2 * margin_y
    cell_w = grid_w // num_alternatives
    cell_h = grid_h // num_questions
    answers    = {}
    confidence = {}
    for q in range(num_questions):
        best_idx = 0
        best_fill = 0
        for a in range(num_alternatives):
            x1 = margin_x + a * cell_w + int(cell_w * 0.1)
            x2 = margin_x + (a+1) * cell_w - int(cell_w * 0.1)
            y1 = margin_y + q * cell_h + int(cell_h * 0.1)
            y2 = margin_y + (q+1) * cell_h - int(cell_h * 0.1)
            fill = cv2.countNonZero(thresh[y1:y2, x1:x2])
            if fill > best_fill:
                best_fill = fill
                best_idx  = a
        fill_ratio = best_fill / (cell_w * cell_h) if cell_w * cell_h > 0 else 0
        q_str = str(q + 1)
        if fill_ratio > 0.15:
            answers[q_str]    = ALTERNATIVES[best_idx]
            confidence[q_str] = round(fill_ratio, 3)
        else:
            answers[q_str]    = None
            confidence[q_str] = 0.0
    return answers, confidence, None


def detect_answers(image_base64, num_questions, num_alternatives=5):
    """
    Função principal.
    Retorna: (answers, confidence, error)
      answers    = {"1": "A", "2": "C", ...}   None = não marcado
      confidence = {"1": 0.87, "2": 0.65, ...}
      error      = string | None
    """
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        nparr = np.frombuffer(base64.b64decode(image_base64), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            return None, None, "Não foi possível decodificar a imagem."

        image   = cv2.resize(image, (800, 1100))
        gray    = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged   = cv2.Canny(blurred, 75, 200)

        # Buscar bordas do documento para correção de perspectiva
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        doc_cnt = None
        for c in contours:
            peri   = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                doc_cnt = approx
                break

        warped = four_point_transform(gray, doc_cnt.reshape(4, 2)) if doc_cnt is not None else gray[30:-30, 30:-30]

        # Threshold de Otsu (automático, sem parâmetros manuais)
        thresh = cv2.threshold(warped, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

        # Detectar bolhas (contornos circulares de tamanho adequado)
        cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h_img, w_img = thresh.shape
        min_s = int(min(h_img, w_img) * 0.018)
        max_s = int(min(h_img, w_img) * 0.10)
        bubble_cnts = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            ar   = w / float(h) if h > 0 else 0
            area = cv2.contourArea(c)
            if min_s <= w <= max_s and min_s <= h <= max_s and 0.65 <= ar <= 1.45 and area > (min_s**2)*0.4:
                bubble_cnts.append(c)

        if len(bubble_cnts) < num_questions * num_alternatives * 0.7:
            logger.warning("Bolhas insuficientes — usando fallback de grade")
            return grid_fallback(thresh, num_questions, num_alternatives)

        # Ordenar de cima para baixo → agrupar por questão
        bubble_cnts = sorted(bubble_cnts, key=lambda c: cv2.boundingRect(c)[1])
        answers    = {}
        confidence = {}

        for q in range(num_questions):
            row_bubbles = bubble_cnts[q*num_alternatives:(q+1)*num_alternatives]
            q_str = str(q + 1)
            if len(row_bubbles) < num_alternatives:
                answers[q_str] = None; confidence[q_str] = 0.0; continue

            # Ordenar esquerda → direita = A, B, C, D, E
            row_bubbles = sorted(row_bubbles, key=lambda c: cv2.boundingRect(c)[0])
            fills = []
            for bubble in row_bubbles:
                mask = np.zeros(thresh.shape, dtype="uint8")
                cv2.drawContours(mask, [bubble], -1, 255, -1)
                fills.append(cv2.countNonZero(cv2.bitwise_and(thresh, thresh, mask=mask)))

            best_idx = int(np.argmax(fills))
            mask_a   = np.zeros(thresh.shape, dtype="uint8")
            cv2.drawContours(mask_a, [row_bubbles[best_idx]], -1, 255, -1)
            bubble_area = cv2.countNonZero(mask_a)
            fill_ratio  = fills[best_idx] / bubble_area if bubble_area > 0 else 0

            if fill_ratio > 0.28:
                answers[q_str]    = ALTERNATIVES[best_idx] if best_idx < len(ALTERNATIVES) else None
                confidence[q_str] = round(fill_ratio, 3)
            else:
                answers[q_str]    = None
                confidence[q_str] = 0.0

        return answers, confidence, None

    except Exception as e:
        logger.exception("Erro na detecção")
        return None, None, str(e)
```
