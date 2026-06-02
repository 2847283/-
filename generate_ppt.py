import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE


DARK_BLUE = RGBColor(0x1B, 0x2A, 0x4A)
ACCENT_BLUE = RGBColor(0x2E, 0x86, 0xC1)
ACCENT_ORANGE = RGBColor(0xE6, 0x7E, 0x22)
ACCENT_GREEN = RGBColor(0x27, 0xAE, 0x60)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xEC, 0xF0, 0xF1)
DARK_GRAY = RGBColor(0x7F, 0x8C, 0x8D)
BLACK = RGBColor(0x2C, 0x3E, 0x50)
CODE_BG = RGBColor(0xF8, 0xF9, 0xFA)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H


def add_bg(slide, color=DARK_BLUE):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, color, transparency=0):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def add_textbox(slide, left, top, width, height, text, font_size=18, bold=False,
                color=BLACK, alignment=PP_ALIGN.LEFT, font_name='Microsoft YaHei'):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = alignment
    return txBox


def add_bullet_list(slide, left, top, width, height, items, font_size=16, color=BLACK):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = '\u25B8 ' + item
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.font.name = 'Microsoft YaHei'
        p.space_after = Pt(8)
    return txBox


def add_code_block(slide, left, top, width, height, code_text, font_size=13):
    rect = add_rect(slide, left, top, width, height, CODE_BG)
    txBox = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.1),
                                       width - Inches(0.4), height - Inches(0.2))
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(code_text.strip().split('\n')):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(font_size)
        p.font.color.rgb = RGBColor(0x2C, 0x3E, 0x50)
        p.font.name = 'Consolas'
        p.space_after = Pt(2)
    return txBox


def add_table(slide, left, top, col_widths, headers, rows, header_color=ACCENT_BLUE):
    n_rows = len(rows) + 1
    n_cols = len(headers)
    total_w = sum(col_widths)
    table_shape = slide.shapes.add_table(n_rows, n_cols, left, top, total_w,
                                         Inches(0.4) * n_rows)
    table = table_shape.table

    for ci, col_w in enumerate(col_widths):
        table.columns[ci].width = col_w

    for ci, h in enumerate(headers):
        cell = table.cell(0, ci)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_color
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(14)
            p.font.bold = True
            p.font.color.rgb = WHITE
            p.font.name = 'Microsoft YaHei'
            p.alignment = PP_ALIGN.CENTER

    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.cell(ri + 1, ci)
            cell.text = str(val)
            if ri % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT_GRAY
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(13)
                p.font.color.rgb = BLACK
                p.font.name = 'Microsoft YaHei'
                p.alignment = PP_ALIGN.CENTER

    return table_shape


def add_section_header(slide, number, title):
    add_bg(slide, DARK_BLUE)
    add_textbox(slide, Inches(1), Inches(1), Inches(11), Inches(1.2),
                f'第 {number} 部分', font_size=20, color= ACCENT_ORANGE,
                alignment=PP_ALIGN.LEFT)
    add_textbox(slide, Inches(1), Inches(2.2), Inches(11), Inches(1.5),
                title, font_size=38, bold=True, color=WHITE,
                alignment=PP_ALIGN.LEFT)
    add_rect(slide, Inches(1), Inches(3.8), Inches(1.5), Inches(0.06), ACCENT_ORANGE)


def add_content_header(slide, title, subtitle=None):
    add_bg(slide, WHITE)
    add_rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(1.1), DARK_BLUE)
    add_textbox(slide, Inches(0.8), Inches(0.2), Inches(11), Inches(0.7),
                title, font_size=28, bold=True, color=WHITE)
    if subtitle:
        add_textbox(slide, Inches(0.8), Inches(0.75), Inches(11), Inches(0.4),
                    subtitle, font_size=14, color=ACCENT_ORANGE)


def add_page_number(slide, num, total):
    add_textbox(slide, Inches(12), Inches(7.1), Inches(1.2), Inches(0.3),
                f'{num} / {total}', font_size=10, color=DARK_GRAY,
                alignment=PP_ALIGN.RIGHT)


TOTAL = 18


