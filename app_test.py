# 这个app.py是自己的test里面的图片生成的网页处理结果
from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect, url_for
import os
import random

app = Flask(__name__)
app.secret_key = "abc1234567890defghijklmn"  # 必须设置

# 验证码图片路径：根目录/dataset/test
CAPTCHA_FOLDER = os.path.join(app.root_path, "dataset", "test")
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif']


# ------------------------ 工具函数 ------------------------
def get_captcha_images():
    """获取dataset/test下所有合法的验证码图片"""
    if not os.path.exists(CAPTCHA_FOLDER):
        os.makedirs(CAPTCHA_FOLDER)
        return []
    captcha_images = []
    for filename in os.listdir(CAPTCHA_FOLDER):
        ext = os.path.splitext(filename)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            captcha_images.append(filename)
    return captcha_images


def get_random_captcha():
    """随机选一张验证码图片，精准提取下划线前的4位验证码"""
    images = get_captcha_images()
    if not images:
        return "default.png", "1234"
    random_img = random.choice(images)
    filename_without_ext = os.path.splitext(random_img)[0]
    captcha_text = filename_without_ext.split('_')[0]  # 按下划线分割取前半部分
    captcha_text = captcha_text.upper()
    return random_img, captcha_text


# ------------------------ 新增：home页面路由 ------------------------
@app.route('/home')
def home():
    """验证成功后的首页"""
    return render_template('home.html')


# ------------------------ 原有路由 ------------------------
@app.route('/')
def index():
    """验证码验证页"""
    img_name, captcha_text = get_random_captcha()
    session['captcha'] = captcha_text
    print(f"初始化验证码：图片名={img_name}，验证码={captcha_text}")
    return render_template('index_test.html', captcha_img=img_name)


@app.route('/get_captcha/<img_name>')
def get_captcha(img_name):
    """返回验证码图片"""
    if img_name not in get_captcha_images() and img_name != "default.png":
        return "无效图片", 403
    return send_from_directory(CAPTCHA_FOLDER, img_name)


@app.route('/refresh_captcha')
def refresh_captcha():
    """刷新验证码"""
    img_name, captcha_text = get_random_captcha()
    session['captcha'] = captcha_text
    print(f"刷新验证码：图片名={img_name}，验证码={captcha_text}")
    return jsonify({
        "success": True,
        "img_name": img_name,
        "captcha_text": captcha_text
    })


@app.route('/verify_captcha', methods=['POST'])
def verify_captcha():
    """验证验证码（核心接口）"""
    # 获取并过滤用户输入
    user_input = request.form.get('user_input', '').strip().upper()
    user_input = ''.join([c for c in user_input if c.isalnum()])
    # 获取正确验证码
    correct_captcha = session.get('captcha', '').upper()

    # 打印日志排查
    print("=" * 60)
    print(f"用户实际输入（过滤后）：{user_input}")
    print(f"后端存储的正确验证码：{correct_captcha}")
    print(f"验证结果：{user_input == correct_captcha}")
    print("=" * 60)

    # 验证逻辑
    if not correct_captcha:
        return jsonify({"success": False, "msg": "验证码已过期，请刷新！"})
    if user_input == correct_captcha:
        session.pop('captcha')  # 销毁验证码
        # ************************** 核心修改：返回跳转指令 **************************
        return jsonify({"success": True, "msg": "验证成功，正在跳转...", "redirect": "/home"})
    else:
        # 验证失败，刷新验证码
        img_name, new_captcha = get_random_captcha()
        session['captcha'] = new_captcha
        return jsonify({
            "success": False,
            "msg": "验证码错误，请重新输入！❌",
            "new_img": img_name
        })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)