import pymysql
import hashlib
import os
import random
from datetime import datetime

# ===================== 配置修改（仅改这3处！！！）=====================
MYSQL_PASSWORD = "kzc20040827"  # 改1：你的Navicat连接MySQL的密码
CAPTCHA_IMG_FOLDER = r"K:\pytorch\tutorial\dataset\test"  # 改2：本地验证码图片文件夹绝对路径（复制文件夹路径，Windows用r前缀，Linux/Mac直接写路径）
ALLOWED_IMG_SUFFIX = [".png", ".jpg", ".jpeg", ".bmp"]  # 改3：你的验证码图片格式，按需添加/删除


# ===================== MySQL数据库连接（通用函数，无需修改）=====================
def get_mysql_conn():
    """创建MySQL连接，连接code_user_db数据库"""
    try:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="kzc20040827",
            db="code_user_db",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ MySQL连接失败：{e}")
        return None


# ===================== 工具函数（密码加密/验证，无需修改）=====================
def encrypt_password(password: str) -> str:
    """密码SHA256加密（比MD5更安全，适配登录密码存储）"""
    sha256 = hashlib.sha256()
    sha256.update(password.encode("utf-8"))
    return sha256.hexdigest()


def verify_password(input_pwd: str, db_pwd: str) -> bool:
    """验证输入密码与数据库加密密码是否一致"""
    return encrypt_password(input_pwd) == db_pwd


# ===================== 数据库表初始化（创建code_user/code_captcha，无需修改）=====================
def init_captcha_tables():
    """初始化2张核心表：code_user(登录账号)、code_captcha(验证码图片信息)"""
    conn = get_mysql_conn()
    if not conn:
        return
    try:
        with conn.cursor() as cursor:
            # 1. 创建code_user表：存储固定登录账号（仅xiaoke）
            create_user_sql = """
            CREATE TABLE IF NOT EXISTS code_user (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
                username VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号',
                password VARCHAR(100) NOT NULL COMMENT '加密后的密码',
                create_time DATETIME NOT NULL COMMENT '创建时间',
                update_time DATETIME NOT NULL COMMENT '更新时间'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='验证码系统登录用户表';
            """
            # 2. 创建code_captcha表：存储验证码图片路径+正确码
            create_captcha_sql = """
            CREATE TABLE IF NOT EXISTS code_captcha (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
                captcha_img_path VARCHAR(255) NOT NULL UNIQUE COMMENT '验证码图片本地绝对路径',
                correct_code VARCHAR(4) NOT NULL COMMENT '正确验证码（图片名前4位）',
                create_time DATETIME NOT NULL COMMENT '导入时间'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='验证码图片信息表（图片名前4位为正确码）';
            """
            cursor.execute(create_user_sql)
            cursor.execute(create_captcha_sql)

            # 3. 插入固定账号：xiaoke，密码：xiaoke123（仅首次运行插入，重复运行无影响）
            insert_user_sql = """
            INSERT IGNORE INTO code_user (username, password, create_time, update_time)
            VALUES (%s, %s, %s, %s)
            """
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(insert_user_sql, ("xiaoke", encrypt_password("xiaoke123"), now, now))

        conn.commit()
        print("✅ 表初始化成功：创建code_user/code_captcha，已插入固定账号xiaoke")
    except Exception as e:
        print(f"❌ 表初始化失败：{e}")
    finally:
        conn.close()


# ===================== 批量导入本地验证码图片到数据库（核心功能）=====================
def batch_import_captcha_imgs():
    """批量读取本地验证码图片文件夹，提取前4位为正确码，存入code_captcha表"""
    # 校验图片文件夹是否存在
    if not os.path.exists(CAPTCHA_IMG_FOLDER):
        print(f"❌ 验证码图片文件夹不存在：{CAPTCHA_IMG_FOLDER}")
        return
    # 获取文件夹下所有图片文件
    img_files = [f for f in os.listdir(CAPTCHA_IMG_FOLDER)
                 if os.path.splitext(f)[1].lower() in ALLOWED_IMG_SUFFIX]
    if not img_files:
        print(f"❌ 文件夹{CAPTCHA_IMG_FOLDER}中无符合格式的图片")
        return

    conn = get_mysql_conn()
    if not conn:
        return
    try:
        with conn.cursor() as cursor:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            success_count = 0
            for img_file in img_files:
                # 提取图片名前4位作为正确验证码
                correct_code = img_file[:4].strip()
                # 获取图片绝对路径（存入数据库，后续读取图片用）
                img_abs_path = os.path.abspath(os.path.join(CAPTCHA_IMG_FOLDER, img_file))
                # 插入数据（IGNORE避免重复导入同一图片）
                insert_sql = """
                INSERT IGNORE INTO code_captcha (captcha_img_path, correct_code, create_time)
                VALUES (%s, %s, %s)
                """
                cursor.execute(insert_sql, (img_abs_path, correct_code, now))
                success_count += 1
        conn.commit()
        print(f"✅ 批量导入完成！共处理{len(img_files)}张图片，成功存入{success_count}条验证码信息")
    except Exception as e:
        print(f"❌ 批量导入失败：{e}")
    finally:
        conn.close()


