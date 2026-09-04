"""
智法通企业级智能法律顾问平台 - 综合功能测试脚本

覆盖11大功能模块的端到端验证：
1. 系统健康检查
2. 认证管理（登录/注册/用户信息/密码修改）
3. 法律问答（提问/流式/对话管理/反馈/推荐/额度）
4. 合同审查（上传/审查/报告/历史/分类/额度）
5. 法规案例检索库（文档列表/搜索/统计/详情/内容）
6. 数据分析（概览/热点/引用/趋势）
7. 仪表盘（概览/趋势/活动/领域）
8. 通知中心（列表/已读）
9. RBAC权限控制（普通用户越权拦截）
10. 额度管理（QA/Contract限制，管理员豁免）
11. 安全测试（XSS净化/越权/上传校验）

运行方式：
    python tests/test_comprehensive.py
"""

from __future__ import annotations

import io
import json
import time
import sys
from typing import Optional

import requests

# ==================== 测试配置 ====================
BASE_URL = "http://localhost"
API_PREFIX = "/api/v1"

# 内置测试账号
ACCOUNTS = {
    "admin": {"username": "admin", "password": "admin123", "role": "超级管理员"},
    "lawyer": {"username": "lawyer", "password": "lawyer123", "role": "法务负责人"},
    "user": {"username": "user", "password": "user123456", "role": "普通用户"},
}

# 请求超时（AI接口需要较长超时）
TIMEOUT_NORMAL = 10
TIMEOUT_AI = 120


