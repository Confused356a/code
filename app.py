from flask import Flask, render_template, request, jsonify
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
import os
import torch
from PIL import Image
from torchvision import transforms
import one_hot
import common
import model  # 你的模型定义
import warnings

warnings.filterwarnings("ignore")  # 忽略无关警告

# ------------------------ 基础配置 ------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "captcha_recognize_123456"  # 防止CSRF攻击
app.config["UPLOAD_FOLDER"] = "uploads"  # 上传文件临时目录
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 限制上传大小16MB
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)  # 自动创建上传目录

# ------------------------ 模型加载（复用你的推理逻辑） ------------------------
# 全局加载模型（只加载一次，提升效率）
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# 加载模型（适配你的torch.save(model, "model.pth")保存方式）
MODEL = torch.load("model.pth", weights_only=False).to(DEVICE)
MODEL.eval()  # 设为评估模式，关闭Dropout/BatchNorm等训练层


# ------------------------ 图片预处理函数（和你的predict.py完全一致） ------------------------
def preprocess_image(image_path):
    """
    图片预处理：灰度化→Resize→ToTensor→调整形状
    :param image_path: 本地图片路径
    :return: 预处理后的tensor（可直接输入模型）/None（处理失败）
    """
    try:
        img = Image.open(image_path)
        transform = transforms.Compose([
            transforms.Grayscale(),  # 灰度化（和你的训练逻辑一致）
            transforms.Resize((60, 160)),  # 固定尺寸，和训练时一致
            transforms.ToTensor()  # 转为tensor并归一化到[0,1]
        ])
        img_tensor = transform(img).to(DEVICE)
        # 调整形状：[1,60,160] → [-1,1,60,160]（适配模型输入的batch维度）
        img_tensor = torch.reshape(img_tensor, (-1, 1, 60, 160))
        return img_tensor
    except Exception as e:
        print(f"图片预处理失败：{e}")
        return None


# ------------------------ 验证码识别核心函数 ------------------------
def recognize_captcha(image_path):
    """
    单张验证码识别
    :param image_path: 本地图片路径
    :return: 识别结果字符串/None（识别失败）
    """
    try:
        # 1. 预处理图片
        img_tensor = preprocess_image(image_path)
        if img_tensor is None:
            return None

        # 2. 模型推理（关闭梯度计算，提升速度+节省显存）
        with torch.no_grad():
            outputs = MODEL(img_tensor)

        # 3. 解析输出（和你的predict.py逻辑一致）
        outputs = outputs.view(-1, len(common.captcha_array))
        result = one_hot.vectotext(outputs)
        return result
    except Exception as e:
        print(f"验证码识别失败：{e}")
        return None


# ------------------------ 表单定义 ------------------------
# 单张识别表单
class SingleUploadForm(FlaskForm):
    file = FileField("上传验证码图片", validators=[DataRequired()])
    submit = SubmitField("单张识别")


# 批量识别表单（移除render_kw，改用前端原生multiple）
class BatchUploadForm(FlaskForm):
    files = FileField("批量上传验证码图片", validators=[DataRequired()])
    submit = SubmitField("批量识别")