# ===================== 随机抽取一张验证码图片（登录时调用，无需修改）=====================
def get_random_captcha():
    """从code_captcha表随机抽取一条验证码信息（图片路径+正确码）"""
    conn = get_mysql_conn()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # 先查询总条数，再随机取一条
            cursor.execute("SELECT COUNT(*) as total FROM code_captcha")
            total = cursor.fetchone()["total"]
            if total == 0:
                print("❌ 数据库中无验证码图片信息，请先执行批量导入")
                return None
            # 随机生成行号
            random_id = random.randint(1, total)
            cursor.execute("SELECT * FROM code_captcha WHERE id = %s", (random_id,))
            captcha_info = cursor.fetchone()
        return captcha_info  # 返回：{'id':xx, 'captcha_img_path':xx, 'correct_code':xx, ...}
    except Exception as e:
        print(f"❌ 随机抽取验证码失败：{e}")
        return None
    finally:
        conn.close()


# ===================== 核心登录验证函数（账号+密码+验证码，无需修改）=====================
def user_login(input_username: str, input_pwd: str, input_captcha: str) -> dict:
    """
    用户登录验证：
    1. 校验账号是否为xiaoke
    2. 校验密码是否为xiaoke123（加密验证）
    3. 随机抽取验证码图片，验证输入的验证码是否正确
    返回：{'success':True/False, 'msg':'提示信息', 'captcha_info':随机抽取的验证码信息}
    """
    # 步骤1：校验数据库连接
    conn = get_mysql_conn()
    if not conn:
        return {"success": False, "msg": "数据库连接失败", "captcha_info": None}
    try:
        # 步骤2：校验账号密码
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM code_user WHERE username = %s", (input_username,))
            user_info = cursor.fetchone()
            # 账号不存在
            if not user_info:
                return {"success": False, "msg": "账号错误，仅支持账号xiaoke", "captcha_info": None}
            # 密码错误
            if not verify_password(input_pwd, user_info["password"]):
                return {"success": False, "msg": "密码错误，xiaoke账号密码为xiaoke123", "captcha_info": None}

        # 步骤3：随机抽取验证码图片
        captcha_info = get_random_captcha()
        if not captcha_info:
            return {"success": False, "msg": "抽取验证码图片失败", "captcha_info": None}

        # 步骤4：验证验证码（忽略大小写，如8A7Z和8a7z都正确，可选关闭）
        if input_captcha.strip().lower() != captcha_info["correct_code"].lower():
            return {
                "success": False,
                "msg": f"验证码错误！正确验证码为：{captcha_info['correct_code']}",
                "captcha_info": captcha_info
            }

        # 所有验证通过
        return {
            "success": True,
            "msg": "登录成功！账号、密码、验证码均正确",
            "captcha_info": captcha_info
        }
    except Exception as e:
        return {"success": False, "msg": f"登录验证失败：{str(e)}", "captcha_info": None}
    finally:
        conn.close()


# ===================== 主函数（运行入口，按顺序执行，无需修改）=====================
if __name__ == "__main__":
    # 步骤1：初始化数据库表（创建code_user/code_captcha，插入xiaoke账号）
    print("===== 步骤1：初始化数据库表 =====")
    init_captcha_tables()

    # 步骤2：批量导入本地验证码图片到数据库
    print("\n===== 步骤2：批量导入验证码图片 =====")
    batch_import_captcha_imgs()

    # 步骤3：模拟用户登录（测试用，可替换为实际前端/控制台输入）
    print("\n===== 步骤3：模拟用户登录验证 =====")
    # 固定账号密码，仅需输入验证码
    TEST_USERNAME = "xiaoke"
    TEST_PASSWORD = "xiaoke123"
    input_captcha = input(f"请输入验证码（账号：{TEST_USERNAME}，密码：{TEST_PASSWORD}）：")

    # 执行登录验证
    login_result = user_login(TEST_USERNAME, TEST_PASSWORD, input_captcha)
    # 打印登录结果
    print(f"\n登录结果：{login_result['msg']}")
    if login_result["captcha_info"]:
        print(f"本次抽取的验证码图片：{login_result['captcha_info']['captcha_img_path']}")