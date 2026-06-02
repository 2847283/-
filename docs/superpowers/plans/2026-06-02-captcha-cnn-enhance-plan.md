# 验证码 CNN 识别增强 & 前端识别结果展示 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强合成训练集扭曲参数重训 CNN，Web 端去掉波纹扭曲，前端 4 张验证码图片下方显示 CNN 识别结果

**Architecture:** 修改 captcha_synth.py 增强扭曲参数 → 重新生成数据集 → 增强 train datagen 并重训模型 → 修改 web_server 去掉波纹扭曲并在 API 返回 CNN 预测 → 修改前端展示识别文本

**Tech Stack:** Python 3.12, TensorFlow/Keras, NumPy, scipy, PIL, 原生 JavaScript (无框架)

---

## 文件结构

| 文件 | 角色 | 操作 |
|------|------|------|
| `验证码登录/captcha_synth.py` | 合成扭曲验证码、生成单张图/切分单字 | **修改** |
| `data/build_captcha_dataset.py` | 批量调用 captcha_synth 生成训练数据集 | 不改 (重运行) |
| `验证码登录/train_captcha_cnn.py` | 加载数据集、构建+训练 CNN、保存 .h5 | **修改** |
| `验证码登录/web_server.py` | Web 服务端、生成验证码、验证登录 | **修改** |
| `验证码登录/templates/login.html` | 前端页面、展示验证码、用户交互 | **修改** |
| `验证码登录/captcha_backend.py` | CNN 推理后端（预测四连数字） | 不改 |
| `data/captcha_dataset.npz` | 训练/测试数据集 | 重生成 |
| `验证码登录/captcha_digit_cnn.h5` | 训练好的模型权重 | 重生成 |

**接口约定:**
- `captcha_synth._blur_and_noise(img, rng) → np.ndarray` — 返回值 shape 不变 (28,28)
- `captcha_synth.one_captcha_image(x_pool, y_pool, rng) → (img, code, digs)` — 返回值签名不变
- `web_server._generate_enhanced_captcha() → (code, b64)` — 返回值签名不变
- `_handle_captcha_challenge()` 响应 JSON 新增 `predictions` 字段: `string[4]`
- 前端从 `data.predictions[i]` 读取第 i 张图的 CNN 识别结果

---

## Task 1: 增强 captcha_synth.py 扭曲参数

**Files:**
- Modify: `验证码登录/captcha_synth.py:65-103`

- [ ] **Step 1: 修改 `_blur_and_noise()` 函数**

