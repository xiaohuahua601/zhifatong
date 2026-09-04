# ============================================================
# 智法通 - 数据库初始化Python脚本
# 说明: 连接MySQL数据库，执行初始化SQL脚本，插入示例数据，验证结果
# 使用: python scripts/init_db.py
# 依赖: pip install pymysql
# ============================================================

import os
import sys
import time
import logging
from pathlib import Path

# 尝试导入pymysql，如果未安装则提示
try:
    import pymysql
except ImportError:
    print("错误: 未安装pymysql库，请执行: pip install pymysql")
    sys.exit(1)

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================
# 数据库连接配置（从环境变量读取，提供默认值）
# ============================================================
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'zhifatong'),
    'password': os.getenv('DB_PASSWORD', 'zhifatong_pass_2026'),
    'database': os.getenv('DB_NAME', 'zhifatong'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

# SQL文件路径
SQL_FILE_PATH = Path(__file__).parent.parent / 'sql' / 'init.sql'


def wait_for_mysql(max_retries=30, retry_interval=3):
    """
    等待MySQL服务就绪
    在Docker环境中，MySQL容器启动后需要一些时间完成初始化
    本函数会反复尝试连接，直到成功或超过最大重试次数

    参数:
        max_retries: 最大重试次数，默认30次
        retry_interval: 重试间隔（秒），默认3秒

    返回:
        bool: MySQL是否就绪
    """
    logger.info("正在等待MySQL服务就绪...")

    for attempt in range(1, max_retries + 1):
        try:
            # 尝试建立连接
            connection = pymysql.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                charset=DB_CONFIG['charset'],
            )
            connection.close()
            logger.info(f"MySQL服务已就绪（第{attempt}次尝试）")
            return True
        except pymysql.err.OperationalError as e:
            logger.warning(f"等待MySQL就绪... 第{attempt}/{max_retries}次尝试 ({e})")
            time.sleep(retry_interval)

    logger.error(f"MySQL服务在{max_retries}次尝试后仍未就绪")
    return False


def execute_sql_file(connection, sql_file_path):
    """
    执行SQL文件中的所有语句
    逐条执行SQL语句，跳过注释和空行

    参数:
        connection: 数据库连接对象
        sql_file_path: SQL文件路径

    返回:
        bool: 是否执行成功
    """
    logger.info(f"正在读取SQL文件: {sql_file_path}")

    if not sql_file_path.exists():
        logger.error(f"SQL文件不存在: {sql_file_path}")
        return False

    # 读取SQL文件内容
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 按分号分割SQL语句
    # 过滤掉空语句和纯注释
    statements = []
    for statement in sql_content.split(';'):
        # 去除首尾空白
        stripped = statement.strip()
        # 跳过空语句和纯注释行
        if not stripped:
            continue
        if stripped.startswith('--') or stripped.startswith('/*'):
            continue
        statements.append(statement)

    logger.info(f"共解析出{len(statements)}条SQL语句")

    # 逐条执行SQL语句
    success_count = 0
    error_count = 0

    with connection.cursor() as cursor:
        for i, statement in enumerate(statements, 1):
            try:
                # 去除首尾空白后执行
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
                    success_count += 1
                    # 每执行50条输出一次进度
                    if i % 50 == 0:
                        logger.info(f"已执行 {i}/{len(statements)} 条SQL语句")
            except pymysql.err.Error as e:
                error_count += 1
                # 获取语句的前100个字符用于错误提示
                preview = statement.strip()[:100]
                logger.warning(f"SQL语句执行出错（第{i}条）: {e}")
                logger.warning(f"语句预览: {preview}...")

    # 提交事务
    connection.commit()

    logger.info(f"SQL执行完成: 成功{success_count}条, 失败{error_count}条")
    return error_count == 0


