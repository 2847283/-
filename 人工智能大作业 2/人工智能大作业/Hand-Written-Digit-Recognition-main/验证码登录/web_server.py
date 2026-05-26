"""
验证码登录 + 手写数字识别 Web 服务端
启动: python web_server.py
"""
from __future__ import annotations

import base64
import io
import json
import os
import random
import sys
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SESSIONS: dict[str, dict] = {}
SESSION_TTL = 600

_backend = None
_backend_init_attempted = False

_digit_model = None
_digit_model_init_attempted = False


# ======================== captcha ========================

def _init_backend():
    global _backend, _backend_init_attempted
    if _backend_init_attempted:
        return
    _backend_init_attempted = True
    if os.environ.get("USE_ML_CAPTCHA", "").strip().lower() not in ("1", "true", "yes"):
        print("[INFO] 使用 PIL 简易验证码模式")
        return
    try:
        from captcha_backend import CaptchaLoginBackend
        _backend = CaptchaLoginBackend()
        print("[INFO] CNN 验证码后端模型加载成功")
    except FileNotFoundError as e:
        print(f"[WARNING] 模型文件不存在: {e}")
        print("[INFO] 将使用 PIL 简易验证码")
    except Exception as e:
        print(f"[WARNING] 后端加载失败: {e}")
        print("[INFO] 将使用 PIL 简易验证码")


def _get_backend():
    _init_backend()
    return _backend


def _is_backend_ready():
    return _backend is not None


def _init_digit_model():
    global _digit_model, _digit_model_init_attempted
    if _digit_model_init_attempted:
        return
    _digit_model_init_attempted = True
    model_dir = os.path.join(os.path.dirname(ROOT), "手写数字识别")
    model_path = os.path.join(model_dir, "cnn_model_v2.h5")
    if not os.path.isfile(model_path):
        print(f"[WARNING] 数字识别模型不存在: {model_path}")
        return
    try:
        import tensorflow as tf
        _digit_model = tf.keras.models.load_model(model_path)
        print("[INFO] 手写数字识别模型加载成功")
    except Exception as e:
        print(f"[WARNING] 数字识别模型加载失败: {e}")


def _get_digit_model():
    _init_digit_model()
    return _digit_model


def _clean_sessions():
    now = time.time()
    expired = [sid for sid, s in SESSIONS.items() if now - s.get("created", 0) > SESSION_TTL]
    for sid in expired:
        del SESSIONS[sid]


def _generate_simple_captcha():
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    code = "".join(str(random.randint(0, 9)) for _ in range(4))
    w, h = 448, 112
    img = Image.new("L", (w, h), color=240)
    draw = ImageDraw.Draw(img)

    for i in range(60):
        x1 = random.randint(0, w)
        y1 = random.randint(0, h)
        x2 = x1 + random.randint(-30, 30)
        y2 = y1 + random.randint(-30, 30)
        draw.line([(x1, y1), (x2, y2)], fill=random.randint(120, 200), width=1)

    for i in range(300):
        x = random.randint(0, w)
        y = random.randint(0, h)
        draw.point((x, y), fill=random.randint(80, 200))

    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except Exception:
        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 60)
        except Exception:
            font = ImageFont.load_default()

    char_w = w // len(code)
    for idx, ch in enumerate(code):
        x_offset = idx * char_w + random.randint(10, 30)
        y_offset = random.randint(10, 20)
        draw.text((x_offset, y_offset), ch, fill=random.randint(0, 60), font=font)

    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return code, b64, img


def _ml_captcha(be):
    img_np, gt, pred = be.new_challenge()
    from PIL import Image
    g = (np.clip(img_np[:, :, 0], 0, 1) * 255).astype(np.uint8)
    pil = Image.fromarray(g, mode="L").resize((448, 112), Image.Resampling.NEAREST)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return gt, b64, img_np


HTML_PATH = os.path.join(ROOT, "templates", "login.html")
if not os.path.exists(HTML_PATH):
    HTML_PATH = os.path.join(ROOT, "login.html")


class RequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def _check_auth(self) -> str:
        body = self._read_body()
        token = body.get("auth_token", "")
        session = SESSIONS.get(f"user_{token}")
        if not session or time.time() - session.get("created", 0) > SESSION_TTL:
            self._send_json({"success": False, "message": "登录已过期，请重新登录"}, 401)
            return ""
        return token

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/captcha":
            self._handle_get_captcha()
        elif self.path == "/api/health":
            self._send_json({
                "status": "ok",
                "captcha_ready": _is_backend_ready(),
                "digit_model_ready": _get_digit_model() is not None,
            })
        elif self.path in ("/", "/login", "/index.html"):
            self._serve_html()
        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        if self.path == "/api/send-code":
            self._handle_send_code()
        elif self.path == "/api/login":
            self._handle_login()
        elif self.path == "/api/digit-recognize":
            self._handle_digit_recognize()
        elif self.path == "/api/digit-recognize-multi":
            self._handle_digit_recognize_multi()
        else:
            self._send_json({"error": "Not Found"}, 404)

    # ---- serve HTML ----

    def _serve_html(self):
        try:
            with open(HTML_PATH, "r", encoding="utf-8") as f:
                html = f.read()
            body = html.encode()
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._send_json({"error": "HTML file not found"}, 500)

    # ---- captcha ----

    def _handle_get_captcha(self):
        _clean_sessions()
        sid = uuid.uuid4().hex
        be = _get_backend()

        if be is not None:
            try:
                gt, b64, img_np = _ml_captcha(be)
                SESSIONS[sid] = {
                    "ground_truth": gt, "image_np": img_np, "created": time.time(),
                }
                self._send_json({
                    "session_id": sid,
                    "captcha_image": f"data:image/png;base64,{b64}",
                    "code_length": 4,
                })
                return
            except Exception as e:
                print(f"[WARNING] CNN captcha failed: {e}")

        code, b64, _ = _generate_simple_captcha()
        SESSIONS[sid] = {"ground_truth": code, "captcha_code": code, "created": time.time()}
        self._send_json({
            "session_id": sid,
            "captcha_image": f"data:image/png;base64,{b64}",
            "code_length": 4,
        })

    # ---- SMS ----

    def _handle_send_code(self):
        body = self._read_body()
        contact = body.get("contact", "").strip()
        if not contact:
            self._send_json({"success": False, "message": "请输入手机号或邮箱"}, 400)
            return
        is_email = "@" in contact
        if is_email:
            if len(contact) > 100 or " " in contact:
                self._send_json({"success": False, "message": "邮箱格式不正确"}, 400)
                return
        else:
            digits_only = "".join(c for c in contact if c.isdigit())
            if len(digits_only) != 11:
                self._send_json({"success": False, "message": "请输入正确的11位手机号"}, 400)
                return

        rng = np.random.default_rng()
        code = "".join(str(rng.integers(0, 10)) for _ in range(6))
        sid = uuid.uuid4().hex
        SESSIONS[f"sms_{sid}"] = {
            "contact": contact, "sms_code": code, "created": time.time(), "attempts": 0,
        }
        print(f"[SMS] {contact}: {code}")
        self._send_json({
            "success": True, "session_id": sid,
            "message": f"验证码已发送至 {contact}", "demo_code": code,
        })

    # ---- login ----

    def _handle_login(self):
        body = self._read_body()
        contact = body.get("contact", "").strip()
        sms_code = body.get("sms_code", "").strip()
        captcha_input = body.get("captcha_input", "").strip()
        sms_sid = body.get("sms_session_id", "")
        captcha_sid = body.get("captcha_session_id", "")

        if not contact:
            self._send_json({"success": False, "message": "请输入手机号或邮箱"}, 400)
            return
        if not sms_code:
            self._send_json({"success": False, "message": "请输入短信验证码"}, 400)
            return
        if not captcha_input:
            self._send_json({"success": False, "message": "请输入图形验证码"}, 400)
            return

        sms_session = SESSIONS.get(f"sms_{sms_sid}") if sms_sid else None
        if sms_session:
            sms_session["attempts"] = sms_session.get("attempts", 0) + 1
            if sms_session["attempts"] > 5:
                self._send_json({"success": False, "message": "验证次数过多，请重新获取验证码"}, 429)
                return
            if sms_code != sms_session.get("sms_code", ""):
                self._send_json({"success": False, "message": "短信验证码错误"}, 401)
                return
        else:
            if sms_code != "123456":
                self._send_json({"success": False, "message": "短信验证码错误或已过期"}, 401)
                return

        captcha_session = SESSIONS.get(captcha_sid) if captcha_sid else None
        if not captcha_session:
            self._send_json({"success": False, "message": "图形验证码已过期，请刷新重试"}, 400)
            return
        if captcha_input != captcha_session.get("ground_truth", ""):
            self._send_json({"success": False, "message": "图形验证码错误，请重新输入"}, 401)
            return

        user_token = uuid.uuid4().hex
        SESSIONS[f"user_{user_token}"] = {
            "contact": contact, "created": time.time(),
        }
        self._send_json({
            "success": True, "auth_token": user_token,
            "message": f"登录成功！欢迎 {contact}",
        })

    # ---- digit recognition ----

    def _decode_image_to_rgb(self, b64_data):
        if b64_data.startswith("data:"):
            b64_data = b64_data.split(",", 1)[1]
        raw_bytes = base64.b64decode(b64_data)
        from PIL import Image
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.paste(img, (0, 0), img)
        return bg.convert("RGB")

    def _preprocess_single(self, img_np):
        import tensorflow as tf
        img_np = tf.image.rgb_to_grayscale(img_np)
        img_np = tf.image.resize(img_np, [28, 28])
        img_np = 255 - img_np
        img_np = img_np / 255.0
        return img_np.numpy().reshape(1, 28, 28, 1)

    def _predict_batch(self, model, batch):
        import tensorflow as tf
        predictions = model.predict(batch, verbose=0)
        probs = tf.nn.softmax(predictions, axis=1).numpy()
        results = []
        for p in probs:
            top3_idx = np.argsort(p)[::-1][:3]
            results.append({
                "digit": int(top3_idx[0]),
                "confidence": round(float(p[top3_idx[0]]) * 100, 1),
                "probabilities": {str(i): round(float(p[i]) * 100, 1) for i in range(10)},
                "top3": [{"digit": int(i), "prob": round(float(p[i]) * 100, 1)} for i in top3_idx],
            })
        return results

    def _handle_digit_recognize(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._send_json({"success": False, "message": "请求体为空"}, 400)
            return
        body = json.loads(self.rfile.read(length))

        token = body.get("auth_token", "")
        session = SESSIONS.get(f"user_{token}")
        if not session or time.time() - session.get("created", 0) > SESSION_TTL:
            self._send_json({"success": False, "message": "登录已过期，请重新登录"}, 401)
            return

        model = _get_digit_model()
        if model is None:
            self._send_json({"success": False, "message": "识别模型未就绪"}, 503)
            return

        b64_data = body.get("image", "")
        if not b64_data:
            self._send_json({"success": False, "message": "请提供手写图像"}, 400)
            return

        try:
            img = self._decode_image_to_rgb(b64_data)
            img_np = np.array(img, dtype=np.float32)
            batch = self._preprocess_single(img_np)
            results = self._predict_batch(model, batch)
            r = results[0]
            self._send_json({
                "success": True,
                "predicted_digit": r["digit"],
                "confidence": r["confidence"],
                "probabilities": r["probabilities"],
                "top3": r["top3"],
                "mode": "single",
            })
        except Exception as e:
            print(f"[ERROR] digit recognition: {e}")
            self._send_json({"success": False, "message": f"识别失败: {str(e)}"}, 500)

    def _handle_digit_recognize_multi(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._send_json({"success": False, "message": "请求体为空"}, 400)
            return
        body = json.loads(self.rfile.read(length))

        token = body.get("auth_token", "")
        session = SESSIONS.get(f"user_{token}")
        if not session or time.time() - session.get("created", 0) > SESSION_TTL:
            self._send_json({"success": False, "message": "登录已过期，请重新登录"}, 401)
            return

        model = _get_digit_model()
        if model is None:
            self._send_json({"success": False, "message": "识别模型未就绪"}, 503)
            return

        b64_data = body.get("image", "")
        if not b64_data:
            self._send_json({"success": False, "message": "请提供手写图像"}, 400)
            return

        try:
            import cv2
            from PIL import Image
            import tensorflow as tf

            img = self._decode_image_to_rgb(b64_data)
            img_np = np.array(img)
            h, w = img_np.shape[:2]

            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            digit_regions = []
            min_area = (w * h) * 0.005
            for cnt in contours:
                x, y, bw, bh = cv2.boundingRect(cnt)
                area = bw * bh
                aspect = bh / max(bw, 1)
                if area < min_area:
                    continue
                if bw > w * 0.9 and bh > h * 0.9:
                    continue
                if aspect > 8 or aspect < 0.12:
                    continue
                margin = max(4, int(min(bw, bh) * 0.25))
                x1 = max(0, x - margin)
                y1 = max(0, y - margin)
                x2 = min(w, x + bw + margin)
                y2 = min(h, y + bh + margin)
                digit_regions.append((x1, y1, x2, y2))

            digit_regions.sort(key=lambda r: r[0])

            if len(digit_regions) == 0:
                self._send_json({
                    "success": True,
                    "sequence": "",
                    "digits": [],
                    "message": "未检测到数字，请确保书写清晰",
                    "mode": "multi",
                })
                return

            crops = []
            for x1, y1, x2, y2 in digit_regions:
                crop = binary[y1:y2, x1:x2]
                crop_rgb = cv2.cvtColor(crop, cv2.COLOR_GRAY2RGB)
                crop_rgb = np.array(crop_rgb, dtype=np.float32)
                crop_rgb = 255 - crop_rgb
                batch_item = self._preprocess_single(crop_rgb)
                crops.append(batch_item[0])

            batch = np.stack(crops, axis=0)
            results = self._predict_batch(model, batch)

            sequence = "".join(str(r["digit"]) for r in results)

            self._send_json({
                "success": True,
                "sequence": sequence,
                "digits": results,
                "count": len(results),
                "positions": [{"x1": r[0], "y1": r[1], "x2": r[2], "y2": r[3]} for r in digit_regions],
                "mode": "multi",
            })
        except Exception as e:
            print(f"[ERROR] multi-digit recognition: {e}")
            self._send_json({"success": False, "message": f"多数字识别失败: {str(e)}"}, 500)


def main():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), RequestHandler)
    print(f"服务已启动: http://localhost:{port}")
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()
