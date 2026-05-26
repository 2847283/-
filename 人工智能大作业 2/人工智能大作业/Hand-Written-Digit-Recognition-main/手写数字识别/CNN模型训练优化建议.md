# CNN_Model_Training.ipynb 优化建议与改进思路

在现有 99.37% 左右测试准确率的基础上，从**数据、训练流程、模型与评估**四方面给出可落地的改进建议，便于产出全新、更稳的模型（如 `cnn_model_v3.h5`）。

---

## 一、数据与数据增强

### 1. 修正验证集使用方式（建议优先做）

当前代码用 `train_test_split` 得到 `x_train_split, x_val, y_train_split, y_val`，但 `fit` 里用的是 `datagen.flow(x_train, y_train, ...)`，相当于**用全部 6 万样本训练、其中 10% 又当验证集**，存在数据泄露、验证不严谨。

**建议**：用划分后的训练集做增强与训练，验证集仅做验证：

```python
# 使用 x_train_split, y_train_split 做增强与训练
history = model_cnn.fit(
    datagen.flow(x_train_split, y_train_split, batch_size=128),
    validation_data=(x_val, y_val),
    epochs=...
)
```

这样验证集才是“未参与训练”的，指标更可信。

### 2. 增强“画板风格”的多样性（与 app 更一致）

Gradio 画板常见：**白笔/浅色笔画 + 深色或浅色背景**，与 MNIST 的“黑字白底”可能不一致，建议在训练里模拟这种差异：

- **随机反色（重要）**：以一定概率对样本做 `x = 1 - x`（或 `255 - x` 再归一化），让模型同时见过“黑底白字”和“白底黑字”，与 `app.py` 里的预处理更兼容。
- **增强参数微调**：
  - `rotation_range=15`（略加大旋转，模拟书写倾斜）
  - 增加 `shear_range=5`（轻度剪切，模拟歪斜）
  - `fill_mode='constant', cval=0` 或 `'nearest'`，避免旋转/平移后边缘出现奇怪灰块。

实现示例（在自定义生成器或 ImageDataGenerator 之后对 batch 做反色）：

```python
# 在自定义 data generator 中，以 0.5 概率对整张图做反色
if np.random.random() > 0.5:
    x_batch[i] = 1.0 - x_batch[i]
```

或先用 `ImageDataGenerator` 做几何变换，再在 `flow` 的 `transform` 或自定义 generator 里加反色。

### 3. 可选：更丰富的增强

- **亮度/对比度**：若用 `ImageDataGenerator`，可加 `brightness_range=[0.9, 1.1]`（若框架支持）；或自己写 generator 对像素做线性变换。
- **小范围弹性形变**：模拟手写抖动（实现稍复杂，可作为进阶）。

---

## 二、训练流程与稳定性

### 1. 学习率调度（ReduceLROnPlateau）

验证损失停滞时自动降低学习率，往往能再提升一点准确率并稳定收敛：

```python
reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.5,
    patience=2,
    min_lr=1e-6,
    verbose=1
)
# 在 model_cnn.fit(..., callbacks=[reduce_lr, ...]) 中加入
```

### 2. 早停与最佳模型保存

- **EarlyStopping**：防止过拟合，并节省时间：
  - `monitor='val_loss'`，`patience=4`，`restore_best_weights=True`
- **ModelCheckpoint**：只保存验证集上表现最好的权重，便于导出“全新模型”：
  - `monitor='val_accuracy'`，`save_best_only=True`，`filepath='cnn_model_v3.h5'`（或 `cnn_model_best.h5`）

这样最终用于 `app.py` 的是**单文件、最佳权重**，且不会因多跑几个 epoch 而变差。

### 3. 随机种子（可复现）

在 notebook 开头固定种子，便于复现和对比实验：

```python
import os
import random
np.random.seed(42)
tf.random.set_seed(42)
random.seed(42)
# 若在 GPU 上，可加：os.environ['TF_DETERMINISTIC_OPS'] = '1'
```

---

## 三、模型结构（可选）

当前结构已经较好，若想尝试“全新模型”的亮点，可做**小幅度**调整，而不是大改：

- **多一层卷积**：在最后一个 Conv2D(128) 后再加一层 Conv2D(256, (3,3)), BN, Dropout(0.25)，再 Flatten，参数量增加不多，有时能再提一点准确率。
- **GlobalAveragePooling2D**：用 `GlobalAveragePooling2D()` 替代 `Flatten()`，再接 Dense，可减少参数量、有时泛化略好，适合作为对比实验。
- **Dropout 微调**：若验证集上出现过拟合，可把最后一两个 Dropout 从 0.25 提到 0.3。

建议：先做**数据和训练流程**的改进，再视时间决定是否做结构小改；大作业报告里可以写“在原有结构上增加了早停、学习率衰减与反色增强”。

---

## 四、评估与可解释性（便于写报告/答辩）

### 1. 测试集评估

- 保留 `model_cnn.evaluate(x_test, y_test)`，记录最终 **test loss** 和 **test accuracy**。
- 可额外打印 **每个类别的精确率/召回率**（`sklearn.metrics.classification_report`），便于分析哪些数字易混淆（如 4/9、3/8）。

### 2. 混淆矩阵

- 用 `sklearn.metrics.confusion_matrix` + `seaborn.heatmap` 画混淆矩阵，展示哪些数字容易互相认错，可作为报告中的图。

### 3. 错例可视化

- 从测试集中挑出若干**预测错误的样本**，画出“原图 + 真实标签 + 预测标签”，用于分析失败原因（书写风格、模糊、倾斜等），体现对模型行为的理解。

---

## 五、与 app.py 的衔接

- **预处理一致**：训练时若用了“反色”增强，app 里当前的 `255 - image` 再归一化与之一致；若训练时只用了“黑字白底”，要确保 app 的预处理与训练时一致（当前逻辑是先 255-x 再 /255，相当于把画板的“浅色笔画”变成“深色笔画”，与 MNIST 一致）。
- **保存格式**：继续用 `model.save("cnn_model_v3.h5")` 即可，`app.py` 中把 `load_model("cnn_model_v2.h5")` 改为 `load_model("cnn_model_v3.h5")` 即可切换新模型。
- **文档**：在 notebook 末尾用 Markdown 注明：本版本改进点（验证集修正、反色增强、学习率衰减、早停、最佳模型保存），以及最终保存的模型文件名和测试集准确率。

---

## 六、建议实施顺序（优先级）

| 优先级 | 项目 | 预期效果 |
|--------|------|----------|
| 1 | 修正验证集：用 `x_train_split`/`y_train_split` 训练 | 验证指标可信、避免过拟合误判 |
| 2 | 早停 + ModelCheckpoint 保存最佳为 `cnn_model_v3.h5` | 得到可复用的最佳模型、便于部署 |
| 3 | 学习率调度 ReduceLROnPlateau | 收敛更稳、准确率可能略升 |
| 4 | 训练时加入随机反色增强 | 与画板输入分布更一致、鲁棒性更好 |
| 5 | 数据增强微调（rotation/shear/fill_mode） | 书写风格多样性更好 |
| 6 | 混淆矩阵 + 错例可视化 | 便于写报告与答辩 |
| 7 | 可选：结构小改（多一层 Conv 或 GAP） | 作为“模型优化”的加分点 |

按上述顺序在 `CNN_Model_Training.ipynb` 中逐步修改，即可在现有基础上产出**全新、更稳健的模型**，并自然形成大作业中的“算法优化”部分内容。