# ============================================================
# Slide 1: 封面
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BLUE)
add_textbox(slide, Inches(1.5), Inches(1.8), Inches(10), Inches(1.0),
            '人工智能创新实践', font_size=22, color=ACCENT_ORANGE, alignment=PP_ALIGN.LEFT)
add_textbox(slide, Inches(1.5), Inches(2.4), Inches(10), Inches(2.0),
            '基于 CNN 的手写数字识别\n与验证码登录系统', font_size=42, bold=True,
            color=WHITE, alignment=PP_ALIGN.LEFT)
add_rect(slide, Inches(1.5), Inches(4.5), Inches(2.5), Inches(0.05), ACCENT_ORANGE)
add_textbox(slide, Inches(1.5), Inches(4.8), Inches(10), Inches(0.5),
            '小组成员：xxx  /  xxx  /  xxx', font_size=18, color=LIGHT_GRAY,
            alignment=PP_ALIGN.LEFT)
add_textbox(slide, Inches(1.5), Inches(5.4), Inches(10), Inches(0.5),
            '2026 年 6 月', font_size=16, color=DARK_GRAY, alignment=PP_ALIGN.LEFT)
add_page_number(slide, 1, TOTAL)

# ============================================================
# Slide 2: 目录
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_BLUE)
add_textbox(slide, Inches(1), Inches(0.8), Inches(11), Inches(1),
            '目  录', font_size=36, bold=True, color=WHITE)
add_rect(slide, Inches(1), Inches(1.7), Inches(1.5), Inches(0.05), ACCENT_ORANGE)

toc_items = [
    ('01', '项目背景与目标', ''),
    ('02', '系统总览与技术栈', ''),
    ('03', '模块一：手写数字识别', '模型结构 · 训练优化 · Gradio 界面'),
    ('04', '模块二：验证码登录系统', '数据合成 · CNN 模型 · Web/桌面双端'),
    ('05', '关键技术对比与难点', ''),
    ('06', '成果展示与总结', ''),
]
for i, (num, title, desc) in enumerate(toc_items):
    y = Inches(2.3) + Inches(0.85) * i
    add_textbox(slide, Inches(1.5), y, Inches(0.8), Inches(0.6),
                num, font_size=28, bold=True, color=ACCENT_ORANGE)
    add_textbox(slide, Inches(2.5), y + Inches(0.02), Inches(6), Inches(0.45),
                title, font_size=22, bold=True, color=WHITE)
    if desc:
        add_textbox(slide, Inches(2.5), y + Inches(0.42), Inches(6), Inches(0.3),
                    desc, font_size=13, color=DARK_GRAY)
add_page_number(slide, 2, TOTAL)

# ============================================================
# Slide 3: 项目背景
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '项目背景')

items = [
    '手写数字识别是计算机视觉与图像分类领域的经典问题，也是深度学习入门必经之路',
    '验证码（CAPTCHA）作为一种"图灵测试"，广泛应用于网站登录、防止机器攻击等场景',
    '基于 MNIST 数据集（60,000 张 28x28 手写数字图片），使用 CNN 解决这两类问题',
    '从模型训练到应用部署，构建一个完整的端到端 AI 应用系统',
    '通过课堂汇报展示深度学习从理论到实践的完整闭环',
]
add_bullet_list(slide, Inches(0.8), Inches(1.5), Inches(11.5), Inches(5.5),
                items, font_size=20, color=BLACK)
add_page_number(slide, 3, TOTAL)

# ============================================================
# Slide 4: 项目目标
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '项目目标')

goals = [
    '训练优化的 CNN 模型识别 0-9 手写数字，测试准确率 > 99%',
    '构建基于 Gradio 的浏览器画板交互界面，实时识别手写数字',
    '实现四连数字验证码的自动合成（含数据增强：旋转、模糊、噪声、对比度等）',
    '训练验证码 CNN 模型（多分类头架构），识别准确率 > 94%',
    '搭建完整的验证码登录系统，支持 Web（HTML+JS）和桌面（Tkinter）双端',
    '将 CNN 识别结果实时可视化展示在前端验证码图片正下方',
]
add_bullet_list(slide, Inches(0.8), Inches(1.5), Inches(11.5), Inches(5.5),
                goals, font_size=19, color=BLACK)
