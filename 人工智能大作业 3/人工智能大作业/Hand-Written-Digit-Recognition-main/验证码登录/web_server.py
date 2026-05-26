"""
验证码图片选择验证 + 手写数字识别 Web 服务端
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


def _bezier_point(pts, t):
    mt = 1 - t
    x = mt**3 * pts[0][0] + 3 * mt**2 * t * pts[1][0] + 3 * mt * t**2 * pts[2][0] + t**3 * pts[3][0]
    y = mt**3 * pts[0][1] + 3 * mt**2 * t * pts[1][1] + 3 * mt * t**2 * pts[2][1] + t**3 * pts[3][1]
    return x, y


def _apply_wave_distortion(img_array, seed):
    rng = np.random.default_rng(seed)
    h, w = img_array.shape[:2]
    amp_x = float(rng.uniform(2.5, 6.0))
    amp_y = float(rng.uniform(2.5, 5.5))
    freq = float(rng.uniform(0.012, 0.030))
    p1 = float(rng.uniform(0, 2 * np.pi))
    p2 = float(rng.uniform(0, 2 * np.pi))
    p3 = float(rng.uniform(0, 2 * np.pi))
    p4 = float(rng.uniform(0, 2 * np.pi))

    y_idx, x_idx = np.meshgrid(np.arange(h, dtype=np.float32),
                               np.arange(w, dtype=np.float32), indexing='ij')

    x_map = x_idx + amp_x * np.sin(2 * np.pi * y_idx * freq + p1) \
            + amp_x * 0.35 * np.sin(2 * np.pi * y_idx * freq * 2.7 + p2)
    y_map = y_idx + amp_y * np.cos(2 * np.pi * x_idx * freq * 1.4 + p3) \
            + amp_y * 0.35 * np.cos(2 * np.pi * x_idx * freq * 2.3 + p4)

    x_map = np.clip(x_map, 0, w - 1)
    y_map = np.clip(y_map, 0, h - 1)

    x0 = np.floor(x_map).astype(np.int32)
    y0 = np.floor(y_map).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1).astype(np.int32)
    y1 = np.minimum(y0 + 1, h - 1).astype(np.int32)

    wx = x_map - x0.astype(np.float32)
    wy = y_map - y0.astype(np.float32)

    img_f = img_array.astype(np.float32)
    if len(img_array.shape) == 3:
        result = np.zeros_like(img_f)
        for c in range(3):
            i00 = img_f[y0, x0, c]
            i01 = img_f[y0, x1, c]
            i10 = img_f[y1, x0, c]
            i11 = img_f[y1, x1, c]
            result[:, :, c] = ((1 - wx) * (1 - wy) * i00 + wx * (1 - wy) * i01 +
                               (1 - wx) * wy * i10 + wx * wy * i11)
    else:
        i00 = img_f[y0, x0]
        i01 = img_f[y0, x1]
        i10 = img_f[y1, x0]
        i11 = img_f[y1, x1]
        result = ((1 - wx) * (1 - wy) * i00 + wx * (1 - wy) * i01 +
                  (1 - wx) * wy * i10 + wx * wy * i11)

    return np.clip(result, 0, 255).astype(np.uint8)


def _generate_enhanced_captcha():
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    code = "".join(str(random.randint(0, 9)) for _ in range(4))
    w, h = 448, 112
    seed = random.randint(0, 2**31 - 1)
    rng = random.Random(seed)

    # ---- high-contrast multi-color palettes ----
    text_palettes = [
        [(220, 35, 35), (25, 75, 200), (210, 110, 0), (25, 165, 65)],
        [(185, 20, 105), (20, 145, 145), (145, 35, 185), (20, 105, 45)],
        [(205, 55, 20), (20, 55, 185), (165, 20, 125), (20, 155, 85)],
        [(30, 35, 185), (190, 35, 30), (20, 135, 45), (165, 75, 20)],
        [(175, 20, 30), (20, 105, 175), (175, 90, 20), (20, 145, 95)],
        [(195, 50, 40), (40, 40, 195), (25, 160, 70), (180, 30, 120)],
    ]
    colors = list(rng.choice(text_palettes))
    rng.shuffle(colors)

    # ---- random background gradient ----
    bg_img = Image.new('RGB', (w, h))
    bg_draw = ImageDraw.Draw(bg_img)
    for y_px in range(h):
        ratio = y_px / h
        rr = int(230 + 20 * ratio + rng.randint(-8, 8))
        gr = int(230 + 18 * ratio + rng.randint(-8, 8))
        br = int(228 + 22 * ratio + rng.randint(-8, 8))
        bg_draw.line([(0, y_px), (w, y_px)], fill=(max(0, min(255, rr)),
                     max(0, min(255, gr)), max(0, min(255, br))))

    # ---- background grid lines ----
    bg_draw = ImageDraw.Draw(bg_img)
    for _ in range(rng.randint(10, 18)):
        x1 = rng.randint(0, w)
        y1 = rng.randint(0, h)
        x2 = x1 + rng.randint(-80, 80)
        y2 = y1 + rng.randint(-80, 80)
        shade = rng.randint(15, 45)
        bg_draw.line([(x1, y1), (x2, y2)], fill=(210 - shade, 210 - shade, 208 - shade),
                     width=rng.randint(1, 2))

    # ---- background dot pattern ----
    for _ in range(rng.randint(200, 400)):
        px = rng.randint(0, w - 1)
        py = rng.randint(0, h - 1)
        sd = rng.randint(5, 40)
        bg_draw.point((px, py), fill=(235 - sd, 235 - sd, 233 - sd))

    # ---- load font ----
    font_size = rng.randint(50, 64)
    font = None
    for fname in ("arial.ttf", "C:\\Windows\\Fonts\\arial.ttf",
                  "C:\\Windows\\Fonts\\consola.ttf", "C:\\Windows\\Fonts\\segoeui.ttf"):
        try:
            font = ImageFont.truetype(fname, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    # ---- per-character rendering with individual transforms ----
    char_layers = []
    char_slot_w = w // len(code) + 20
    for idx, ch in enumerate(code):
        c_img = Image.new('RGBA', (char_slot_w + 40, h + 50), (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(c_img)
        x_off = rng.randint(6, 28)
        y_off = rng.randint(10, 35)
        c_draw.text((x_off, y_off), ch, fill=colors[idx], font=font)
        angle = rng.uniform(-22, 22)
        c_img = c_img.rotate(angle, expand=True, resample=Image.BICUBIC,
                             fillcolor=(0, 0, 0, 0))
        char_layers.append(c_img)

    # ---- composite characters onto text layer ----
    text_layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    overlap = rng.randint(5, 18)
    for idx, c_img in enumerate(char_layers):
        base_x = idx * (w // len(code)) - overlap
        base_y = rng.randint(-20, -5)
        text_layer.paste(c_img, (base_x, base_y), c_img)

    # ---- merge text onto background ----
    text_arr = np.array(text_layer.convert('RGB'))
    bg_arr = np.array(bg_img)
    alpha = np.array(text_layer)[:, :, 3].astype(np.float32) / 255.0
    alpha = np.expand_dims(alpha, axis=2)
    merged = (text_arr.astype(np.float32) * alpha +
              bg_arr.astype(np.float32) * (1 - alpha)).astype(np.uint8)

    # ---- wave distortion ----
    merged = _apply_wave_distortion(merged, seed)
    distorted = Image.fromarray(merged)
    draw = ImageDraw.Draw(distorted)

    # ---- bezier interference curves ----
    for _ in range(rng.randint(3, 7)):
        pts = [(rng.randint(0, w), rng.randint(0, h)) for _ in range(4)]
        curve_color = (rng.randint(60, 190), rng.randint(60, 190), rng.randint(60, 190))
        curve_w = rng.randint(1, 3)
        segments = 50
        for j in range(segments):
            t0 = j / segments
            t1 = (j + 1) / segments
            x0, y0 = _bezier_point(pts, t0)
            x1, y1 = _bezier_point(pts, t1)
            draw.line([(x0, y0), (x1, y1)], fill=curve_color, width=curve_w)

    # ---- arc / ellipse interference ----
    for _ in range(rng.randint(2, 5)):
        ax = rng.randint(20, w - 100)
        ay = rng.randint(10, h - 70)
        arx = rng.randint(18, 70)
        ary = rng.randint(8, 30)
        arc_col = (rng.randint(50, 160), rng.randint(50, 160), rng.randint(50, 160))
        arc_start = rng.randint(0, 180)
        arc_end = rng.randint(180, 360)
        draw.arc([ax, ay, ax + arx, ay + ary], arc_start, arc_end,
                 fill=arc_col, width=rng.randint(1, 3))

    # ---- dense point noise ----
    for _ in range(rng.randint(250, 500)):
        nx = rng.randint(0, w - 1)
        ny = rng.randint(0, h - 1)
        dn = rng.randint(0, 200)
        draw.point((nx, ny), fill=(dn, dn, dn))

    # ---- short random line noise ----
    for _ in range(rng.randint(12, 30)):
        lx1 = rng.randint(0, w - 1)
        ly1 = rng.randint(0, h - 1)
        lx2 = min(lx1 + rng.randint(-25, 25), w - 1)
        ly2 = min(ly1 + rng.randint(-25, 25), h - 1)
        ln = rng.randint(50, 180)
        draw.line([(lx1, ly1), (lx2, ly2)], fill=(ln, ln, ln),
                  width=rng.randint(1, 2))

    # ---- small rectangle / shape noise ----
    for _ in range(rng.randint(3, 8)):
        rx = rng.randint(5, w - 30)
        ry = rng.randint(5, h - 20)
        rw = rng.randint(6, 20)
        rh = rng.randint(3, 10)
        rn = rng.randint(40, 170)
        draw.rectangle([rx, ry, rx + rw, ry + rh], outline=(rn, rn, rn),
                       width=rng.randint(1, 2))

    # ---- Gaussian blur for edge softening ----
    blur_radius = rng.uniform(0.5, 1.3)
    distorted = distorted.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    buf = io.BytesIO()
    distorted.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return code, b64


def _ml_captcha(be):
    img_np, gt, pred = be.new_challenge()
    from PIL import Image
    g = (np.clip(img_np[:, :, 0], 0, 1) * 255).astype(np.uint8)
    pil = Image.fromarray(g, mode="L").resize((448, 112), Image.Resampling.NEAREST)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return gt, b64


def _generate_one_captcha():
    be = _get_backend()
    if be is not None:
        try:
            gt, b64 = _ml_captcha(be)
            return gt, b64
        except Exception as e:
            print(f"[WARNING] CNN captcha failed: {e}")
    gt, b64 = _generate_enhanced_captcha()
    return gt, b64


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

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/captcha-challenge":
            self._handle_captcha_challenge()
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
        if self.path == "/api/captcha-challenge":
            self._handle_captcha_challenge()
        elif self.path == "/api/verify-captcha":
            self._handle_verify_captcha()
        elif self.path == "/api/digit-recognize":
            self._handle_digit_recognize()
        elif self.path == "/api/digit-recognize-multi":
            self._handle_digit_recognize_multi()
        else:
            self._send_json({"error": "Not Found"}, 404)

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

    def _handle_captcha_challenge(self):
        _clean_sessions()
        sid = uuid.uuid4().hex
        rng = np.random.default_rng()

        images = []
        ground_truths = []

        for _ in range(4):
            gt, b64 = _generate_one_captcha()
            images.append(f"data:image/png;base64,{b64}")
            ground_truths.append(gt)

        target_index = int(rng.integers(0, 4))
        target_code = ground_truths[target_index]

        SESSIONS[sid] = {
            "ground_truths": ground_truths,
            "target_index": target_index,
            "target_code": target_code,
            "created": time.time(),
            "attempts": 0,
        }

        self._send_json({
            "session_id": sid,
            "images": images,
            "target_code": target_code,
        })

    def _handle_verify_captcha(self):
        body = self._read_body()
        sid = body.get("session_id", "")
        selected = body.get("selected", -1)

        session = SESSIONS.get(sid)
        if not session:
            self._send_json({"success": False, "message": "验证已过期，请刷新重试"}, 400)
            return

        session["attempts"] = session.get("attempts", 0) + 1
        if session["attempts"] > 5:
            del SESSIONS[sid]
            self._send_json({"success": False, "message": "尝试次数过多，请刷新重试"}, 429)
            return

        if not isinstance(selected, int) or selected < 1 or selected > 4:
            self._send_json({"success": False, "message": "请选择有效的图片编号（1-4）"}, 400)
            return

        if session["ground_truths"][selected - 1] == session["target_code"]:
            user_token = uuid.uuid4().hex
            SESSIONS[f"user_{user_token}"] = {
                "contact": "验证通过", "created": time.time(),
            }
            del SESSIONS[sid]
            self._send_json({
                "success": True,
                "auth_token": user_token,
                "message": "验证通过！",
            })
        else:
            self._send_json({
                "success": False,
                "message": "验证失败，您选择的图片不包含目标数字，请重新尝试",
            })

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
