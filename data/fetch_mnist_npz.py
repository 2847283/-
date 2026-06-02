"""
可选：从 GitHub 镜像下载与 Keras 兼容的 mnist.npz 到项目根目录。
镜像仓库：coleifer/mnist 等社区备份（若失效可自行替换 URL）。
"""
from __future__ import annotations

import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "mnist.npz")

# 官方与常见镜像（按顺序尝试）
URLS = [
    "https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz",
]


def main():
    if os.path.isfile(OUT):
        print(f"已存在，跳过: {OUT}")
        return 0
    for url in URLS:
        try:
            print(f"尝试下载: {url}")
            urllib.request.urlretrieve(url, OUT + ".part")
            os.replace(OUT + ".part", OUT)
            print(f"已保存: {OUT}")
            return 0
        except Exception as e:
            print(f"失败: {e}")
    print("所有镜像均失败，请手动下载 mnist.npz 到项目根目录。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