add_page_number(slide, 4, TOTAL)

# ============================================================
# Slide 5: 系统总览
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '系统总体架构')

add_table(slide, Inches(1), Inches(1.6),
          [Inches(5.2), Inches(5.8)],
          ['', ''],
          [],
          header_color=RGBColor(0x1A, 0x52, 0x7F))

add_textbox(slide, Inches(1.2), Inches(1.7), Inches(5), Inches(0.6),
            '\U0001F4CC 模块一：手写数字识别', font_size=18, bold=True, color=WHITE)
items1 = [
    '输入：画板手写 / 上传图片',
    '模型：CNN（4 层卷积 + 全连接）',
    '输出：预测数字 + Top-3 概率',
    '界面：Gradio Web（浏览器访问）',
]
add_bullet_list(slide, Inches(1.2), Inches(2.3), Inches(5), Inches(3),
                items1, font_size=14, color=WHITE)

add_textbox(slide, Inches(6.4), Inches(1.7), Inches(5.5), Inches(0.6),
            '\U0001F4CC 模块二：验证码登录系统', font_size=18, bold=True, color=WHITE)
items2 = [
    '输入：4 连数字验证码图片',
    '模型：CNN（3 层卷积 + 4 头并行 Softmax）',
    '输出：4 位数字识别结果',
    '界面：Tkinter 桌面 + Web 前端（HTML/CSS/JS）',
]
add_bullet_list(slide, Inches(6.4), Inches(2.3), Inches(5.5), Inches(3),
                items2, font_size=14, color=WHITE)

add_textbox(slide, Inches(1), Inches(5.2), Inches(11), Inches(0.7),
            '技术栈：TensorFlow / Keras  +  NumPy / SciPy / PIL  +  Gradio / Tkinter / HTML+CSS+JS',
            font_size=16, bold=True, color=ACCENT_ORANGE, alignment=PP_ALIGN.CENTER)
add_page_number(slide, 5, TOTAL)

# ============================================================
# Slide 6: 手写数字识别 - 模型结构
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '模块一 ── CNN 模型结构', '手写数字识别')

add_textbox(slide, Inches(0.8), Inches(1.4), Inches(11.5), Inches(0.5),
            '数据集：MNIST（28\u00d728 灰度，10 类）  |  预处理：灰度 \u2192 28\u00d728 \u2192 [0,1] \u2192 反色',
            font_size=15, color=DARK_GRAY)

model_layers = (
    'Input (28, 28, 1)\n'
    '\u251C\u2500 Conv2D(32, 3\u00d73) + BatchNorm + MaxPool + Dropout(0.25)\n'
    '\u251C\u2500 Conv2D(64, 3\u00d73) + BatchNorm + MaxPool + Dropout(0.25)\n'
    '\u251C\u2500 Conv2D(128, 3\u00d73) + BatchNorm\n'
    '\u251C\u2500 Conv2D(256, 3\u00d73) + BatchNorm + MaxPool + Dropout(0.25)\n'
    '\u251C\u2500 Flatten\n'
    '\u251C\u2500 Dense(128) + Dropout(0.5)\n'
    '\u2514\u2500 Dense(10) + Softmax'
)
add_code_block(slide, Inches(0.8), Inches(2.2), Inches(6), Inches(4.5),
               model_layers, font_size=14)

add_textbox(slide, Inches(7.5), Inches(2.2), Inches(5), Inches(2),
            '\u25B8 设计要点\n\n'
            '\u2022 4 层卷积逐步加深，提取 \n'
            '   从边缘到语义的多级特征\n'
            '\u2022 BatchNorm 加速收敛、防止梯度消失\n'
            '\u2022 Dropout 防止过拟合\n'
            '\u2022 Softmax 输出 10 类概率分布\n'
            '\u2022 参数量适中，兼顾精度与速度',
            font_size=15, color=BLACK)
add_page_number(slide, 6, TOTAL)