# ------------------------ 路由定义 ------------------------
@app.route("/", methods=["GET", "POST"])
def single_recognize():
    """单张验证码识别页面（标准答案对比+对错标记）"""
    form = SingleUploadForm()
    result = None  # 识别结果
    standard_answer = None  # 标准答案（文件名前4位）
    is_correct = None  # 是否识别正确

    if form.validate_on_submit():
        # 1. 获取上传文件
        file = form.file.data
        original_filename = file.filename  # 原始文件名（用于提取标准答案）
        filename = secure_filename(original_filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # 2. 保存文件到临时目录
        file.save(file_path)

        # 3. 提取标准答案：文件名前4位（如 4pbx_1769162055.png → 4pbx）
        name_part = original_filename.split("_")[0].split("-")[0]
        if len(name_part) >= 4:
            standard_answer = name_part[:4]
        else:
            standard_answer = "无法提取标准答案（文件名格式错误）"

        # 4. 识别验证码
        pred_result = recognize_captcha(file_path)

        # 5. 对比结果，判断是否正确
        if pred_result is not None and standard_answer != "无法提取标准答案（文件名格式错误）":
            result = pred_result
            is_correct = (result == standard_answer)
        else:
            result = "识别失败！请检查图片格式/模型是否正常"
            is_correct = False

        # 6. 删除临时文件
        os.remove(file_path)

    return render_template(
        "single.html",
        form=form,
        result=result,
        standard_answer=standard_answer,
        is_correct=is_correct
    )


@app.route("/batch", methods=["GET", "POST"])
def batch_recognize():
    """批量验证码识别页面（基于标准答案统计正确率）"""
    form = BatchUploadForm()
    results = []  # 存储识别结果：[{"filename": xxx, "std_ans": xxx, "pred_ans": xxx, "is_correct": bool, "is_filename_valid": bool}]
    total_count = 0  # 有效文件总数（文件名≥4位）
    correct_count = 0  # 识别正确数
    error = None  # 错误提示

    # 处理批量上传请求
    if request.method == "POST" and "files" in request.files:
        files = request.files.getlist("files")  # 获取多文件列表

        # 校验是否选择了文件
        if len(files) == 0 or (len(files) == 1 and files[0].filename == ""):
            error = "请选择至少一张验证码图片！"
            return render_template(
                "batch.html",
                form=form,
                results=results,
                total_count=total_count,
                correct_count=correct_count,
                accuracy=0.0,
                error=error
            )

        # 遍历处理每个文件
        for file in files:
            if file.filename == "":
                continue  # 跳过空文件

            try:
                # 1. 提取原始文件名和标准答案
                original_filename = file.filename
                name_part = original_filename.split("_")[0].split("-")[0]
                # 校验文件名是否有效（至少4位）
                if len(name_part) >= 4:
                    std_ans = name_part[:4]
                    is_filename_valid = True
                    total_count += 1  # 仅有效文件计入统计
                else:
                    std_ans = "文件名格式错误"
                    is_filename_valid = False

                # 2. 保存文件到临时目录
                filename = secure_filename(original_filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)

                # 3. 识别验证码
                pred_ans = recognize_captcha(file_path)

                # 4. 对比标准答案判断对错（仅有效文件参与对比）
                if is_filename_valid and pred_ans is not None:
                    is_correct = (pred_ans == std_ans)
                    if is_correct:
                        correct_count += 1
                    show_result = pred_ans
                elif is_filename_valid and pred_ans is None:
                    is_correct = False
                    show_result = "模型推理失败"
                else:
                    is_correct = False
                    show_result = "无有效识别结果"

                # 5. 记录结果
                results.append({
                    "filename": original_filename,
                    "std_ans": std_ans,
                    "pred_ans": show_result,
                    "is_correct": is_correct,
                    "is_filename_valid": is_filename_valid
                })

                # 6. 删除临时文件
                os.remove(file_path)

            except Exception as e:
                # 单个文件处理失败
                error_info = f"文件处理失败：{str(e)[:50]}"
                results.append({
                    "filename": file.filename,
                    "std_ans": "处理异常",
                    "pred_ans": error_info,
                    "is_correct": False,
                    "is_filename_valid": False
                })

    # 计算正确率（仅有效文件参与，避免除以0）
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0.0
    accuracy = round(accuracy, 2)  # 保留2位小数

    # 渲染页面
    return render_template(
        "batch.html",
        form=form,
        results=results,
        total_count=total_count,
        correct_count=correct_count,
        accuracy=accuracy,
        error=error
    )


@app.route("/api/recognize", methods=["POST"])
def api_recognize():
    """验证码识别API接口（供第三方调用）"""
    # 校验是否上传文件
    if "file" not in request.files:
        return jsonify({"code": 400, "msg": "未上传图片文件", "result": ""})

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"code": 400, "msg": "请选择图片文件", "result": ""})

    try:
        # 保存文件到临时目录
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # 识别验证码
        result = recognize_captcha(file_path)

        # 删除临时文件
        os.remove(file_path)

        # 严格校验结果有效性
        if result is not None and len(str(result)) == 4:
            return jsonify({"code": 200, "msg": "识别成功", "result": result})
        else:
            return jsonify({"code": 500, "msg": "识别失败（结果无效）", "result": ""})

    except Exception as e:
        return jsonify({"code": 500, "msg": f"服务器错误：{str(e)[:50]}", "result": ""})


# ------------------------ 启动应用 ------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)