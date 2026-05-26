"""
阶段二：在合成模糊四连码的「单字切片」上训练 CNN，保存 captcha_digit_cnn.h5。
需先运行: python data/build_captcha_dataset.py
"""
from __future__ import annotations

import os

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "data", "captcha_dataset.npz")
MODEL_OUT = os.path.join(ROOT, "captcha_digit_cnn.h5")


def build_model():
    model = models.Sequential(
        [
            layers.Input(shape=(28, 28, 1)),
            layers.Conv2D(32, (3, 3), activation="relu", padding="same"),
            layers.BatchNormalization(),
            layers.MaxPooling2D(2),
            layers.Dropout(0.25),
            layers.Conv2D(64, (3, 3), activation="relu", padding="same"),
            layers.BatchNormalization(),
            layers.MaxPooling2D(2),
            layers.Dropout(0.25),
            layers.Conv2D(128, (3, 3), activation="relu", padding="same"),
            layers.BatchNormalization(),
            layers.Dropout(0.25),
            layers.Flatten(),
            layers.Dense(128, activation="relu"),
            layers.Dense(10, activation="linear"),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )
    return model


def main():
    if not os.path.isfile(DATA_PATH):
        raise SystemExit(f"请先运行: python data/build_captcha_dataset.py  （缺少 {DATA_PATH}）")

    d = np.load(DATA_PATH)
    x_train = d["train_crops_x"].astype(np.float32)
    y_train = d["train_crops_y"].astype(np.int32)
    x_test = d["test_crops_x"].astype(np.float32)
    y_test = d["test_crops_y"].astype(np.int32)

    tf.keras.utils.set_random_seed(42)

    datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        rotation_range=12,
        width_shift_range=0.12,
        height_shift_range=0.12,
        zoom_range=0.12,
    )
    datagen.fit(x_train)

    model = build_model()
    bs = 256
    train_gen = datagen.flow(x_train, y_train, batch_size=bs, seed=42)

    cb = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=5, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=3, min_lr=1e-5
        ),
    ]

    model.fit(
        train_gen,
        epochs=40,
        validation_data=(x_test, y_test),
        callbacks=cb,
        verbose=1,
    )

    model.save(MODEL_OUT)
    print(f"已保存模型: {MODEL_OUT}")


if __name__ == "__main__":
    main()