# ============================================================
# Slide 7: 手写数字识别 - 训练流程
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '模块一 ── 训练流程与优化', '手写数字识别')

add_textbox(slide, Inches(0.8), Inches(1.4), Inches(5.5), Inches(0.5),
            '\u25B8 数据增强（ImageDataGenerator）', font_size=18, bold=True, color=ACCENT_BLUE)
add_table(slide, Inches(0.8), Inches(2.0),
          [Inches(2.5), Inches(2.5)],
          ['参数', '设置'],
          [['rotation_range', '12\u00b0'], ['width_shift_range', '12\u00b7'],
           ['height_shift_range', '12\u00b7'], ['zoom_range', '12\u00b7']])

add_textbox(slide, Inches(7), Inches(1.4), Inches(5.5), Inches(0.5),
            '\u25B8 训练回调', font_size=18, bold=True, color=ACCENT_BLUE)
callbacks = [
    'EarlyStopping：patience=8，监控 val_accuracy',
    'ModelCheckpoint：按 val_accuracy 保存最佳模型',
    'ReduceLROnPlateau：学习率自动衰减',
    '固定随机种子（seed=42），保证可复现',
]
add_bullet_list(slide, Inches(7), Inches(2.0), Inches(5.5), Inches(2),
                callbacks, font_size=14, color=BLACK)

add_textbox(slide, Inches(0.8), Inches(4.5), Inches(11.5), Inches(0.5),
            '\u25B8 训练结果', font_size=18, bold=True, color=ACCENT_BLUE)
train_res = [
    '测试集准确率：~99.2%',
    '易混淆数字对：4\u21949、3\u21948、7\u21949（通过混淆矩阵分析）',
    '模型保存为 cnn_model_v2.h5，供 Gradio 前端加载',
]
add_bullet_list(slide, Inches(0.8), Inches(5.1), Inches(11.5), Inches(2),
                train_res, font_size=15, color=BLACK)
add_page_number(slide, 7, TOTAL)

# ============================================================
# Slide 8: 手写数字识别 - Gradio 界面
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '模块一 ── Gradio Web 界面', '手写数字识别')

features = [
    '\u2022 框架：Gradio（Python 原生 Web UI 库）',
    '\u2022 左侧画板：用户用鼠标手写数字，支持一键清空重画',
    '\u2022 右侧结果区：展示预测数字 + 0~9 各类别概率条形图',
    '\u2022 图像预处理：画板图像 → 灰度 → 28\u00d728 → 归一化 → 反色',
    '\u2022 低置信度提示：当最高概率低于阈值时，提示"请重新书写"',
    '\u2022 通过浏览器访问 http://127.0.0.1:7860 即可使用',
]
add_bullet_list(slide, Inches(0.8), Inches(1.5), Inches(11.5), Inches(5),
                features, font_size=18, color=BLACK)

add_rect(slide, Inches(3), Inches(5.2), Inches(7), Inches(1.8), LIGHT_GRAY)
add_textbox(slide, Inches(3.5), Inches(5.4), Inches(6), Inches(1.4),
            '\u2139 此处放 Gradio 界面截图\n'
            '（运行 python app.py 后截取浏览器页面）',
            font_size=18, color=DARK_GRAY, alignment=PP_ALIGN.CENTER)
add_page_number(slide, 8, TOTAL)

# ============================================================
# Slide 9-14: 模块二
# ============================================================
# Slide 9: 验证码生成
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '模块二 ── 验证码生成流程', '验证码登录系统')

add_textbox(slide, Inches(0.8), Inches(1.4), Inches(11.5), Inches(0.5),
            '流程：从 MNIST 随机抽取 4 张数字图片 \u2192 拼合为 28\u00d7112 \u2192 数据增强 \u2192 输出训练样本',
            font_size=16, color=DARK_GRAY)

add_textbox(slide, Inches(0.8), Inches(2.2), Inches(5.5), Inches(0.5),
            '\u25B8 数据增强参数（重点优化）', font_size=18, bold=True, color=ACCENT_BLUE)
