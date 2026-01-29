import pymysql
import hashlib
import random
import string
from datetime import datetime


# 1. 连接新建的code_user_db数据库（仅改密码！）
def get_mysql_conn():
    conn = pymysql.connect(
        host='localhost',  # 本地MySQL地址，不用改
        user='root',  # MySQL账号，默认是root，不用改
        password='kzc20040827',  # 填你Navicat的MySQL密码
        db='code_user_db',  # 已建好的数据库名，不用改
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn


# 2. 初始化数据表（自动创建code_user_operation表）
def init_mysql_db():
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cursor:
            # 创建带code前缀的表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS code_user_operation (
                id INT AUTO_INCREMENT PRIMARY KEY,
                account VARCHAR(50) NOT NULL COMMENT '用户账号',
                password VARCHAR(100) NOT NULL COMMENT '加密后的密码',
                verification_code VARCHAR(10) COMMENT '验证码',
                create_time DATETIME NOT NULL COMMENT '创建时间'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户操作表（code前缀）';
            """
            cursor.execute(create_table_sql)
        conn.commit()
        print("✅ 数据表code_user_operation创建成功！")
    except Exception as e:
        print(f"❌ 表创建失败：{e}")
    finally:
        conn.close()


# 3. 密码加密（自动处理，不用改）
def encrypt_password(password):
    sha256 = hashlib.sha256()
    sha256.update(password.encode('utf-8'))
    return sha256.hexdigest()


# 4. 生成验证码（自动处理，不用改）
def generate_verification_code(length=6):
    chars = string.digits + string.ascii_letters
    return ''.join(random.choice(chars) for _ in range(length))


# 5. 插入用户数据（自动存到新表）
def insert_user_info(account, password):
    encrypted_pwd = encrypt_password(password)
    verify_code = generate_verification_code()
    create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_mysql_conn()
    try:
        with conn.cursor() as cursor:
            insert_sql = """
            INSERT INTO code_user_operation (account, password, verification_code, create_time)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (account, encrypted_pwd, verify_code, create_time))
        conn.commit()
        print(f"✅ 用户【{account}】信息已存入code_user_db数据库！")
        print(f"👉 该用户的验证码：{verify_code}（仅展示一次）")
        return verify_code
    except Exception as e:
        print(f"❌ 插入数据失败：{e}")
        return None
    finally:
        conn.close()


# 6. 查询用户数据（验证是否存成功）
def query_user_info(account):
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cursor:
            query_sql = "SELECT * FROM code_user_operation WHERE account = %s"
            cursor.execute(query_sql, (account,))
            result = cursor.fetchone()
            if result:
                print("\n✅ 查询到用户信息：")
                print(f"账号：{result['account']}")
                print(f"加密密码：{result['password']}")
                print(f"验证码：{result['verification_code']}")
                print(f"创建时间：{result['create_time']}")
            else:
                print(f"\n❌ 未查询到账号【{account}】的信息")
            return result
    except Exception as e:
        print(f"❌ 查询失败：{e}")
        return None
    finally:
        conn.close()


# 主函数（运行入口，改账号密码即可）
if __name__ == "__main__":
    # 第一步：初始化数据表（自动建表）
    init_mysql_db()

    # 第二步：自定义要插入的用户信息（改这两行！）
    test_account = "kezhicheng"  # 你想设置的用户账号
    test_password = "kezhicheng2004"  # 你想设置的用户密码

    # 第三步：插入数据到新数据库
    insert_user_info(test_account, test_password)

    # 第四步：查询验证数据是否存入
    query_user_info(test_account)