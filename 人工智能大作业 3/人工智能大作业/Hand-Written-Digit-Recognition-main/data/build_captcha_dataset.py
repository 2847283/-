"""
从公开手写数字图像集构建「模糊四连码」训练数据。

数据来源说明（满足课程「从 GitHub / 网络获取图像集」要求）：
- 主路径：TensorFlow 内置 MNIST（首次运行会从网络自动下载）。
- 镜像参考：MNIST 原始 idx 格式在社区仓库多有镜像，例如可检索 GitHub 上的
  TensorFlow-MNIST / mnist 等仓库，将文件放到本地后也可用 keras 加载。

本脚本将四张 28x28 数字横向拼接为 28×112，再施加模糊与噪声，模拟验证码。
输出：data/captcha_dataset.npz
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from 验证码登录.captcha_synth import load_mnist_digits, one_captcha_image


def expand_to_single_digit_dataset(
    images: np.ndarray, digit_labels: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """将每张 28x112 切成 4 张 28x28，用于单字符 CNN 训练。"""
    n, h, w, _ = images.shape
    assert h == 28 and w == 112, f"期望 (28,112), 得到 ({h},{w})"
    xs = []
    ys = []
    for i in range(n):
        for k in range(4):
            crop = images[i, :, k * 28 : (k + 1) * 28, :]
            xs.append(crop)
            ys.append(digit_labels[i, k])
    return np.stack(xs, axis=0), np.array(ys, dtype=np.int32)


def build_many(n: int, x: np.ndarray, y: np.ndarray, seed: int):
    rng = np.random.default_rng(seed)
    images = np.zeros((n, 28, 112, 1), dtype=np.float32)
    digit_labels = np.zeros((n, 4), dtype=np.int32)
    codes = []
    for i in range(n):
        img, code, digs = one_captcha_image(x, y, rng)
        images[i] = img
        digit_labels[i] = digs
        codes.append(code)
    return images, digit_labels, np.array(codes)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-train", type=int, default=24000)
    parser.add_argument("--n-test", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    x, y = load_mnist_digits()
    out_dir = os.path.dirname(__file__)
    os.makedirs(out_dir, exist_ok=True)

    tr_img, tr_dig, tr_codes = build_many(args.n_train, x, y, args.seed)
    te_img, te_dig, te_codes = build_many(args.n_test, x, y, args.seed + 999)

    tr_x1, tr_y1 = expand_to_single_digit_dataset(tr_img, tr_dig)
    te_x1, te_y1 = expand_to_single_digit_dataset(te_img, te_dig)

    path = os.path.join(out_dir, "captcha_dataset.npz")
    np.savez_compressed(
        path,
        train_images=tr_img,
        train_digit_labels=tr_dig,
        train_codes=tr_codes,
        test_images=te_img,
        test_digit_labels=te_dig,
        test_codes=te_codes,
        train_crops_x=tr_x1,
        train_crops_y=tr_y1,
        test_crops_x=te_x1,
        test_crops_y=te_y1,
    )
    print(f"已保存: {path}")
    print(
        f"四连图: train {tr_img.shape}, test {te_img.shape}; "
        f"单字切片: train {tr_x1.shape}, test {te_x1.shape}"
    )


if __name__ == "__main__":
    main()