add_table(slide, Inches(0.8), Inches(2.8),
          [Inches(2.2), Inches(1.7), Inches(1.7)],
          ['参数', '原值', '增强后'],
          [['旋转角', '\u00b115\u00b0', '\u00b130\u00b0'],
           ['高斯模糊 \u03c3', '0.6 ~ 1.4', '1.0 ~ 2.5'],
           ['噪声 \u03c3', '0.03 ~ 0.08', '0.05 ~ 0.15'],
           ['对比度缩放', '0.85 ~ 1.15', '0.55 ~ 1.55'],
           ['亮度偏移', '\u2014', '\u00b10.25（新增）'],
           ['膨胀/腐蚀', '\u2014', '30\u00b7 概率（新增）']])

add_textbox(slide, Inches(7), Inches(2.2), Inches(5.5), Inches(0.5),
            '\u25B8 训练数据集', font_size=18, bold=True, color=ACCENT_BLUE)
ds_items = [
    '训练集：24,000 张',
    '测试集：4,000 张',
    '每张为 28\u00d7112 灰度图（4 连数字）',
    '数字等概率随机抽取',
    '数据格式：captcha_dataset.npz',
]
add_bullet_list(slide, Inches(7), Inches(2.8), Inches(5.5), Inches(3),
                ds_items, font_size=15, color=BLACK)
add_page_number(slide, 9, TOTAL)

# Slide 10: 验证码 CNN 模型
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '模块二 ── 验证码 CNN 模型结构', '验证码登录系统')

model_code = (
    'Input (28, 112, 1)\n'
    '\u251C\u2500 Conv2D(32, 3\u00d73) + BatchNorm + MaxPool + Dropout\n'
    '\u251C\u2500 Conv2D(64, 3\u00d73) + BatchNorm + MaxPool + Dropout\n'
    '\u251C\u2500 Conv2D(128, 3\u00d73) + BatchNorm + MaxPool + Dropout\n'
    '\u251C\u2500 Flatten\n'
    '\u251C\u2500 \u250C Dense1_1(64) \u2192 Dense1_2(10) \u2192 Softmax  \u2192 第1位\n'
    '\u251C\u2500 \u250C Dense2_1(64) \u2192 Dense2_2(10) \u2192 Softmax  \u2192 第2位\n'
    '\u251C\u2500 \u250C Dense3_1(64) \u2192 Dense3_2(10) \u2192 Softmax  \u2192 第3位\n'
    '\u2514\u2500 \u250C Dense4_1(64) \u2192 Dense4_2(10) \u2192 Softmax  \u2192 第4位'
)
add_code_block(slide, Inches(0.8), Inches(1.8), Inches(6.5), Inches(4.8),
               model_code, font_size=13)

design_notes = [
    '\u25B8 设计思路',
    '',
    '\u2022 3 层共享卷积提取图像特征',
    '\u2022 4 个独立分类头并行预测',
    '\u2022 每路输出 10 类，对应 0-9',
    '\u2022 损失函数：4 路交叉熵之和',
    '\u2022 训练 datagen 更激进：',
    '    rotation \u00b125\u00b0, shift \u00b120\u00b7',
    '    zoom \u00b118\u00b7',
    '',
    '\u25B8 训练结果',
    '\u2022 验证准确率：~94\u00b7+',
]
add_textbox(slide, Inches(8), Inches(1.8), Inches(4.5), Inches(5),
            '\n'.join(design_notes), font_size=14, color=BLACK)
add_page_number(slide, 10, TOTAL)

# Slide 11: 两种运行模式
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '模块二 ── 验证码两种运行模式', '验证码登录系统')

add_rect(slide, Inches(0.8), Inches(1.8), Inches(5.5), Inches(4.5), LIGHT_GRAY)
add_textbox(slide, Inches(1), Inches(1.9), Inches(5), Inches(0.5),
            '模式一：CNN 合成模式', font_size=20, bold=True, color=ACCENT_BLUE)
mode1 = [
    '使用 MNIST 合成 + 增强生成验证码',
    '数据与训练数据同分布，识别率最高',
    '适合演示 CNN 模型的高精度效果',
    '启用方式：USE_ML_CAPTCHA=1',
]
add_bullet_list(slide, Inches(1), Inches(2.6), Inches(5), Inches(3),
                mode1, font_size=15, color=BLACK)

