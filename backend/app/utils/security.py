"""
智法通 - 安全工具模块

提供JWT令牌生成/验证和密码哈希/验证功能，
以及AI输出内容的XSS净化工具。
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import re

from app.config import settings


# ==================== XSS净化工具 ====================
# 以下正则用于中和AI回答中可能包含的危险HTML内容。
# 设计原则：defense-in-depth（前端已用DOMPurify二次净化，此处为后端兜底）。
# 保留合法的Markdown和HTML结构，仅中和会触发脚本执行的成分。

# 转义 <script> 与 </script> 标签（不区分大小写，含变体如 <script type=...>）
_SCRIPT_OPEN_RE = re.compile(r'<script', re.IGNORECASE)
_SCRIPT_CLOSE_RE = re.compile(r'</script>', re.IGNORECASE)
# 移除事件处理器属性：覆盖带引号、单引号和无引号三种形式
# 匹配: onerror="alert(1)" / onerror='alert(1)' / onerror=alert(1) / onerror=javascript:alert(1)
_EVENT_HANDLER_RE = re.compile(r'\son\w+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', re.IGNORECASE)
# 转义 <iframe>、<object>、<embed>、<svg> 等可执行脚本/加载外部资源的危险标签
_DANGEROUS_TAG_RE = re.compile(r'<(iframe|object|embed|svg)', re.IGNORECASE)
# 移除 javascript: 协议链接（防止 href="javascript:alert(1)"）
_JS_PROTOCOL_RE = re.compile(r'javascript\s*:', re.IGNORECASE)


def sanitize_html_content(text: str) -> str:
    """对AI回答进行XSS防护净化（后端兜底，前端已用DOMPurify二次净化）

    处理策略：
    1. 转义 <script> 标签（防止脚本执行），保留标签文本可见
    2. 移除事件处理器属性（onerror/onload/onclick 等，含无引号形式）
    3. 转义 <iframe>/<object>/<embed>/<svg> 等危险标签
    4. 移除 javascript: 协议链接

    保留合法的Markdown和HTML结构（如 <strong>、<table> 等），
    确保法条引用、表格等富文本展示正常。

    Args:
        text: 待处理的AI回答文本

    Returns:
        经过安全处理后的文本；输入为空则原样返回
    """
    if not text:
        return text
    # 1. 转义 <script> 与 </script> 标签
    text = _SCRIPT_OPEN_RE.sub('&lt;script', text)
    text = _SCRIPT_CLOSE_RE.sub('&lt;/script&gt;', text)
    # 2. 移除事件处理器属性（覆盖带引号、单引号、无引号三种形式）
    text = _EVENT_HANDLER_RE.sub('', text)
    # 3. 转义 <iframe>/<object>/<embed>/<svg> 等危险标签
    text = _DANGEROUS_TAG_RE.sub(r'&lt;\1', text)
    # 4. 移除 javascript: 协议
    text = _JS_PROTOCOL_RE.sub('', text)
    return text


# ==================== 密码哈希工具 ====================

def hash_password(password: str) -> str:
    """对明文密码进行哈希

    Args:
        password: 明文密码

    Returns:
        哈希后的密码字符串
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        密码是否匹配
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ==================== JWT令牌工具 ====================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建访问令牌

    Args:
        data: 令牌载荷数据（通常包含sub=用户ID）
        expires_delta: 过期时间增量

    Returns:
        JWT访问令牌字符串
    """
    to_encode = data.copy()
    to_encode["type"] = "access"

    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # 签发时间
    })

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建刷新令牌

    Args:
        data: 令牌载荷数据（通常包含sub=用户ID）
        expires_delta: 过期时间增量

    Returns:
        JWT刷新令牌字符串
    """
    to_encode = data.copy()
    to_encode["type"] = "refresh"

    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
    })

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> Optional[dict]:
    """解码并验证JWT令牌

    Args:
        token: JWT令牌字符串

    Returns:
        令牌载荷字典，验证失败返回None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None