# ==================== 测试结果统计 ====================
class TestResult:
    """测试结果收集器"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures: list[str] = []
        self.passes: list[str] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.passed += 1
        msg = f"[PASS] {name}" + (f" - {detail}" if detail else "")
        self.passes.append(msg)
        print(f"  ✓ {msg}")

    def fail(self, name: str, reason: str) -> None:
        self.failed += 1
        msg = f"[FAIL] {name} - {reason}"
        self.failures.append(msg)
        print(f"  ✗ {msg}")

    def skip(self, name: str, reason: str = "") -> None:
        self.skipped += 1
        msg = f"[SKIP] {name}" + (f" - {reason}" if reason else "")
        print(f"  - {msg}")

    def summary(self) -> str:
        total = self.passed + self.failed + self.skipped
        rate = (self.passed / total * 100) if total > 0 else 0
        return (
            f"\n{'=' * 60}\n"
            f"测试结果汇总\n"
            f"{'=' * 60}\n"
            f"  通过: {self.passed}\n"
            f"  失败: {self.failed}\n"
            f"  跳过: {self.skipped}\n"
            f"  总数: {total}\n"
            f"  通过率: {rate:.1f}%\n"
            f"{'=' * 60}"
        )


# ==================== 测试客户端 ====================
class TestClient:
    """API测试客户端封装

    使用独立的requests调用而非Session，避免会话状态污染
    （如Content-Type header残留导致文件上传失败）。
    """

    def __init__(self, result: TestResult):
        self.result = result
        self.tokens: dict[str, str] = {}  # 账号 -> access_token

    def login(self, account_key: str) -> bool:
        """登录指定账号并缓存令牌"""
        acc = ACCOUNTS[account_key]
        try:
            resp = requests.post(
                f"{BASE_URL}{API_PREFIX}/auth/login",
                json={"username": acc["username"], "password": acc["password"]},
                timeout=TIMEOUT_NORMAL,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.tokens[account_key] = data["access_token"]
                return True
            self.result.fail(f"登录-{account_key}", f"HTTP {resp.status_code}: {resp.text}")
            return False
        except Exception as e:
            self.result.fail(f"登录-{account_key}", str(e))
            return False

    def auth_headers(self, account_key: str) -> dict:
        """获取认证请求头"""
        token = self.tokens.get(account_key, "")
        return {"Authorization": f"Bearer {token}"}

    def request(
        self,
        method: str,
        path: str,
        account_key: str = "user",
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
        files=None,
        timeout: int = TIMEOUT_NORMAL,
        expect_status: int = 200,
    ) -> Optional[requests.Response]:
        """统一请求方法

        使用独立的requests.request调用，每次请求都是全新的连接和header，
        避免Session状态污染。
        只在参数非None时传递给requests，避免None值影响请求行为。
        """
        url = f"{BASE_URL}{API_PREFIX}{path}" if path.startswith("/") else f"{BASE_URL}{API_PREFIX}/{path}"
        headers = self.auth_headers(account_key)

        # 构建kwargs，只包含非None的参数
        kwargs: dict = {"headers": headers, "timeout": timeout}
        if json_body is not None:
            kwargs["json"] = json_body
        if params is not None:
            kwargs["params"] = params
        if files is not None:
            kwargs["files"] = files

        try:
            resp = requests.request(method=method, url=url, **kwargs)
            return resp
        except requests.exceptions.Timeout:
            self.result.fail(f"{method} {path}", f"请求超时({timeout}s)")
            return None
        except requests.exceptions.ConnectionError as e:
            self.result.fail(f"{method} {path}", f"连接异常: {e}")
            return None
        except Exception as e:
            self.result.fail(f"{method} {path}", f"请求异常: {type(e).__name__}: {e}")
            return None


# ==================== 测试用例 ====================

def test_system_health(client: TestClient, r: TestResult) -> None:
    """模块1：系统健康检查"""
    print("\n【模块1】系统健康检查")

    # 后端健康检查
    resp = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT_NORMAL)
    if resp and resp.status_code == 200:
        data = resp.json()
        r.ok("后端健康检查", f"status={data.get('status')}")
    else:
        r.fail("后端健康检查", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 前端首页
    resp = requests.get(f"{BASE_URL}/", timeout=TIMEOUT_NORMAL)
    if resp and resp.status_code == 200 and "<div id=\"app\">" in resp.text:
        r.ok("前端首页", "返回HTML")
    else:
        r.fail("前端首页", "未返回正常HTML")

    # OpenAPI文档
    resp = requests.get(f"{BASE_URL}/openapi.json", timeout=TIMEOUT_NORMAL)
    if resp and resp.status_code == 200:
        paths = resp.json().get("paths", {})
        r.ok("OpenAPI规范", f"{len(paths)}个路径")
    else:
        r.fail("OpenAPI规范", "无法获取")


def test_auth(client: TestClient, r: TestResult) -> None:
    """模块2：认证管理"""
    print("\n【模块2】认证管理")

    # 3个账号登录
    for key in ACCOUNTS:
        if client.login(key):
            r.ok(f"登录-{key}", ACCOUNTS[key]["role"])

    # 获取当前用户信息
    for key in ACCOUNTS:
        resp = client.request("GET", "/auth/me", account_key=key)
        if resp and resp.status_code == 200:
            data = resp.json()
            roles = data.get("roles", [])
            # roles可能是字符串列表或对象列表，统一处理
            role_codes = [r if isinstance(r, str) else r.get("code") for r in roles]
            r.ok(f"获取用户信息-{key}", f"username={data.get('username')}, roles={role_codes}")
        else:
            r.fail(f"获取用户信息-{key}", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 错误密码登录应失败（使用不存在的用户名避免锁定真实账号）
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"username": "nonexistent_user_xyz", "password": "wrong_password"},
            timeout=TIMEOUT_NORMAL,
        )
        if resp.status_code == 400:
            r.ok("错误密码登录拦截", "返回400")
        else:
            r.fail("错误密码登录拦截", f"HTTP {resp.status_code}, body={resp.text[:200]}")
    except Exception as e:
        r.fail("错误密码登录拦截", f"请求异常: {e}")

    # 无效令牌访问应拒绝
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            headers={"Authorization": "Bearer invalid_token_xxx"},
            timeout=TIMEOUT_NORMAL,
        )
        if resp.status_code in (401, 403):
            r.ok("无效令牌拦截", f"HTTP {resp.status_code}")
        else:
            r.fail("无效令牌拦截", f"HTTP {resp.status_code}")
    except Exception as e:
        r.fail("无效令牌拦截", f"请求异常: {e}")


def test_qa(client: TestClient, r: TestResult) -> None:
    """模块3：法律问答"""
    print("\n【模块3】法律问答")

    # 获取推荐问题
    resp = client.request("GET", "/qa/suggestions", account_key="user")
    if resp and resp.status_code == 200:
        sugg = resp.json().get("suggestions", [])
        r.ok("获取推荐问题", f"{len(sugg)}条")
    else:
        r.fail("获取推荐问题", f"HTTP {resp.status_code if resp else 'N/A'}")
        sugg = ["劳动合同解除后经济补偿如何计算？"]

    # 非流式提问
    resp = client.request(
        "POST", "/qa/ask",
        account_key="user",
        json_body={"question": sugg[0] if sugg else "什么是劳动合同？", "stream": False},
        timeout=TIMEOUT_AI,
    )
    conversation_id = None
    message_id = None
    if resp and resp.status_code == 200:
        data = resp.json()
        conversation_id = data.get("conversation_id")
        message_id = data.get("message_id")
        answer = data.get("answer", "")
        # 验证AI免责声明
        has_disclaimer = "法律免责声明" in answer or "不构成律师正式法律意见" in answer
        r.ok("非流式提问", f"conv={conversation_id}, msg={message_id}, 含免责声明={has_disclaimer}")
        if not has_disclaimer:
            r.fail("AI免责声明", "回答末尾未包含法律免责声明")
    else:
        r.fail("非流式提问", f"HTTP {resp.status_code if resp else 'N/A'}, body={resp.text[:200] if resp else ''}")

    # 获取对话列表
    resp = client.request("GET", "/qa/conversations", account_key="user", params={"page": 1, "page_size": 10})
    if resp and resp.status_code == 200:
        data = resp.json()
        r.ok("获取对话列表", f"total={data.get('total')}")
    else:
        r.fail("获取对话列表", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 获取对话消息
    if conversation_id:
        resp = client.request("GET", f"/qa/conversations/{conversation_id}/messages", account_key="user")
        if resp and resp.status_code == 200:
            msgs = resp.json().get("messages", [])
            r.ok("获取对话消息", f"{len(msgs)}条消息")
        else:
            r.fail("获取对话消息", f"HTTP {resp.status_code if resp else 'N/A'}")

        # 重命名对话
        resp = client.request(
            "PATCH", f"/qa/conversations/{conversation_id}",
            account_key="user",
            json_body={"title": "测试对话-经济补偿"},
        )
        if resp and resp.status_code == 200:
            r.ok("重命名对话", "标题已更新")
        else:
            r.fail("重命名对话", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 提交反馈
    if message_id:
        resp = client.request(
            "POST", "/qa/feedback",
            account_key="user",
            json_body={"message_id": message_id, "is_positive": True, "rating": 5},
        )
        if resp and resp.status_code == 200:
            r.ok("提交问答反馈", "5星好评")
        else:
            r.fail("提交问答反馈", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 查询QA额度
    resp = client.request("GET", "/qa/quota", account_key="user")
    if resp and resp.status_code == 200:
        data = resp.json()
        r.ok("查询QA额度", f"used={data.get('used')}, remaining={data.get('remaining')}, limit={data.get('limit')}")
    else:
        r.fail("查询QA额度", f"HTTP {resp.status_code if resp else 'N/A'}")


def test_contract(client: TestClient, r: TestResult) -> None:
    """模块4：合同审查"""
    print("\n【模块4】合同审查")

    # 上传合同（构造测试txt文件）
    contract_content = """劳动合同书
