# 手写数字识别与验证码安全系统

## 项目概述

本项目是一个集**手写数字识别**与**高安全性验证码校验**于一体的综合性人工智能实践系统。系统包含两个核心子系统：

1. **验证码图片选择验证系统**：通过生成高复杂度验证码图片并采用"图片选择"验证机制，在保证用户体验的同时有效抵御自动化机器人攻击。
2. **手写数字识别系统**：基于卷积神经网络（CNN），支持用户在 Web 画板上手写数字，实时返回 Top-3 概率预测结果。

项目完整实现了从数据准备、模型训练到 Web 部署的全流程，可作为人工智能课程设计或验证码安全研究的参考实现。

---

## 目录结构

```
Hand-Written-Digit-Recognition-main/
├── 验证码登录/                         # 验证码验证子系统
│   ├── web_server.py                   # ★ 主服务入口：HTTP 服务器，整合验证码与识别接口
│   ├── captcha_synth.py                # MNIST 手写数字验证码合成（模糊+噪点）
│   ├── captcha_backend.py              # CNN 验证码识别后端（加载模型验证用户答案）
│   ├── train_captcha_cnn.py            # 训练 CNN 模型用于验证码单字识别
│   ├── login_captcha_tkinter.py        # Tkinter 桌面演示程序
│   ├── captcha_digit_cnn.h5            # 训练好的 CNN 验证码识别模型
│   └── templates/
│       └── login.html                  # Web 前端页面（单页应用）
├── 手写数字识别/                       # 手写数字识别子系统
│   ├── app.py                          # Gradio 独立 Web 应用
│   └── cnn_model_v2.h5                 # 训练好的 CNN 手写数字识别模型
├── data/                               # 数据与数据集构建
│   ├── build_captcha_dataset.py        # 从 MNIST 构建验证码训练数据集
│   ├── fetch_mnist_npz.py             # MNIST 数据下载工具
│   └── captcha_dataset.npz             # 生成的训练数据集（运行后产出）
├── requirements.txt                    # Python 依赖清单
└── README.md                           # 本文档
```

---

## 核心功能介绍

### 1. 验证码图片选择验证

系统采用创新的**4图选择验证**机制，替代传统的输入式验证码：

- **生成阶段**：服务端同时生成 4 张不同的验证码图片，每张包含 4 位随机手写数字
- **挑战阶段**：从 4 张图片中随机选中一张，提取其数字序列作为"目标数字"展示给用户
- **验证阶段**：用户需要从 4 张图片中找出包含目标数字的那一张，点击选择提交验证
- **结果处理**：验证通过后进入手写数字识别页面；失败则提示重试并支持刷新换组

**安全特性**：
- 多色彩高对比度文字（6 组四色方案随机选取）
- 非线性波浪扭曲变换（双层正弦/余弦位移映射 + 双线性插值）
- 贝塞尔干扰曲线（3~7 条，50 段线段近似绘制）
- 逐字独立旋转（±22° BICUBIC 重采样）+ 字符间随机重叠
- 多层次噪点：背景网格线、随机点阵、前景随机点、短线段、矩形框
- 边缘高斯模糊（0.5~1.3px 随机半径）
- 所有参数随机化，每次生成的验证码完全不可预测
- 尺寸 448×112 像素，远超常规验证码规格

### 2. 手写数字识别

基于 CNN 的手写数字实时识别：

- **画板绘制**：支持鼠标和触屏手写输入
- **单数字模式**：书写单个 0~9 数字，返回预测结果及 0~9 全概率分布
- **多数字模式**：书写多个数字，系统自动分割、逐个识别并输出连续序列
- **可视化反馈**：置信度条形图、Top-3 候选结果展示

### 3. 独立的 Gradio 识别应用

[手写数字识别/app.py](手写数字识别/app.py) 提供基于 Gradio 框架的独立 Web 应用，使用 Sketchpad 组件实现画板交互，可脱离验证码系统单独部署。

---

## 技术栈