将 [L65-L74](file:///e:/过去作业/人工智能创新实践/大作业/人工智能大作业%203/人工智能大作业/Hand-Written-Digit-Recognition-main/验证码登录/captcha_synth.py#L65-L74) 替换为：

```python
def _blur_and_noise(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    from scipy import ndimage

    sigma = rng.uniform(1.0, 2.5)
    blurred = ndimage.gaussian_filter(img.astype(np.float64), sigma=sigma).astype(np.float32)
    noise = rng.normal(0, rng.uniform(0.05, 0.15), blurred.shape).astype(np.float32)
    out = np.clip(blurred + noise, 0.0, 1.0)
    c = rng.uniform(0.55, 1.55)
    offset = rng.uniform(-0.25, 0.25)
    mean_val = float(np.mean(out))
    out = np.clip((out - mean_val) * c + mean_val + offset, 0.0, 1.0)

    if rng.random() < 0.3:
        se_size = int(rng.integers(1, 3))
        se = np.ones((se_size, se_size))
        if rng.random() < 0.5:
            out = ndimage.grey_dilation(out, footprint=se)
        else:
            out = ndimage.grey_erosion(out, footprint=se)
        out = np.clip(out, 0.0, 1.0)

    return out
```

- [ ] **Step 2: 修改 `one_captcha_image()` 中的旋转角**

将 [L94](file:///e:/过去作业/人工智能创新实践/大作业/人工智能大作业%203/人工智能大作业/Hand-Written-Digit-Recognition-main/验证码登录/captcha_synth.py#L94) 的 `angle = rng.uniform(-15, 15)` 改为：

```python
        angle = rng.uniform(-30, 30)
```

- [ ] **Step 3: 验证快速合成测试**

运行以下命令，确认增强后的合成图生成正常（只合成 4 张不报错）：

```powershell
cd "e:\过去作业\人工智能创新实践\大作业\人工智能大作业 3\人工智能大作业\Hand-Written-Digit-Recognition-main"
.\.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, '验证码登录')
from captcha_synth import load_mnist_digits, one_captcha_image
import numpy as np
x, y = load_mnist_digits()
rng = np.random.default_rng(42)
for i in range(4):
    img, code, digs = one_captcha_image(x, y, rng)
    print(f'[{i}] code={code}, digits={digs}, img_shape={img.shape}')
print('OK')
"
```

Expected: 打印 4 行验证码文本和 shape 信息，无报错。

---

## Task 2: 重新生成训练数据集

**Files:**
- Regenerate: `data/captcha_dataset.npz`

- [ ] **Step 1: 删除旧数据集**

```powershell
cd "e:\过去作业\人工智能创新实践\大作业\人工智能大作业 3\人工智能大作业\Hand-Written-Digit-Recognition-main"
Remove-Item -Force "data\captcha_dataset.npz" -ErrorAction SilentlyContinue
```

- [ ] **Step 2: 运行 build_captcha_dataset.py 生成新数据集**

```powershell
cd "e:\过去作业\人工智能创新实践\大作业\人工智能大作业 3\人工智能大作业\Hand-Written-Digit-Recognition-main"
.\.venv\Scripts\python.exe data/build_captcha_dataset.py --n-train 24000 --n-test 4000 --seed 42
```

Expected: 输出 "已保存: ...data\captcha_dataset.npz" 及数据集规模信息。

---

## Task 3: 增强 train_captcha_cnn.py 并重训模型

**Files:**
- Modify: `验证码登录/train_captcha_cnn.py`

- [ ] **Step 1: 修正数据路径**

将 [L14](file:///e:/过去作业/人工智能创新实践/大作业/人工智能大作业%203/人工智能大作业/Hand-Written-Digit-Recognition-main/验证码登录/train_captcha_cnn.py#L14) 的 `DATA_PATH` 改为正确的路径（data/ 在项目根目录下，而非 验证码登录/ 下）：

```python
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(os.path.dirname(ROOT), "data", "captcha_dataset.npz")
```

- [ ] **Step 2: 增强 ImageDataGenerator 参数**

将 [L58-L63](file:///e:/过去作业/人工智能创新实践/大作业/人工智能大作业%203/人工智能大作业/Hand-Written-Digit-Recognition-main/验证码登录/train_captcha_cnn.py#L58-L63) 替换为：

```python
    datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        rotation_range=25,
        width_shift_range=0.20,
        height_shift_range=0.20,
        zoom_range=0.18,
    )
```

- [ ] **Step 3: 运行训练脚本**

```powershell
cd "e:\过去作业\人工智能创新实践\大作业\人工智能大作业 3\人工智能大作业\Hand-Written-Digit-Recognition-main"
.\.venv\Scripts\python.exe 验证码登录/train_captcha_cnn.py
```

Expected: 训练过程输出 epoch 进度条，最终 "已保存模型: ...验证码登录\captcha_digit_cnn.h5"，val_accuracy ≥ 85%。

---

## Task 4: 修改 web_server.py — 去掉波纹扭曲 + 返回 CNN 预测

**Files:**
- Modify: `验证码登录/web_server.py`

- [ ] **Step 1: 在 `_generate_enhanced_captcha()` 中删除波纹扭曲调用**

找到 [L244-L245](file:///e:/过去作业/人工智能创新实践/大作业/人工智能大作业%203/人工智能大作业/Hand-Written-Digit-Recognition-main/验证码登录/web_server.py#L244-L245) 附近的 `_apply_wave_distortion` 调用并删除：

```python
    # 删除这两行:
    # merged = _apply_wave_distortion(merged, seed)
    # distorted = Image.fromarray(merged)
    
    # 替换为:
    distorted = Image.fromarray(merged)
```

具体做法：将 L244-L246：
```python
    # ---- wave distortion ----
    merged = _apply_wave_distortion(merged, seed)
    distorted = Image.fromarray(merged)
```

改为：
```python
    distorted = Image.fromarray(merged)
```

- [ ] **Step 2: 在 `_handle_captcha_challenge()` 中添加 CNN 预测**

找到 `_handle_captcha_challenge()` 方法（L402-L430）。在生成 4 张图片的同时，对每张图转灰度 → 缩放到 28×112 → 调用 CNN 预测。

将 L407-L414：
```python
        for _ in range(4):
            gt, b64 = _generate_one_captcha()
            images.append(f"data:image/png;base64,{b64}")
            ground_truths.append(gt)
```

改为：
```python
        predictions = []
        for _ in range(4):
            gt, b64 = _generate_one_captcha()
            images.append(f"data:image/png;base64,{b64}")
            ground_truths.append(gt)

            import base64 as _b64
            from PIL import Image as _PILImage
            raw_bytes = _b64.b64decode(b64)
            pil_img = _PILImage.open(io.BytesIO(raw_bytes)).convert("L")
            pil_img = pil_img.resize((112, 28), _PILImage.Resampling.LANCZOS)
            img_np = np.array(pil_img, dtype=np.float32) / 255.0
            img_np = img_np.reshape(28, 112, 1)

            be = _get_backend()
            if be is not None:
                try:
                    pred = be.predict_code(img_np)
                except Exception:
                    pred = ""
            else:
                pred = ""
            predictions.append(pred)
```

然后修改 L426-L430 的 `_send_json` 调用，在响应中添加 `predictions`：

```python
        self._send_json({
            "session_id": sid,
            "images": images,
            "predictions": predictions,
            "target_code": target_code,
        })
```

- [ ] **Step 3: 启动服务验证**

```powershell
cd "e:\过去作业\人工智能创新实践\大作业\人工智能大作业 3\人工智能大作业\Hand-Written-Digit-Recognition-main"
.\.venv\Scripts\python.exe 验证码登录/web_server.py
```

用浏览器访问 `http://localhost:5000`，打开开发者工具 Network 面板，刷新验证码，检查 `/api/captcha-challenge` 响应中是否包含 `predictions` 数组，且数组有 4 个字符串元素。

---

## Task 5: 修改 login.html 前端展示 CNN 识别结果

**Files:**
- Modify: `验证码登录/templates/login.html`

- [ ] **Step 1: 添加 CSS 样式**

在 `</style>` 之前（L649 前）添加：

```css
.cnn-prediction{
  text-align:center;
  font-size:12px;
  color:var(--gray-500);
  padding:4px 0 6px;
  font-weight:500;
  letter-spacing:1px;
}
```

- [ ] **Step 2: 在 HTML 模板中为每张验证码图添加预测文本容器**

为 4 个 `.captcha-item` 的 `<img>` 后分别添加 `<div class="cnn-prediction">`：

```html
<div class="captcha-item" data-index="1" onclick="selectCaptcha(1)">
  <span class="captcha-number">1</span>
  <span class="check-mark">...</span>
  <img src="" alt="验证码 1" id="captchaImg1">
  <div class="cnn-prediction" id="cnnPred1"></div>
</div>
```

同样为 index 2、3、4 的 `.captcha-item` 添加对应的 `cnnPred2`、`cnnPred3`、`cnnPred4`。

- [ ] **Step 3: 在 JavaScript 中渲染 CNN 预测文本**

修改 `refreshChallenge()` 函数中设置图片 src 的循环（约 L857-L859 附近）：

```javascript
      for (var i = 0; i < data.images.length; i++) {
        $('captchaImg' + (i + 1)).src = data.images[i];
      }
```

改为：

```javascript
      for (var i = 0; i < data.images.length; i++) {
        $('captchaImg' + (i + 1)).src = data.images[i];
      }
      if (data.predictions) {
        for (var i = 0; i < data.predictions.length; i++) {
          var predEl = $('cnnPred' + (i + 1));
          if (predEl) {
            predEl.textContent = 'CNN识别: ' + (data.predictions[i] || '----');
          }
        }
      } else {
        for (var i = 1; i <= 4; i++) {
          var predEl = $('cnnPred' + i);
          if (predEl) predEl.textContent = '';
        }
      }
```

- [ ] **Step 4: 浏览器验证**

刷新 `http://localhost:5000`，检查：
1. 4 张验证码图片下方是否各有一行灰色文本"CNN识别: XXXX"
2. 点击"换一组验证码"后预测文本是否同步更新
3. 整个登录验证流程是否正常

---

## 执行顺序依赖

```
Task 1 (captcha_synth.py) ──→ Task 2 (生成数据集) ──→ Task 3 (训练模型)
                                                           │
Task 4 (web_server.py) ←───────────────────────────────────┘
       │
       ▼
Task 5 (login.html)
```

Task 4 依赖 Task 3 训练出的新模型。Task 5 依赖 Task 4 返回的新 JSON 字段。
