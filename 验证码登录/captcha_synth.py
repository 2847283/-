"""合成模糊四连数字验证码（基于 MNIST 风格 28×28 字符）。"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass


def load_mnist_digits():
    """
    加载顺序：本地 mnist.npz → OpenML（sklearn）→ Keras 官方下载。
    可通过环境变量 MNIST_NPZ_PATH 指定本地 npz。
    """
    local = os.environ.get("MNIST_NPZ_PATH", "").strip()
    root = os.path.dirname(os.path.abspath(__file__))
    candidates = [p for p in (local, os.path.join(root, "mnist.npz")) if p]

    def _from_npz(path: str):
        z = np.load(path)
        if "x_train" in z.files:
            x = np.concatenate([z["x_train"], z["x_test"]], axis=0).astype(np.float32) / 255.0
            y = np.concatenate([z["y_train"], z["y_test"]], axis=0).astype(np.int32)
        else:
            x, y = z["x"], z["y"]
            x = x.astype(np.float32) / 255.0
            y = y.astype(np.int32).ravel()
        return x, y

    for path in candidates:
        if path and os.path.isfile(path):
            return _from_npz(path)

    try:
        from sklearn.datasets import fetch_openml

        data = fetch_openml("mnist_784", version=1, as_frame=False, parser="auto")
        x = data["data"].reshape(-1, 28, 28).astype(np.float32) / 255.0
        y_raw = np.asarray(data["target"])
        if y_raw.dtype.kind in "UO" or y_raw.dtype == object:
            y = np.array([int(str(v)) for v in y_raw], dtype=np.int32)
        else:
            y = y_raw.astype(np.int32)
        return x, y
    except Exception:
        pass

    try:
        import tensorflow as tf

        (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
    except Exception as e:
        raise RuntimeError(
            "无法加载 MNIST。请联网后重试，或将 mnist.npz 放到项目根目录并设置 MNIST_NPZ_PATH，"
            "或安装 scikit-learn 后由 OpenML 自动下载。"
        ) from e
    x = np.concatenate([x_train, x_test], axis=0).astype(np.float32) / 255.0
    y = np.concatenate([y_train, y_test], axis=0).astype(np.int32)
    return x, y


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


def one_captcha_image(
    x_pool: np.ndarray,
    y_pool: np.ndarray,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, str, np.ndarray]:
    """
    生成单张验证码图 (28,112,1) float32，以及 4 位字符串标签与 shape (4,) 的逐位整数标签。
    """
    from scipy import ndimage

    if rng is None:
        rng = np.random.default_rng()
    strips = []
    digits: list[int] = []
    for _ in range(4):
        idx = int(rng.integers(0, len(x_pool)))
        d2 = np.array(x_pool[idx], dtype=np.float32)
        angle = rng.uniform(-30, 30)
        d2 = ndimage.rotate(d2, angle, reshape=False, order=1, mode="constant", cval=0.0)
        d2 = np.clip(d2, 0, 1)
        strips.append(d2)
        digits.append(int(y_pool[idx]))
    row = np.concatenate(strips, axis=1)
    row = _blur_and_noise(row, rng)
    img = row.reshape(28, 112, 1).astype(np.float32)
    code = "".join(str(d) for d in digits)
    return img, code, np.array(digits, dtype=np.int32)


def split_four_crops(img: np.ndarray) -> np.ndarray:
    """(28,112,1) -> (4,28,28,1)"""
    assert img.shape == (28, 112, 1)
    return np.stack([img[:, k * 28 : (k + 1) * 28, :] for k in range(4)], axis=0)