| 类别 | 技术 |
|------|------|
| **编程语言** | Python 3.10+ |
| **深度学习** | TensorFlow 2.12~2.18 / Keras |
| **图像处理** | Pillow、OpenCV (cv2)、SciPy |
| **Web 服务端** | Python 内置 `http.server` |
| **Web 前端** | 原生 HTML5 / CSS3 / JavaScript（Canvas API） |
| **独立 UI** | Gradio 4.0+、Tkinter |
| **数据处理** | NumPy、scikit-learn |
| **数据来源** | MNIST 手写数字数据集（70,000 张 28×28 灰度图） |

---

## 依赖清单

详见 [requirements.txt](requirements.txt)：

```
tensorflow>=2.12,<2.19
numpy>=1.23
scipy>=1.10
scikit-learn>=1.2
Pillow>=9.0
gradio>=4.0
```

> **注意**：`opencv-python` 虽未在 requirements.txt 中列显，但在多数字识别模式中依赖 `cv2`。建议一并安装：
> ```bash
> pip install opencv-python
> ```

---

## 环境配置与安装指南

### 前置条件

- Python 3.10 或更高版本
- pip 包管理器
- 稳定的网络连接（用于首次下载 MNIST 数据集和 TensorFlow 依赖）

### 安装步骤

```bash
# 1. 克隆项目或解压项目包
# 2. 进入项目根目录
cd Hand-Written-Digit-Recognition-main

# 3. 创建虚拟环境（强烈推荐）
python -m venv .venv

# 4. 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux / macOS:
# source .venv/bin/activate

# 5. 安装依赖
pip install -r requirements.txt
pip install opencv-python

# 6. 验证安装
python -c "import tensorflow as tf; print('TensorFlow:', tf.__version__)"
python -c "from PIL import Image; print('Pillow OK')"
```

---

## 使用方法

### 启动主服务（验证码验证 + 手写数字识别）

```bash
cd 验证码登录
python web_server.py
```

服务默认监听 `http://localhost:5000`。

浏览器打开后，系统会自动加载验证码挑战：
1. 页面展示 4 张验证码图片及一段目标数字
2. 点击选择你认为包含该数字的图片
3. 点击"确认选择"提交验证
4. 验证通过后进入手写数字识别页面
5. 在画板上书写数字，点击"识别数字"查看结果
6. 可通过开关切换单数字/多数字模式

**自定义端口**：
```bash
# Windows CMD:
set PORT=8080 && python web_server.py
# PowerShell:
$env:PORT=8080; python web_server.py
```

**启用 CNN 手写验证码模式**（需先训练模型）：
```bash
# Windows CMD:
set USE_ML_CAPTCHA=1 && python web_server.py
# PowerShell:
$env:USE_ML_CAPTCHA=1; python web_server.py
```

### 启动 Gradio 独立识别应用

```bash
cd 手写数字识别
python app.py
```

Gradio 应用会在浏览器中自动打开，提供画板绘制和模型预测功能。

### 启动 Tkinter 桌面演示

```bash
cd 验证码登录
python login_captcha_tkinter.py
```

> 需要先完成模型训练（见下文）。

---

## 模型训练流程（可选）

如果你希望使用 CNN 手写验证码模式（`USE_ML_CAPTCHA=1`），需要按顺序执行以下步骤：

### 步骤 1：下载 MNIST 数据

```bash
python data/fetch_mnist_npz.py
```

或将 `mnist.npz` 手动放到项目根目录。

### 步骤 2：构建验证码训练数据集

```bash
python data/build_captcha_dataset.py --n-train 24000 --n-test 4000
```

此脚本将 MNIST 单字拼接为四连模糊验证码，并切分为单字训练样本，输出 `data/captcha_dataset.npz`。

### 步骤 3：训练 CNN 模型

```bash
cd 验证码登录
python train_captcha_cnn.py
```

训练完成后在 `验证码登录/` 下生成 `captcha_digit_cnn.h5`。

---

## API 接口说明