def verify_initialization(connection):
    """
    验证数据库初始化结果
    检查各表的记录数，确保数据正确插入

    参数:
        connection: 数据库连接对象

    返回:
        bool: 验证是否通过
    """
    logger.info("正在验证数据库初始化结果...")

    # 需要检查的表及其预期最小记录数
    tables_to_check = {
        'users': 1,                    # 至少1个用户
        'system_configs': 1,           # 至少1条配置
        'legal_documents': 20,         # 至少20条法律文档
        'conversations': 0,            # 对话表可以为空
        'messages': 0,                 # 消息表可以为空
        'contracts': 0,                # 合同表可以为空
        'review_reports': 0,           # 审查报告表可以为空
        'document_chunks': 0,          # 文档分块表可以为空
        'query_logs': 0,               # 查询日志表可以为空
        'citation_stats': 1,           # 至少1条引用统计
        'audit_logs': 1,               # 至少1条审计日志
    }

    all_passed = True

    with connection.cursor() as cursor:
        for table_name, expected_min in tables_to_check.items():
            try:
                cursor.execute(f"SELECT COUNT(*) AS count FROM `{table_name}`")
                result = cursor.fetchone()
                count = result['count']

                if count >= expected_min:
                    logger.info(f"  ✓ {table_name}: {count} 条记录（预期≥{expected_min}）")
                else:
                    logger.warning(f"  ✗ {table_name}: {count} 条记录（预期≥{expected_min}）")
                    all_passed = False
            except pymysql.err.Error as e:
                logger.error(f"  ✗ {table_name}: 查询失败 - {e}")
                all_passed = False

    # 验证管理员用户是否存在
    with connection.cursor() as cursor:
        try:
            cursor.execute("SELECT id, username, role FROM `users` WHERE username = 'admin'")
            admin = cursor.fetchone()
            if admin:
                logger.info(f"  ✓ 管理员用户验证通过: id={admin['id']}, username={admin['username']}, role={admin['role']}")
            else:
                logger.warning("  ✗ 管理员用户不存在")
                all_passed = False
        except pymysql.err.Error as e:
            logger.error(f"  ✗ 管理员用户验证失败: {e}")
            all_passed = False

    # 验证法律文档数量
    with connection.cursor() as cursor:
        try:
            cursor.execute("SELECT doc_type, COUNT(*) AS count FROM `legal_documents` GROUP BY doc_type")
            doc_types = cursor.fetchall()
            logger.info("  法律文档统计:")
            for doc in doc_types:
                logger.info(f"    - {doc['doc_type']}: {doc['count']} 条")
        except pymysql.err.Error as e:
            logger.warning(f"  法律文档统计查询失败: {e}")

    return all_passed


def main():
    """
    主函数：执行数据库初始化流程
    1. 等待MySQL服务就绪
    2. 执行SQL初始化脚本
    3. 验证初始化结果
    """
    logger.info("=" * 60)
    logger.info("智法通 - 数据库初始化脚本")
    logger.info("=" * 60)

    # 步骤1: 等待MySQL服务就绪
    if not wait_for_mysql():
        logger.error("MySQL服务未就绪，初始化终止")
        sys.exit(1)

    # 步骤2: 连接数据库并执行SQL
    try:
        # 先不指定数据库连接，用于创建数据库
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            charset=DB_CONFIG['charset'],
            cursorclass=pymysql.cursors.DictCursor,
        )
        logger.info("数据库连接成功")

        # 执行SQL初始化脚本
        logger.info("-" * 40)
        success = execute_sql_file(connection, SQL_FILE_PATH)

        if not success:
            logger.warning("部分SQL语句执行出错，但将继续验证")

        # 步骤3: 验证初始化结果
        logger.info("-" * 40)
        # 切换到目标数据库
        connection.select_db(DB_CONFIG['database'])
        verified = verify_initialization(connection)

        # 关闭连接
        connection.close()
        logger.info("数据库连接已关闭")

    except pymysql.err.Error as e:
        logger.error(f"数据库操作失败: {e}")
        sys.exit(1)

    # 输出最终结果
    logger.info("=" * 60)
    if verified:
        logger.info("✓ 数据库初始化完成，所有验证通过！")
        logger.info("  默认管理员: admin / admin123")
        logger.info("  请在生产环境中修改默认密码！")
    else:
        logger.warning("⚠ 数据库初始化完成，但部分验证未通过，请检查日志")
    logger.info("=" * 60)

    sys.exit(0 if verified else 1)


# 脚本入口
if __name__ == '__main__':
    main()
