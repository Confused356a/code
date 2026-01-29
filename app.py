from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
import os
import torch
import pymysql
import hashlib
import random
import io
from datetime import datetime
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

# ===================== 已固定配置（无需修改）=====================
MYSQL_PASSWORD = "kzc20040827"  # 你的MySQL密码，已固定
CAPTCHA_IMG_FOLDER = r"K:\pytorch\tutorial\dataset\test"  # 你的K盘图片路径
# ==========================================================
ALLOWED_IMG_SUFFIX = [".png", ".jpg", ".jpeg", ".bmp"]  # 支持的图片格式

# ------------------------ 模型加载（原逻辑完全保留） ------------------------
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL = torch.load("model.pth", weights_only=False).to(DEVICE)
MODEL.eval()  # 评估模式，关闭训练层


# ------------------------ MySQL数据库操作（适配已有code_captcha数据） ------------------------
def get_mysql_conn():
    """创建MySQL连接，连接code_user_db数据库（核心：固定密码）"""
    try:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password=MYSQL_PASSWORD,  # 已固定为kzc20040827
            db="code_user_db",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10  # 增加连接超时，提升稳定性
        )
        return conn
    except Exception as e:
        print(f"❌ MySQL连接失败：{e}（请检查MySQL服务是否启动、密码是否正确）")
        return None


def encrypt_password(password: str) -> str:
    """密码SHA256加密"""
    sha256 = hashlib.sha256()
    sha256.update(password.encode("utf-8"))
    return sha256.hexdigest()


def verify_password(input_pwd: str, db_pwd: str) -> bool:
    """验证密码是否一致"""
    return encrypt_password(input_pwd) == db_pwd


def init_captcha_tables():
    """初始化表（仅创建缺失表/插入缺失账号，不影响已有数据）"""
    conn = get_mysql_conn()
    if not conn:
        return
    try:
        with conn.cursor() as cursor:
            # 1. 登录账号表（确保xiaoke账号存在）
            create_user_sql = """
            CREATE TABLE IF NOT EXISTS code_user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(100) NOT NULL,
                create_time DATETIME NOT NULL,
                update_time DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            # 2. 验证码图片表（兼容已有数据，不重建）
            create_captcha_sql = """
            CREATE TABLE IF NOT EXISTS code_captcha (
                id INT AUTO_INCREMENT PRIMARY KEY,
                captcha_img_name VARCHAR(100) NOT NULL,
                captcha_img_path VARCHAR(255) NOT NULL UNIQUE,
                correct_code VARCHAR(4) NOT NULL,
                create_time DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            cursor.execute(create_user_sql)
            cursor.execute(create_captcha_sql)

            # 确保固定账号xiaoke存在（密码xiaoke123）
            insert_user_sql = """
            INSERT IGNORE INTO code_user (username, password, create_time, update_time)
            VALUES (%s, %s, %s, %s)
            """
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(insert_user_sql, ("xiaoke", encrypt_password("xiaoke123"), now, now))
        conn.commit()
        print("✅ 数据库表初始化完成（兼容已有数据），确保xiaoke账号存在")
    except Exception as e:
        print(f"❌ 表初始化失败：{e}")
    finally:
        conn.close()


# ------------------------ 图片预处理+识别（原逻辑完全保留） ------------------------
def preprocess_image(image_path):
    try:
        img = Image.open(image_path)
        transform = transforms.Compose([
            transforms.Grayscale(),
            transforms.Resize((60, 160)),
            transforms.ToTensor()
        ])
        img_tensor = transform(img).to(DEVICE)
        img_tensor = torch.reshape(img_tensor, (-1, 1, 60, 160))
        return img_tensor
    except Exception as e:
        print(f"图片预处理失败：{e}")
        return None


def recognize_captcha(image_path):
    try:
        img_tensor = preprocess_image(image_path)
        if img_tensor is None:
            return None
        with torch.no_grad():
            outputs = MODEL(img_tensor)
        outputs = outputs.view(-1, len(common.captcha_array))
        result = one_hot.vectotext(outputs)
        return result
    except Exception as e:
        print(f"验证码识别失败：{e}")
        return None


# ------------------------ 表单定义（原逻辑完全保留） ------------------------
class SingleUploadForm(FlaskForm):
    file = FileField("上传验证码图片", validators=[DataRequired()])
    submit = SubmitField("单张识别")


class BatchUploadForm(FlaskForm):
    files = FileField("批量上传验证码图片", validators=[DataRequired()])
    submit = SubmitField("批量识别")


# ------------------------ 原有路由（单张/批量识别，完全保留） ------------------------
@app.route("/", methods=["GET", "POST"])
def single_recognize():
    form = SingleUploadForm()
    result = None
    standard_answer = None
    is_correct = None

    if form.validate_on_submit():
        file = form.file.data
        original_filename = file.filename
        filename = secure_filename(original_filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # 提取标准答案
        name_part = original_filename.split("_")[0].split("-")[0]
        standard_answer = name_part[:4] if len(name_part) >= 4 else "无法提取标准答案（文件名格式错误）"
        # 识别验证码
        pred_result = recognize_captcha(file_path)
        # 对比结果
        if pred_result is not None and standard_answer != "无法提取标准答案（文件名格式错误）":
            result = pred_result
            is_correct = (result == standard_answer)
        else:
            result = "识别失败！请检查图片格式/模型是否正常"
            is_correct = False
        # 删除临时文件
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
    form = BatchUploadForm()
    results = []
    total_count = 0
    correct_count = 0
    error = None

    if request.method == "POST" and "files" in request.files:
        files = request.files.getlist("files")
        if len(files) == 0 or (len(files) == 1 and files[0].filename == ""):
            error = "请选择至少一张验证码图片！"
            return render_template("batch.html", form=form, results=results, total_count=0, correct_count=0,
                                   accuracy=0.0, error=error)

        for file in files:
            if file.filename == "":
                continue
            try:
                original_filename = file.filename
                name_part = original_filename.split("_")[0].split("-")[0]
                if len(name_part) >= 4:
                    std_ans = name_part[:4]
                    is_filename_valid = True
                    total_count += 1
                else:
                    std_ans = "文件名格式错误"
                    is_filename_valid = False

                filename = secure_filename(original_filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)

                pred_ans = recognize_captcha(file_path)
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

                results.append({
                    "filename": original_filename,
                    "std_ans": std_ans,
                    "pred_ans": show_result,
                    "is_correct": is_correct,
                    "is_filename_valid": is_filename_valid
                })
                os.remove(file_path)
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "std_ans": "处理异常",
                    "pred_ans": f"错误：{str(e)[:50]}",
                    "is_correct": False,
                    "is_filename_valid": False
                })

    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0.0
    accuracy = round(accuracy, 2)
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
    if "file" not in request.files:
        return jsonify({"code": 400, "msg": "未上传图片文件", "result": ""})
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"code": 400, "msg": "请选择图片文件", "result": ""})
    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        result = recognize_captcha(file_path)
        os.remove(file_path)
        if result is not None and len(str(result)) == 4:
            return jsonify({"code": 200, "msg": "识别成功", "result": result})
        else:
            return jsonify({"code": 500, "msg": "识别失败（结果无效）", "result": ""})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"服务器错误：{str(e)[:50]}", "result": ""})