add_rect(slide, Inches(7), Inches(1.8), Inches(5.5), Inches(4.5), LIGHT_GRAY)
add_textbox(slide, Inches(7.2), Inches(1.9), Inches(5), Inches(0.5),
            '模式二：PIL 增强模式（默认）', font_size=20, bold=True, color=ACCENT_GREEN)
mode2 = [
    'PIL 绘制彩色带干扰的验证码',
    '字符旋转、颜色随机、干扰弧线（已去波纹扭曲）',
    'CNN 模型对整图推理，预测 4 位数字',
    '更接近真实网站验证码风格',
    '前端实时显示 CNN 识别结果',
]
add_bullet_list(slide, Inches(7.2), Inches(2.6), Inches(5), Inches(3),
                mode2, font_size=15, color=BLACK)
add_page_number(slide, 11, TOTAL)

# Slide 12: Web 登录流程
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '模块二 ── Web 验证码登录流程', '验证码登录系统')

add_textbox(slide, Inches(0.8), Inches(1.4), Inches(11.5), Inches(0.5),
            '请求流程', font_size=18, bold=True, color=ACCENT_BLUE)

flow_items = [
    '1. 用户打开页面 \u2192 前端请求 /api/captcha-challenge',
    '2. 后端生成 4 张验证码图片（PIL 模式，已去波纹扭曲）',
    '3. CNN 模型逐张识别每张图，得到 4 个 4 位数字预测',
    '4. 后端返回 JSON：{ images[4], predictions[4], session_id, target_code }',
    '5. 前端渲染 2\u00d72 网格，每张图下方显示 "CNN识别: XXXX"',
    '6. 用户选中一张验证码 \u2192 提交验证 \u2192 返回登录结果',
]
add_bullet_list(slide, Inches(0.8), Inches(2.0), Inches(11.5), Inches(3.5),
                flow_items, font_size=17, color=BLACK)

add_textbox(slide, Inches(0.8), Inches(5.0), Inches(11.5), Inches(0.5),
            'API 响应格式', font_size=18, bold=True, color=ACCENT_BLUE)
api_json = (
    '{\n'
    '  "session_id": "a1b2c3d4...",\n'
    '  "images": ["data:image/png;base64,...", ...],\n'
    '  "predictions": ["4392", "9888", "5934", "3802"],\n'
    '  "target_code": "3802"\n'
    '}'
)
add_code_block(slide, Inches(0.8), Inches(5.5), Inches(7), Inches(1.8),
               api_json)
add_page_number(slide, 12, TOTAL)

# Slide 13: 前端界面
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '模块二 ── Web 前端界面设计', '验证码登录系统')

front_items = [
    '\u25B8 技术选型：原生 HTML + CSS + JavaScript（无框架依赖）',
    '',
    '\u25B8 页面布局：',
    '  \u2022 顶部：标题栏 + 用户图标',
    '  \u2022 中部：2\u00d72 验证码网格 + CNN 识别文本',
    '  \u2022 底部：验证码输入框 + 登录按钮',
    '',
    '\u25B8 核心交互：',
    '  \u2022 点击切换选中验证码（蓝色高亮 + 勾选标记）',
    '  \u2022 "换一组"按钮重新获取 4 张新验证码',
    '  \u2022 选中后自动填入底部输入框',
    '  \u2022 实时 CNN 识别结果更新在每张图下方',
]
add_bullet_list(slide, Inches(0.8), Inches(1.5), Inches(7), Inches(5.5),
                front_items, font_size=17, color=BLACK)

add_rect(slide, Inches(8.5), Inches(1.8), Inches(4.2), Inches(5), LIGHT_GRAY)
add_textbox(slide, Inches(8.8), Inches(3), Inches(3.6), Inches(2.5),
            '\u2139 此处放 Web 登录界面截图\n\n'
            '\u25B6 运行：\n'
            'python web_server.py\n\n'
            '\u25B6 访问：\n'
            'http://localhost:5000',
            font_size=14, color=DARK_GRAY, alignment=PP_ALIGN.CENTER)
