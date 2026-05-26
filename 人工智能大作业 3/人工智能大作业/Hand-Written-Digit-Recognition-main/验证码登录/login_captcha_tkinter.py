"""
基于模糊数字验证码识别的自动化登录演示（Tkinter）。

运行前请训练模型：
  python data/build_captcha_dataset.py
  python train_captcha_cnn.py

启动：
  python login_captcha_tkinter.py

比对逻辑见 captcha_backend.py（默认与图像内真实 4 位一致；可设 CAPTCHA_VERIFY=model 改为与 CNN 输出一致）。
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import messagebox

import numpy as np
from PIL import Image, ImageTk

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from captcha_backend import CaptchaLoginBackend


class LoginApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("模糊数字验证码登录演示")
        self.root.geometry("520x420")
        self.root.minsize(480, 380)

        self.backend = CaptchaLoginBackend()
        self._photo: ImageTk.PhotoImage | None = None
        self.current_image: np.ndarray | None = None
        self.ground_truth: str = ""

        frm = tk.Frame(self.root, padx=16, pady=16)
        frm.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frm,
            text="请输入下方验证码中的 4 位数字（从左到右）",
            font=("Microsoft YaHei UI", 11),
        ).pack(anchor=tk.W)

        self.canvas = tk.Label(frm, bg="#f0f0f0", relief=tk.SUNKEN, bd=1)
        self.canvas.pack(pady=12)

        row = tk.Frame(frm)
        row.pack(fill=tk.X, pady=6)
        tk.Label(row, text="验证码：", font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        self.entry = tk.Entry(row, width=12, font=("Consolas", 14))
        self.entry.pack(side=tk.LEFT, padx=8)

        btn_row = tk.Frame(frm)
        btn_row.pack(pady=10)
        tk.Button(
            btn_row,
            text="登录",
            font=("Microsoft YaHei UI", 10),
            width=10,
            command=self._on_login,
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            btn_row,
            text="换一张",
            font=("Microsoft YaHei UI", 10),
            width=10,
            command=self._refresh,
        ).pack(side=tk.LEFT, padx=4)

        self.hint = tk.Label(
            frm,
            text="",
            font=("Microsoft YaHei UI", 9),
            fg="#555",
            wraplength=460,
            justify=tk.LEFT,
        )
        self.hint.pack(anchor=tk.W, pady=8)

        self._refresh()
        self.root.bind("<Return>", lambda e: self._on_login())

    def _array_to_photo(self, img: np.ndarray) -> ImageTk.PhotoImage:
        g = (np.clip(img[:, :, 0], 0, 1) * 255).astype(np.uint8)
        pil = Image.fromarray(g, mode="L").resize((448, 112), Image.Resampling.NEAREST)
        return ImageTk.PhotoImage(pil)

    def _refresh(self):
        img, gt, pred = self.backend.new_challenge()
        self.current_image = img
        self.ground_truth = gt
        self._photo = self._array_to_photo(img)
        self.canvas.configure(image=self._photo)
        self.entry.delete(0, tk.END)
        mode = os.environ.get("CAPTCHA_VERIFY", "ground_truth").strip().lower()
        tip = (
            "校验方式：与验证码图像中的真实 4 位数字一致即登录成功；下方为 CNN 识别供参考。"
            if mode != "model"
            else "校验方式：须与 CNN 识别结果完全一致才算登录成功。"
        )
        self.hint.configure(text=f"{tip}\n当前 CNN 预读：{pred}（提交时会再次推理）")

    def _on_login(self):
        if self.current_image is None:
            return
        raw = self.entry.get()
        ok, u, pred = self.backend.check_login(raw, self.current_image, self.ground_truth)
        if ok:
            messagebox.showinfo("结果", f"登录成功！\n您输入：{u}\nCNN 识别：{pred}")
        else:
            messagebox.showwarning(
                "结果",
                f"登录失败。\n您输入：{u!r}（需为 4 位数字）\nCNN 识别：{pred}\n将为您刷新新的验证码。",
            )
            self._refresh()

    def run(self):
        self.root.mainloop()


def main():
    try:
        LoginApp().run()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