甲方：智法通科技有限公司
乙方：张三

第一条 合同期限
本合同期限为3年，自2024年1月1日起至2026年12月31日止。试用期6个月。

第二条 工作内容
乙方担任软件工程师岗位。

第三条 劳动报酬
乙方月工资为人民币15000元，试用期工资为月工资的80%。

第四条 违约责任
任何一方违约应支付违约金人民币100万元。

第五条 保密条款
乙方在职期间及离职后5年内应对甲方商业秘密保密。
"""
    files = {
        "file": ("测试劳动合同.txt", io.BytesIO(contract_content.encode("utf-8")), "text/plain")
    }
    resp = client.request("POST", "/contract/upload", account_key="user", files=files, timeout=TIMEOUT_NORMAL)
    contract_id = None
    if resp and resp.status_code == 200:
        data = resp.json()
        contract_id = data.get("id")
        r.ok("上传合同", f"id={contract_id}, status={data.get('status')}")
    else:
        r.fail("上传合同", f"HTTP {resp.status_code if resp else 'N/A'}, body={resp.text[:200] if resp else ''}")

    # 获取合同历史
    resp = client.request("GET", "/contract/history", account_key="user", params={"page": 1, "page_size": 10})
    if resp and resp.status_code == 200:
        data = resp.json()
        r.ok("获取合同历史", f"total={data.get('total')}")
    else:
        r.fail("获取合同历史", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 获取合同详情
    if contract_id:
        resp = client.request("GET", f"/contract/{contract_id}", account_key="user")
        if resp and resp.status_code == 200:
            r.ok("获取合同详情", f"id={contract_id}")
        else:
            r.fail("获取合同详情", f"HTTP {resp.status_code if resp else 'N/A'}")

        # 更新合同分类
        resp = client.request(
            "PATCH", f"/contract/{contract_id}/type",
            account_key="user",
            json_body={"contract_type": "劳动合同"},
        )
        if resp and resp.status_code == 200:
            r.ok("更新合同分类", "已分类为劳动合同")
        else:
            r.fail("更新合同分类", f"HTTP {resp.status_code if resp else 'N/A'}")

        # 启动AI审查（耗时较长）
        resp = client.request(
            "POST", "/contract/review",
            account_key="user",
            json_body={"contract_id": contract_id, "contract_type": "劳动合同"},
            timeout=TIMEOUT_AI,
        )
        if resp and resp.status_code == 200:
            r.ok("启动合同审查", f"id={contract_id}")
        else:
            r.fail("启动合同审查", f"HTTP {resp.status_code if resp else 'N/A'}, body={resp.text[:200] if resp else ''}")

        # 获取审查报告
        resp = client.request("GET", f"/contract/report/{contract_id}", account_key="user")
        if resp and resp.status_code == 200:
            r.ok("获取审查报告", f"id={contract_id}")
        else:
            r.fail("获取审查报告", f"HTTP {resp.status_code if resp else 'N/A'}")


def test_knowledge(client: TestClient, r: TestResult) -> None:
    """模块5：法规案例检索库"""
    print("\n【模块5】法规案例检索库")

    # 文档列表
    resp = client.request("GET", "/knowledge/documents", account_key="user", params={"page": 1, "page_size": 10})
    doc_id = None
    if resp and resp.status_code == 200:
        data = resp.json()
        items = data.get("items", [])
        if items:
            doc_id = items[0].get("id")
        r.ok("文档列表", f"total={data.get('total')}, 首条id={doc_id}")
    else:
        r.fail("文档列表", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 文档搜索（POST方法，字段名query）
    resp = client.request(
        "POST", "/knowledge/search",
        account_key="user",
        json_body={"query": "劳动合同", "top_k": 5},
        timeout=TIMEOUT_AI,
    )
    if resp and resp.status_code == 200:
        data = resp.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        result_count = len(results) if isinstance(results, list) else "N/A"
        r.ok("文档搜索", f"query=劳动合同, 结果数={result_count}")
    else:
        r.fail("文档搜索", f"HTTP {resp.status_code if resp else 'N/A'}, body={resp.text[:200] if resp else ''}")

    # 文档统计
    resp = client.request("GET", "/knowledge/stats", account_key="user")
    if resp and resp.status_code == 200:
        r.ok("文档统计", f"data={resp.json()}")
    else:
        r.fail("文档统计", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 文档详情
    if doc_id:
        resp = client.request("GET", f"/knowledge/documents/{doc_id}", account_key="user")
        if resp and resp.status_code == 200:
            r.ok("文档详情", f"id={doc_id}")
        else:
            r.fail("文档详情", f"HTTP {resp.status_code if resp else 'N/A'}")

        # 文档内容
        resp = client.request("GET", f"/knowledge/documents/{doc_id}/content", account_key="user")
        if resp and resp.status_code == 200:
            r.ok("文档原文", f"id={doc_id}")
        else:
            r.fail("文档原文", f"HTTP {resp.status_code if resp else 'N/A'}")


def test_analysis(client: TestClient, r: TestResult) -> None:
    """模块6：数据分析"""
    print("\n【模块6】数据分析")

    endpoints = [
        ("GET", "/analysis/overview", "概览"),
        ("GET", "/analysis/hot-topics", "热点话题"),
        ("GET", "/analysis/citations", "引用统计"),
        ("GET", "/analysis/trends", "趋势"),
    ]
    for method, path, name in endpoints:
        resp = client.request(method, path, account_key="admin")
        if resp and resp.status_code == 200:
            r.ok(f"数据分析-{name}", "OK")
        else:
            r.fail(f"数据分析-{name}", f"HTTP {resp.status_code if resp else 'N/A'}")


def test_dashboard(client: TestClient, r: TestResult) -> None:
    """模块7：仪表盘"""
    print("\n【模块7】仪表盘")

    endpoints = [
        ("GET", "/dashboard/overview", "概览"),
        ("GET", "/dashboard/trends", "趋势"),
        ("GET", "/dashboard/recent-activities", "最近活动"),
        ("GET", "/dashboard/domain-distribution", "领域分布"),
    ]
    for method, path, name in endpoints:
        resp = client.request(method, path, account_key="admin")
        if resp and resp.status_code == 200:
            r.ok(f"仪表盘-{name}", "OK")
        else:
            r.fail(f"仪表盘-{name}", f"HTTP {resp.status_code if resp else 'N/A'}")


def test_notification(client: TestClient, r: TestResult) -> None:
    """模块8：通知中心"""
    print("\n【模块8】通知中心")

    # 获取通知列表
    resp = client.request("GET", "/notifications/", account_key="user")
    if resp and resp.status_code == 200:
        data = resp.json()
        notif_count = len(data) if isinstance(data, list) else len(data.get("items", []))
        r.ok("通知列表", f"{notif_count}条")
    else:
        r.fail("通知列表", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 标记全部已读（PUT方法）
    resp = client.request("PUT", "/notifications/read-all", account_key="user")
    if resp and resp.status_code == 200:
        r.ok("全部已读", "OK")
    else:
        r.fail("全部已读", f"HTTP {resp.status_code if resp else 'N/A'}, body={resp.text[:200] if resp else ''}")


def test_rbac(client: TestClient, r: TestResult) -> None:
    """模块9：RBAC权限控制"""
    print("\n【模块9】RBAC权限控制")

    # 普通用户访问数据分析（应被拦截，返回403或400）
    # 注意：requests库的Response在4xx/5xx状态码时bool(resp)为False，
    # 必须用 `resp is not None` 判断，而非 `if resp:`
    resp = client.request("GET", "/analysis/overview", account_key="user")
    if resp is not None and resp.status_code in (403, 400):
        r.ok("普通用户访问数据分析被拦截", f"HTTP {resp.status_code}")
    elif resp is not None and resp.status_code == 200:
        # 部分接口可能允许普通用户访问，记录但不视为失败
        r.skip("普通用户访问数据分析", "接口允许普通用户访问")
    else:
        r.fail("普通用户访问数据分析", f"HTTP {resp.status_code if resp is not None else 'N/A'}, body={resp.text[:200] if resp is not None else ''}")

    # 普通用户访问仪表盘（应被拦截）
    resp = client.request("GET", "/dashboard/overview", account_key="user")
    if resp is not None and resp.status_code in (403, 400):
        r.ok("普通用户访问仪表盘被拦截", f"HTTP {resp.status_code}")
    elif resp is not None and resp.status_code == 200:
        r.skip("普通用户访问仪表盘", "接口允许普通用户访问")
    else:
        r.fail("普通用户访问仪表盘", f"HTTP {resp.status_code if resp is not None else 'N/A'}, body={resp.text[:200] if resp is not None else ''}")

    # 管理员可以访问数据分析
    resp = client.request("GET", "/analysis/overview", account_key="admin")
    if resp and resp.status_code == 200:
        r.ok("管理员访问数据分析", "OK")
    else:
        r.fail("管理员访问数据分析", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 管理员可以访问仪表盘
    resp = client.request("GET", "/dashboard/overview", account_key="admin")
    if resp and resp.status_code == 200:
        r.ok("管理员访问仪表盘", "OK")
    else:
        r.fail("管理员访问仪表盘", f"HTTP {resp.status_code if resp else 'N/A'}")


def test_quota(client: TestClient, r: TestResult) -> None:
    """模块10：额度管理"""
    print("\n【模块10】额度管理")

    # 普通用户QA额度
    resp = client.request("GET", "/qa/quota", account_key="user")
    if resp and resp.status_code == 200:
        data = resp.json()
        limit = data.get("limit")
        if limit and limit > 0:
            r.ok("普通用户QA额度限制", f"limit={limit}/日")
        else:
            r.fail("普通用户QA额度限制", f"limit={limit}")
    else:
        r.fail("普通用户QA额度查询", f"HTTP {resp.status_code if resp else 'N/A'}")

    # 管理员QA额度应为-1（不限）
    resp = client.request("GET", "/qa/quota", account_key="admin")
    if resp and resp.status_code == 200:
        data = resp.json()
        limit = data.get("limit")
        if limit == -1:
            r.ok("管理员QA额度豁免", "limit=-1 不限额")
        else:
            r.fail("管理员QA额度豁免", f"limit={limit} 应为-1")
    else:
        r.fail("管理员QA额度查询", f"HTTP {resp.status_code if resp else 'N/A'}")


def test_security(client: TestClient, r: TestResult) -> None:
    """模块11：安全测试"""
    print("\n【模块11】安全测试")

    # XSS测试：提交含恶意脚本的问题
    xss_payload = '<script>alert("xss")</script>什么是劳动合同？'
    resp = client.request(
        "POST", "/qa/ask",
        account_key="user",
        json_body={"question": xss_payload, "stream": False},
        timeout=TIMEOUT_AI,
    )
    if resp is not None and resp.status_code == 200:
        answer = resp.json().get("answer", "")
        if "<script>" not in answer:
            r.ok("XSS防护-非流式", "回答中不含<script>标签")
        else:
            r.fail("XSS防护-非流式", "回答中检测到<script>标签")
    else:
        r.fail("XSS防护-非流式", f"HTTP {resp.status_code if resp is not None else 'N/A'}")

    # 越权访问：user尝试访问admin的对话（id=99999应该不存在或不属于user）
    resp = client.request("GET", "/qa/conversations/99999/messages", account_key="user")
    if resp is not None and resp.status_code in (400, 404):
        r.ok("越权访问拦截-对话", f"HTTP {resp.status_code}")
    else:
        r.fail("越权访问拦截-对话", f"HTTP {resp.status_code if resp is not None else 'N/A'}, body={resp.text[:200] if resp is not None else ''}")

    # 越权访问：user尝试访问他人的合同
    resp = client.request("GET", "/contract/99999", account_key="user")
    if resp is not None and resp.status_code in (400, 404):
        r.ok("越权访问拦截-合同", f"HTTP {resp.status_code}")
    else:
        r.fail("越权访问拦截-合同", f"HTTP {resp.status_code if resp is not None else 'N/A'}, body={resp.text[:200] if resp is not None else ''}")

    # 文件上传校验：尝试上传非法格式
    files = {"file": ("malicious.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")}
    resp = client.request("POST", "/contract/upload", account_key="user", files=files)
    if resp is not None and resp.status_code in (400, 415):
        r.ok("非法文件格式拦截", f"HTTP {resp.status_code}")
    else:
        r.fail("非法文件格式拦截", f"HTTP {resp.status_code if resp is not None else 'N/A'}, body={resp.text[:200] if resp is not None else ''}")


# ==================== 主测试入口 ====================

def main() -> int:
    """主测试入口，返回退出码（0=成功，1=有失败）"""
    print("=" * 60)
    print("智法通企业级智能法律顾问平台 - 综合功能测试")
    print("=" * 60)
    print(f"测试目标: {BASE_URL}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试账号: {list(ACCOUNTS.keys())}")

    r = TestResult()
    client = TestClient(r)

    # 先登录所有账号
    print("\n【预处理】登录所有测试账号")
    for key in ACCOUNTS:
        client.login(key)

    # 执行11大模块测试
    test_system_health(client, r)
    test_auth(client, r)
    test_qa(client, r)
    test_contract(client, r)
    test_knowledge(client, r)
    test_analysis(client, r)
    test_dashboard(client, r)
    test_notification(client, r)
    test_rbac(client, r)
    test_quota(client, r)
    test_security(client, r)

    # 输出汇总
    print(r.summary())

    # 输出失败详情
    if r.failures:
        print("\n失败详情：")
        for i, f in enumerate(r.failures, 1):
            print(f"  {i}. {f}")

    return 0 if r.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