主服务 `web_server.py` 提供以下 HTTP 接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 服务 HTML 前端页面 |
| `GET` | `/api/captcha-challenge` | 获取验证码挑战（4 张图 + 目标数字） |
| `POST` | `/api/verify-captcha` | 提交验证请求（body: `session_id`, `selected` 1-4） |
| `POST` | `/api/digit-recognize` | 单数字识别（body: `auth_token`, `image` base64） |
| `POST` | `/api/digit-recognize-multi` | 多数字识别（body: `auth_token`, `image` base64） |
| `GET` | `/api/health` | 健康检查 |

### 验证流程示意

```
客户端                           服务端
  │                                │
  ├─ GET /api/captcha-challenge ──►│ 生成 4 张图 + 随机选目标数字
  │◄── { images[], target_code } ─┤
  │                                │
  ├─ 用户选择图片 index=3          │
  │                                │
  ├─ POST /api/verify-captcha ────►│ 比对 ground_truths[2]==target_code
  │◄── { success, auth_token } ───┤
  │                                │
  ├─ 后续请求携带 auth_token ────►│ 校验 token 有效性
```

---

## 常见问题解答

### Q1: 启动服务后浏览器打不开页面？

请检查：
- 控制台是否有端口冲突报错（默认 5000）
- 是否在正确的目录下运行 `python web_server.py`
- 防火墙是否拦截了本地端口
- 尝试使用 `http://127.0.0.1:5000` 替代 `localhost`

### Q2: 验证码图片不显示？

确保 `Pillow` 已正确安装：
```bash
pip install --upgrade Pillow
```
同时检查系统是否有可用的 TrueType 字体（Arial），程序会自动 fallback 到默认字体。

### Q3: 手写数字识别返回"识别模型未就绪"？

需要将训练好的 `cnn_model_v2.h5` 放在 `手写数字识别/` 目录下。该模型文件需要单独训练获得。

### Q4: 多数字识别模式依赖 OpenCV 报错？

```bash
pip install opencv-python
```

### Q5: 如何提升验证码安全性？

- 启用 CNN 手写模式：设置 `USE_ML_CAPTCHA=1`（需先完成模型训练）
- 调整 `_generate_enhanced_captcha()` 中的干扰强度参数

### Q6: 如何重置或复用某些参数？

- 服务端 session 有效期为 600 秒（`SESSION_TTL`），过期自动清理
- 端口可通过 `PORT` 环境变量配置
- 验证码校验模式通过 `CAPTCHA_VERIFY` 环境变量配置（`ground_truth` / `model`）

---

## 维护注意事项

1. **模型文件管理**：`cnn_model_v2.h5` 和 `captcha_digit_cnn.h5` 是训练产出物，应妥善备份。如需分发项目，可以仅保留代码，让新用户自行训练。
2. **依赖版本约束**：TensorFlow 版本限制在 2.12~2.18 之间，安装时请注意不要超出范围。如需升级，请先在测试环境验证兼容性。
3. **字体兼容性**：验证码生成依赖系统 TrueType 字体（Arial），在 Linux 部署时可通过 `apt install ttf-mscorefonts-installer` 安装，或修改 `_generate_enhanced_captcha()` 中的字体搜索路径。
4. **session 清理**：服务端使用内存存储 session，重启服务后所有 session 失效。对于生产环境，建议替换为 Redis 等持久化方案。
5. **安全建议**：当前实现为演示级别。生产环境中应：
   - 添加 HTTPS 支持
   - 实现请求频率限制（rate limiting）
   - 将验证码过期时间与 session 解耦
   - 添加日志审计功能
6. **性能考量**：每张增强验证码的生成涉及大量图像处理运算，单次 4 图并发生成在普通 CPU 上约需 100~300ms。对高并发场景建议使用异步队列。
7. **数据集版权**：MNIST 数据集为公开学术数据集（Yann LeCun et al.），可用于学习和研究目的。

---

## 许可说明

本项目为教育用途的人工智能课程实践项目。所使用的 MNIST 数据集及 TensorFlow 框架遵循各自的许可协议。