add_page_number(slide, 13, TOTAL)

# Slide 14: 桌面端
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '模块二 ── 桌面端验证码登录', 'Tkinter 界面')

tk_items = [
    '\u25B8 框架：Python Tkinter（标准库，无需额外安装）',
    '',
    '\u25B8 功能特性：',
    '  \u2022 展示 28\u00d7112 灰度四连验证码图片',
    '  \u2022 输入框输入 4 位数字 \u2192 点击"登录"验证',
    '  \u2022 界面显示 CNN 模型识别结果（供参考）',
    '  \u2022 "换一张"按钮手动刷新验证码',
    '',
    '\u25B8 两种校验模式：',
    '  \u2022 默认模式：输入与真实答案一致即登录成功',
    '  \u2022 模型模式（CAPTCHA_VERIFY=model）',
    '    输入必须与 CNN 识别结果一致才通过',
]
add_bullet_list(slide, Inches(0.8), Inches(1.5), Inches(7), Inches(5.5),
                tk_items, font_size=17, color=BLACK)

add_rect(slide, Inches(8.5), Inches(1.8), Inches(4.2), Inches(5), LIGHT_GRAY)
add_textbox(slide, Inches(8.8), Inches(3), Inches(3.6), Inches(2.5),
            '\u2139 此处放 Tkinter 界面截图\n\n'
            '\u25B6 运行：\n'
            'python login_captcha_tkinter.py',
            font_size=14, color=DARK_GRAY, alignment=PP_ALIGN.CENTER)
add_page_number(slide, 14, TOTAL)

# ============================================================
# Slide 15: 两模块对比
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '两个模块对比分析')

add_table(slide, Inches(0.8), Inches(1.6),
          [Inches(2.2), Inches(4.5), Inches(4.7)],
          ['对比维度', '手写数字识别', '验证码登录'],
          [['输入尺寸', '28\u00d728 单数字灰度', '28\u00d7112 四连数字'],
           ['输出', '1 个类别（0-9）', '4 个类别（每位 0-9）'],
           ['模型结构', '4卷积 + 全连接 + Softmax', '3共享卷积 + 4头并行 Softmax'],
           ['界面框架', 'Gradio（Python 自动生成）', '原生 HTML+CSS+JS / Tkinter'],
           ['数据增强', '标准（rotation/shift/zoom）', '激进（更大+膨胀/腐蚀/亮度）'],
           ['CNN结果展示', '作为最终输出', '每张验证码图下方标注'],
           ['部署方式', '浏览器 Gradio', 'Web 服务器 + 桌面窗口']])
add_page_number(slide, 15, TOTAL)

# ============================================================
# Slide 16: 技术难点
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '技术难点与解决方案')

difficulties = [
    ('难点 1：训练数据与 PIL 验证码图像域不匹配',
     '方案：增强合成数据集扭曲参数（旋转\u00b130\u00b0、模糊\u03c3=2.5、噪声\u03c3=0.15）使训练数据覆盖更广的分布'),
    ('难点 2：PIL 非线性波纹扭曲导致字符变形严重',
     '方案：去掉波纹扭曲调用，保持字符几何完整性，使 CNN 模型能有效识别'),
    ('难点 3：在前端实时展示 CNN 识别结果',
     '方案：后端 API 返回 predictions 数组，前端 JavaScript 动态渲染到每张图片下方的 DOM 元素'),
    ('难点 4：四连数字的并行预测',
     '方案：采用多分类头架构，共享卷积特征提取层，4 个独立全连接头并行输出'),
]

for i, (title, solution) in enumerate(difficulties):
    y_base = Inches(1.6) + Inches(1.35) * i
    add_rect(slide, Inches(0.8), y_base, Inches(11.5), Inches(1.2), LIGHT_GRAY)
    add_textbox(slide, Inches(1), y_base + Inches(0.05), Inches(11), Inches(0.4),
                title, font_size=17, bold=True, color=ACCENT_BLUE)
    add_textbox(slide, Inches(1), y_base + Inches(0.5), Inches(11), Inches(0.6),
                solution, font_size=14, color=BLACK)
