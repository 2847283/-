# 验证码 CNN 识别增强 & 前端识别结果展示

**日期**: 2026-06-02  
**状态**: 已批准

---

## 目标

1. 增强合成训练集的扭曲参数，重新训练 `captcha_digit_cnn.h5`，使模型能识别更强扭曲的验证码
2. Web 端 PIL 验证码去除非线性波纹扭曲，让字符保持几何完整性
3. Web 前端登录页面在 4 张验证码图片下方显示 CNN 识别结果

---

## 整体架构

```
captcha_synth.py (增强扭曲参数)
       │ 重新生成训练数据
       ▼
train_captcha_cnn.py (增强 datagen) → captcha_digit_cnn.h5 (新版)
       │                                      │
       │                                      ▼
web_server.py (去掉波纹扭曲)  ←──  captcha_backend.predict_code (逐张识别)
       │ /api/captcha-challenge
       │ JSON: {images, predictions[], target_code}
       ▼
login.html (每张图下方显示 CNN 识别数字)
```

---

## 改动清单

### 1. `captcha_synth.py` — 增强扭曲参数

**涉及函数**: `_blur_and_noise()` (L65-74)、`one_captcha_image()` (L77-103)

| 参数 | 现值 | 新值 |
|------|------|------|
| 旋转角 `angle` | ±15° | ±30° |
| 高斯模糊 σ | 0.6~1.4 | 1.0~2.5 |
| 噪声 σ | 0.03~0.08 | 0.05~0.15 |
| 对比度缩放 `c` | 0.85~1.15 | 0.55~1.55 |
| 亮度偏移 (新增) | 无 | 添加 `offset ∈ ±0.25`，`clip((img-mean)*c + mean + offset, 0, 1)` |
| 膨胀/腐蚀 (新增) | 无 | 随机应用 morphological dilation/erosion |

**依赖**: scipy.ndimage 已有

---

### 2. `data/build_captcha_dataset.py` — 重新生成数据集

运行此脚本重新生成 `data/captcha_dataset.npz`。

---

### 3. `train_captcha_cnn.py` — 增强 datagen 参数

| 参数 | 现值 | 新值 |
|------|------|------|
| `rotation_range` | 12 | 25 |
| `width_shift_range` | 0.12 | 0.20 |
| `height_shift_range` | 0.12 | 0.20 |
| `zoom_range` | 0.12 | 0.18 |

模型架构不变。重新训练后输出新的 `captcha_digit_cnn.h5`。

---

### 4. `web_server.py` — 去掉波纹扭曲 + 返回 CNN 预测

**改动 4a**: `_generate_enhanced_captcha()` 中移除 `_apply_wave_distortion()` 调用

**改动 4b**: `_handle_captcha_challenge()` 中，对每张生成的验证码图：
- 将 PIL 彩色图转为灰度，缩放至 28×112
- 调用 `captcha_backend.CaptchaLoginBackend.predict_code()` 进行识别
- 在 API 响应 JSON 中添加 `predictions` 数组

```json
{
  "session_id": "...",
  "images": [...],
  "predictions": ["1234", "5678", "9012", "3456"],
  "target_code": "5678"
}
```

---

### 5. `login.html` — 前端展示识别结果

在每个 `.captcha-item` 的 `<img>` 后添加 CNN 识别文本行：

```html
<div class="cnn-prediction">CNN识别: 1234</div>
```

样式：居中、font-size 12px、color `var(--gray-500)`、padding-top 4px。

JavaScript 从 API 响应的 `predictions` 数组中读取对应值，设置到对应 DOM 元素。

---

## 数据流

```
用户刷新验证码
  → fetch /api/captcha-challenge
    → 后端循环 4 次生成验证码 (PIL, 无波纹扭曲)
    → 每张图调用 CNN 模型 predict_code()
    → 返回 {images, predictions, target_code}
  → 前端渲染 4 张图 + 每张下方 CNN预测文本
  → 用户选择一张 → 验证登录
```

---

## 验收标准

1. CNN 模型在新增强数据集上训练完成，验证准确率 ≥ 85%
2. PIL 生成的验证码无波纹扭曲，字符轮廓完整
3. Web 前端 4 张验证码图片下方均正确显示 CNN 识别结果
4. 登录验证流程正常工作