# ------------------------ 核心路由（数据库读取图片，解决调用失败问题） ------------------------
@app.route("/webtest.html")
def webtest_page():
    """随机测试页面"""
    return render_template("webtest.html")

# 新增：home.html 访问路由（与webtest.html同级）
@app.route("/home.html")
def home_page():
    """验证码验证成功后跳转的首页"""
    return render_template("home.html")


@app.route("/get_captcha_img/<int:captcha_id>")
def get_captcha_img(captcha_id):
    """
    核心：从数据库code_captcha查询图片路径，读取并返回图片流（适配已有数据）
    :param captcha_id: code_captcha表的主键ID
    """
    conn = get_mysql_conn()
    if not conn:
        return jsonify({"success": False, "msg": "数据库连接失败"}), 500
    try:
        # 1. 从数据库查询图片完整信息（重点：读取已存在的captcha_img_path）
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT captcha_img_name, captcha_img_path, correct_code 
                FROM code_captcha 
                WHERE id = %s
            """, (captcha_id,))
            img_info = cursor.fetchone()

        # 2. 校验数据库是否有该图片信息
        if not img_info:
            return jsonify({"success": False, "msg": f"数据库中无ID={captcha_id}的图片信息"}), 404

        img_abs_path = img_info["captcha_img_path"]  # 直接使用数据库中存储的K盘路径
        img_name = img_info["captcha_img_name"]

        # 3. 校验K盘实际文件是否存在
        if not os.path.exists(img_abs_path):
            return jsonify({"success": False, "msg": f"图片文件不存在：{img_abs_path}"}), 404

        # 4. 二进制读取图片，生成内存流（解决跨盘访问）
        with open(img_abs_path, 'rb') as f:
            img_data = f.read()
        img_stream = io.BytesIO(img_data)
        img_stream.seek(0)  # 重置流指针

        # 5. 自动匹配图片MIME类型
        img_suffix = os.path.splitext(img_name)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".bmp": "image/bmp"}
        mime_type = mime_map.get(img_suffix, "image/png")

        # 6. 返回图片流（前端直接展示）
        return send_file(
            img_stream,
            mimetype=mime_type,
            as_attachment=False,
            download_name=img_name
        )
    except Exception as e:
        print(f"❌ 读取图片失败（ID={captcha_id}）：{e}")
        return jsonify({"success": False, "msg": f"图片读取失败：{str(e)[:30]}"}), 500
    finally:
        conn.close()


@app.route("/api/get_captcha", methods=["GET"])
def api_get_captcha():
    """从数据库code_captcha**随机抽取**一张图片（核心：适配已有数据）"""
    conn = get_mysql_conn()
    if not conn:
        return jsonify({"success": False, "msg": "MySQL连接失败（密码：kzc20040827）"})
    try:
        with conn.cursor() as cursor:
            # 1. 查询数据库中已有图片总数
            cursor.execute("SELECT COUNT(*) as total FROM code_captcha")
            total = cursor.fetchone()["total"]
            if total == 0:
                return jsonify({"success": False, "msg": "code_captcha表中无任何图片数据！"})

            # 2. 随机生成ID，抽取图片（基于数据库已有ID范围）
            random_id = random.randint(1, total)

            # 3. 查询该随机图片的核心信息
            cursor.execute("SELECT id, correct_code FROM code_captcha WHERE id = %s", (random_id,))
            captcha = cursor.fetchone()

        # 4. 拼接图片访问URL（基于数据库ID）
        img_url = f"/get_captcha_img/{captcha['id']}"
        return jsonify({
            "success": True,
            "data": {
                "captcha_id": captcha["id"],
                "img_url": img_url
            }
        })
    except Exception as e:
        print(f"❌ 随机抽取图片失败：{e}")
        return jsonify({"success": False, "msg": f"抽取失败：{str(e)[:30]}"}), 500
    finally:
        conn.close()


# ------------------------ 新增：秒杀接口（复用原有识别逻辑，核心修改） ------------------------
@app.route("/api/predict_captcha", methods=["POST"])
def predict_captcha():
    """秒杀接口：根据captcha_id调用model.pth识别验证码，返回预测结果"""
    try:
        # 1. 获取前端传递的验证码ID
        data = request.get_json()
        captcha_id = data.get("captcha_id")
        if not captcha_id or not str(captcha_id).isdigit():
            return jsonify({"success": False, "msg": "缺少有效验证码ID！"})
        captcha_id = int(captcha_id)

        # 2. 从数据库查询验证码图片实际路径（复用已有数据库逻辑）
        conn = get_mysql_conn()
        if not conn:
            return jsonify({"success": False, "msg": "数据库连接失败！"})
        with conn.cursor() as cursor:
            cursor.execute("SELECT captcha_img_path FROM code_captcha WHERE id = %s", (captcha_id,))
            img_info = cursor.fetchone()
        conn.close()
        if not img_info:
            return jsonify({"success": False, "msg": "验证码图片不存在，请刷新！"})
        img_abs_path = img_info["captcha_img_path"]

        # 3. 校验图片文件是否存在
        if not os.path.exists(img_abs_path):
            return jsonify({"success": False, "msg": f"图片文件丢失：{os.path.basename(img_abs_path)}"})

        # 4. 复用原有识别逻辑（核心：不重复写模型代码，直接调用recognize_captcha）
        pred_captcha = recognize_captcha(img_abs_path)
        if not pred_captcha or len(str(pred_captcha)) != 4:
            return jsonify({"success": False, "msg": "模型识别失败，请重试！"})

        # 5. 返回成功结果（4位验证码）
        return jsonify({
            "success": True,
            "captcha": str(pred_captcha)  # 确保为字符串格式
        })
    except Exception as e:
        print(f"❌ 秒杀接口执行失败：{e}")
        return jsonify({"success": False, "msg": f"秒杀失败：{str(e)[:30]}"})


@app.route("/api/login", methods=["POST"])
def api_login():
    """登录验证（账号xiaoke/密码xiaoke123 + 数据库验证码验证）"""
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    input_captcha = data.get("captcha", "").strip()
    captcha_id = data.get("captcha_id", "")

    # 基础校验
    if not all([username, password, input_captcha, captcha_id]):
        return jsonify({"success": False, "msg": "请完整输入账号、密码、验证码！"})

    conn = get_mysql_conn()
    if not conn:
        return jsonify({"success": False, "msg": "数据库连接失败！"})

    try:
        # 1. 校验账号密码
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM code_user WHERE username = %s", (username,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"success": False, "msg": "仅支持固定账号：xiaoke！"})
        if not verify_password(password, user["password"]):
            return jsonify({"success": False, "msg": "密码错误！正确密码：xiaoke123！"})

        # 2. 从数据库查询**正确验证码**（核心：使用已有code_captcha数据）
        cursor.execute("SELECT correct_code FROM code_captcha WHERE id = %s", (captcha_id,))
        captcha = cursor.fetchone()
        if not captcha:
            return jsonify({"success": False, "msg": "验证码已过期，请刷新图片！"})

        # 3. 验证验证码（忽略大小写）
        if input_captcha.lower() != captcha["correct_code"].lower():
            return jsonify({"success": False, "msg": f"验证码错误！正确码：{captcha['correct_code']}"})

        return jsonify({"success": True, "msg": "登录成功！即将进入识别系统！"})
    except Exception as e:
        print(f"❌ 登录验证失败：{e}")
        return jsonify({"success": False, "msg": f"登录失败：{str(e)[:30]}"}), 500
    finally:
        conn.close()


# ------------------------ 程序入口（启动即可用） ------------------------
if __name__ == "__main__":
    init_captcha_tables()  # 仅初始化缺失表/账号，不影响已有数据
    app.run(debug=True, host="0.0.0.0", port=5000)