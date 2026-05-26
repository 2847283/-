import os

import gradio as gr
import numpy as np 
import tensorflow as tf

ROOT = os.path.dirname(os.path.abspath(__file__))
model = tf.keras.models.load_model(os.path.join(ROOT, "cnn_model_v2.h5"))


def predict(input_dict):
    if not input_dict or "composite" not in input_dict:
        return {str(i): 0.0 for i in range(10)}

    image = input_dict["composite"]

    # Remove alpha channel (RGBA → RGB)
    image = image[:, :, :3]

    # Convert to grayscale
    image = tf.image.rgb_to_grayscale(image)

    # Resize to 28x28
    image = tf.image.resize(image, [28, 28])

    # Invert colors and normalize
    image = 255 - image
    image = image / 255.0
    image = image.numpy().reshape(-1, 28, 28, 1)

    # Predict
    prediction = model.predict(image)
    probs = tf.nn.softmax(prediction[0]).numpy()

    if probs.max() < 0.5:
        return "请重新尝试绘制数字。"
    else:
        return {str(i): float(probs[i]) for i in range(10)}


# 使用 Gradio Blocks 创建更美观的中文界面
with gr.Blocks() as demo:
    gr.Markdown(
        """
        # 手写数字识别（MNIST）
        使用已经训练好的卷积神经网络（CNN）模型，对您在画板上书写的 **0–9 手写数字** 进行识别。
        """
    )

    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("### 在下方画板中书写一个数字")
            sketchpad = gr.Sketchpad(
                label="绘制数字（0–9）",
                height=280,
            )

            with gr.Row():
                clear_btn = gr.ClearButton([sketchpad], value="清空画板")
                submit_btn = gr.Button("识别数字", variant="primary")

        with gr.Column(scale=2):
            gr.Markdown("### 预测结果（概率）")
            label = gr.Label(
                label="模型预测的前 3 个数字",
                num_top_classes=3,
            )
            gr.Markdown(
                """
                **使用小贴士：**

                - 尽量把数字写在画板正中间  
                - 使用稍粗一点的笔画，笔迹要连贯  
                - 如果结果不理想，可以点击“清空画板”后重新书写  
                """
            )

    # 按钮触发预测
    submit_btn.click(fn=predict, inputs=sketchpad, outputs=label)


demo.launch(
    debug=False,
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
)