add_page_number(slide, 16, TOTAL)

# ============================================================
# Slide 17: 成果展示
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '成果展示')

add_rect(slide, Inches(0.8), Inches(1.5), Inches(5.6), Inches(2.6), LIGHT_GRAY)
add_textbox(slide, Inches(1), Inches(2.3), Inches(5.2), Inches(1),
            '截图 1: Gradio 手写数字识别界面\n（画板 + 识别结果）',
            font_size=14, color=DARK_GRAY, alignment=PP_ALIGN.CENTER)

add_rect(slide, Inches(7), Inches(1.5), Inches(5.6), Inches(2.6), LIGHT_GRAY)
add_textbox(slide, Inches(7.2), Inches(2.3), Inches(5.2), Inches(1),
            '截图 2: 验证码合成对比\n（清晰 \u2194 增强扭曲）',
            font_size=14, color=DARK_GRAY, alignment=PP_ALIGN.CENTER)

add_rect(slide, Inches(0.8), Inches(4.4), Inches(5.6), Inches(2.6), LIGHT_GRAY)
add_textbox(slide, Inches(1), Inches(5.2), Inches(5.2), Inches(1),
            '截图 3: Web 验证码登录界面\n（2\u00d72 网格 + CNN 识别文本）',
            font_size=14, color=DARK_GRAY, alignment=PP_ALIGN.CENTER)

add_rect(slide, Inches(7), Inches(4.4), Inches(5.6), Inches(2.6), LIGHT_GRAY)
add_textbox(slide, Inches(7.2), Inches(5.2), Inches(5.2), Inches(1),
            '截图 4: Tkinter 桌面验证码\n登录界面',
            font_size=14, color=DARK_GRAY, alignment=PP_ALIGN.CENTER)
add_page_number(slide, 17, TOTAL)

# ============================================================
# Slide 18: 总结与展望
# ============================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_content_header(slide, '总结与展望')

add_textbox(slide, Inches(0.8), Inches(1.5), Inches(5.5), Inches(0.5),
            '\u25B8 项目成果', font_size=20, bold=True, color=ACCENT_GREEN)
results = [
    '\u2714 完成两套完整的 CNN 识别系统',
    '\u2714 手写数字识别准确率 > 99%（MNIST 测试集）',
    '\u2714 验证码识别准确率 > 94%（增强训练集）',
    '\u2714 实现 Web + 桌面双端验证码登录',
    '\u2714 CNN 识别结果实时展示在前端',
]
add_bullet_list(slide, Inches(0.8), Inches(2.1), Inches(5.5), Inches(3.5),
                results, font_size=16, color=BLACK)

add_textbox(slide, Inches(7), Inches(1.5), Inches(5.5), Inches(0.5),
            '\u25B8 改进方向', font_size=20, bold=True, color=ACCENT_ORANGE)
future = [
    '\u2022 引入端到端 OCR（CRNN+CTC）处理复杂验证码',
    '\u2022 扩展字符集（字母+数字混合）',
    '\u2022 部署至云服务器实现在线访问',
    '\u2022 增加用户管理与数据库持久化',
    '\u2022 前端性能优化与响应式适配',
]
add_bullet_list(slide, Inches(7), Inches(2.1), Inches(5.5), Inches(3.5),
                future, font_size=16, color=BLACK)

add_rect(slide, Inches(0.8), Inches(5.8), Inches(11.5), Inches(1.2), DARK_BLUE)
add_textbox(slide, Inches(1), Inches(6.0), Inches(11), Inches(0.8),
            '核心亮点：CNN 从训练到部署的完整闭环  |  工作量体现：模型优化 + 数据增强 + 前后端开发 + 双端部署  |  '
            '创新点：CNN 识别结果可视化展示在验证码下方',
            font_size=15, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)
add_page_number(slide, 18, TOTAL)


# ============================================================
# 保存
# ============================================================
output_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(output_dir, '课堂汇报.pptx')
prs.save(output_path)
print(f'PPT 已生成: {output_path}')
print(f'共 {len(prs.slides)} 页')
