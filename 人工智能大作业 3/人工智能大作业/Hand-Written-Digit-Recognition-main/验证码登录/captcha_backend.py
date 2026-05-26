"""
验证码登录后端：加载 CNN，对整张四连图逐位识别；与用户输入比对。

比对策略（环境变量 CAPTCHA_VERIFY）：
- ground_truth（默认）：用户输入须与验证码图像中的真实 4 位数字一致（与真实网站一致：服务端掌握标准答案）。
- model：用户输入须与 CNN 识别结果一致（用于检验模型输出与用户是否一致）。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import tensorflow as tf

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from captcha_synth import load_mnist_digits, one_captcha_image, split_four_crops
DEFAULT_MODEL = os.path.join(ROOT, "captcha_digit_cnn.h5")


class CaptchaLoginBackend:
    def __init__(self, model_path: str | None = None):
        path = model_path or DEFAULT_MODEL
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"未找到模型文件: {path}\n请先执行: python data/build_captcha_dataset.py\n"
                f"再执行: python train_captcha_cnn.py"
            )
        self.model = tf.keras.models.load_model(path)
        self._x_pool, self._y_pool = load_mnist_digits()
        self._rng = np.random.default_rng()
        mode = os.environ.get("CAPTCHA_VERIFY", "ground_truth").strip().lower()
        self.verify_against_model = mode == "model"

    def predict_code(self, image: np.ndarray) -> str:
        """image: (28,112,1) float32"""
        crops = split_four_crops(image)
        logits = self.model.predict(crops, verbose=0)
        pred = np.argmax(logits, axis=1)
        return "".join(str(int(d)) for d in pred)

    def new_challenge(self) -> tuple[np.ndarray, str, str]:
        """
        随机生成一张验证码。
        返回: image (28,112,1), ground_truth 字符串, model_prediction 字符串（先验预测，可与 new 后一致）
        """
        img, gt, _ = one_captcha_image(self._x_pool, self._y_pool, self._rng)
        pred = self.predict_code(img)
        return img, gt, pred

    def check_login(self, user_input: str, image: np.ndarray, ground_truth: str) -> tuple[bool, str, str]:
        """
        返回: (是否成功, 规范化用户输入, CNN 识别字符串)
        """
        u = "".join(c for c in user_input.strip() if c.isdigit())[:4]
        pred = self.predict_code(image)
        ref = pred if self.verify_against_model else ground_truth
        ok = len(u) == 4 and u == ref
        return ok, u, pred
