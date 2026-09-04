"""
智法通 - 全面功能测试脚本
在Docker部署环境下测试所有API端点（通过Nginx反向代理）
覆盖: 功能测试 + 兼容性测试 + 性能测试 + 安全测试
"""
import requests
import json
import sys
import time
import traceback

# 测试配置 - 通过Nginx反向代理测试（验证完整链路: Nginx → Backend → DB）
BASE_URL = "http://localhost"
API_PREFIX = "/api/v1"
TIMEOUT = 30

# 测试结果统计
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "errors": []
}

def record_result(name, passed, detail=""):
    """记录测试结果"""
    test_results["total"] += 1
    if passed:
        test_results["passed"] += 1
        print(f"  ✅ {name}")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"{name}: {detail}")
        print(f"  ❌ {name} - {detail}")

def test_health():
    """测试健康检查"""
    print("\n📊 测试1: 健康检查")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            record_result("健康检查端点", data.get("status") == "healthy")
            record_result("应用名称", "智法通" in str(data.get("app_name", "")) or "app_name" in data)
        else:
            record_result("健康检查端点", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("健康检查端点", False, str(e))

def test_auth():
    """测试认证模块"""
    print("\n🔐 测试2: 认证模块")
    token = None
    
    # 测试登录
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            record_result("用户登录", token is not None)
        else:
            record_result("用户登录", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        record_result("用户登录", False, str(e))
    
    # 测试获取用户信息
    if token:
        try:
            resp = requests.get(
                f"{BASE_URL}{API_PREFIX}/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=TIMEOUT
            )
            if resp.status_code == 200:
                data = resp.json()
                record_result("获取用户信息", data.get("username") == "admin")
            else:
                record_result("获取用户信息", False, f"HTTP {resp.status_code}")
        except Exception as e:
            record_result("获取用户信息", False, str(e))
    
    # 测试注册
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/register",
            json={
                "username": f"testuser_{int(time.time())}",
                "email": f"test_{int(time.time())}@example.com",
                "password": "test123456"
            },
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            record_result("用户注册", data.get("access_token") is not None)
        else:
            record_result("用户注册", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        record_result("用户注册", False, str(e))
    
    return token

def test_qa(token):
    """测试法律问答模块"""
    print("\n⚖️ 测试3: 法律问答模块")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = None
    
    # 测试获取推荐问题
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/qa/suggestions",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            suggestions = data.get("suggestions", [])
            record_result("获取推荐问题", len(suggestions) > 0)
        else:
            record_result("获取推荐问题", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("获取推荐问题", False, str(e))
    
    # 测试获取对话列表
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/qa/conversations",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("获取对话列表", True)
        else:
            record_result("获取对话列表", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("获取对话列表", False, str(e))
    
    # 测试非流式问答
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/qa/ask",
            json={"question": "什么是格式条款？", "stream": False},
            headers=headers,
            timeout=120
        )
        if resp.status_code == 200:
            data = resp.json()
            conversation_id = data.get("conversation_id")
            answer = data.get("answer", "")
            citations = data.get("citations", [])
            confidence = data.get("confidence", 0)
            record_result("非流式问答-回答", len(answer) > 10)
            record_result("非流式问答-对话ID", conversation_id is not None)
            record_result("非流式问答-置信度", confidence > 0)
        else:
            record_result("非流式问答", False, f"HTTP {resp.status_code}: {resp.text[:300]}")
    except Exception as e:
        record_result("非流式问答", False, str(e))
    
    # 测试流式问答
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/qa/ask/stream",
            json={"question": "劳动合同解除后经济补偿金如何计算？", "stream": True},
            headers=headers,
            timeout=120,
            stream=True
        )
        if resp.status_code == 200:
            content_received = False
            done_received = False
            for line in resp.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        done_received = True
                        break
                    try:
                        chunk = json.loads(data_str)
                        if chunk.get("type") == "content":
                            content_received = True
                    except:
                        pass
            record_result("流式问答-内容接收", content_received)
            record_result("流式问答-结束标记", done_received)
        else:
            record_result("流式问答", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("流式问答", False, str(e))
    
    return conversation_id

def test_contract(token):
    """测试合同审查模块"""
    print("\n📋 测试4: 合同审查模块")
    headers = {"Authorization": f"Bearer {token}"}
    contract_id = None
    
    # 测试获取合同历史
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/contract/history",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("获取合同历史", True)
        else:
            record_result("获取合同历史", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("获取合同历史", False, str(e))
    
    # 测试上传合同
    try:
        # 创建一个简单的测试合同文件
        contract_content = """房屋租赁合同

出租方（甲方）：张三
承租方（乙方）：李四

第一条 租赁物
甲方将位于某市某区某路某号的房屋出租给乙方使用。

第二条 租赁期限
租赁期限为一年，自2024年1月1日起至2024年12月31日止。

第三条 租金
月租金为人民币5000元，乙方应于每月5日前支付。

第四条 押金
乙方应于合同签订时支付押金10000元。

第五条 甲方责任
甲方应保证房屋适合居住。

第六条 乙方责任
乙方应按时支付租金。

第七条 违约责任
乙方逾期支付租金的，应按日支付违约金。
甲方可以随时解除合同，无需承担任何违约责任。

第八条 争议解决
本合同争议由甲方所在地人民法院管辖。

第九条 其他
本合同最终解释权归甲方所有。
"""
        files = {
            "file": ("test_contract.txt", contract_content.encode("utf-8"), "text/plain")
        }
        data = {"title": "测试房屋租赁合同"}
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/contract/upload",
            files=files,
            data=data,
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            result = resp.json()
            contract_id = result.get("id")
            record_result("上传合同", contract_id is not None)
        else:
            record_result("上传合同", False, f"HTTP {resp.status_code}: {resp.text[:300]}")
    except Exception as e:
        record_result("上传合同", False, str(e))
    
    # 测试获取合同详情
    if contract_id:
        try:
            resp = requests.get(
                f"{BASE_URL}{API_PREFIX}/contract/{contract_id}",
                headers=headers,
                timeout=TIMEOUT
            )
            if resp.status_code == 200:
                record_result("获取合同详情", True)
            else:
                record_result("获取合同详情", False, f"HTTP {resp.status_code}")
        except Exception as e:
            record_result("获取合同详情", False, str(e))
    
    return contract_id

def test_knowledge(token):
    """测试知识库模块"""
    print("\n📚 测试5: 知识库模块")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试获取文档列表
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/knowledge/documents",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("获取文档列表", True)
        else:
            record_result("获取文档列表", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("获取文档列表", False, str(e))
    
    # 测试获取知识库统计
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/knowledge/stats",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            record_result("知识库统计", data.get("total_documents", 0) > 0)
        else:
            record_result("知识库统计", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("知识库统计", False, str(e))
    
    # 测试语义搜索
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/knowledge/search",
            json={"query": "经济补偿金", "top_k": 3},
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("语义搜索", True)
        else:
            record_result("语义搜索", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        record_result("语义搜索", False, str(e))

def test_analysis(token):
    """测试数据分析模块"""
    print("\n📊 测试6: 数据分析模块")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试热点分析
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/analysis/hot-topics?days=30",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("热点分析", True)
        else:
            record_result("热点分析", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("热点分析", False, str(e))
    
    # 测试引用统计
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/analysis/citations?days=30",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("引用统计", True)
        else:
            record_result("引用统计", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("引用统计", False, str(e))
    
    # 测试用户聚类
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/analysis/user-clusters?days=30",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("用户聚类", True)
        else:
            record_result("用户聚类", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("用户聚类", False, str(e))
    
    # 测试趋势数据
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/analysis/trends?start_date=2026-01-01&end_date=2026-06-19&granularity=month",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("趋势数据", True)
        else:
            record_result("趋势数据", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("趋势数据", False, str(e))
    
    # 测试分析概览
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/analysis/overview",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("分析概览", True)
        else:
            record_result("分析概览", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("分析概览", False, str(e))

def test_dashboard(token):
    """测试仪表盘模块"""
    print("\n📈 测试7: 仪表盘模块")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试概览统计
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/dashboard/overview",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            record_result("概览统计", "total_users" in data)
        else:
            record_result("概览统计", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("概览统计", False, str(e))
    
    # 测试最近活动
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/dashboard/recent-activities?limit=5",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("最近活动", True)
        else:
            record_result("最近活动", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("最近活动", False, str(e))
    
    # 测试领域分布
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/dashboard/domain-distribution",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("领域分布", True)
        else:
            record_result("领域分布", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("领域分布", False, str(e))
    
    # 测试趋势数据
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/dashboard/trends?days=7",
            headers=headers,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            record_result("仪表盘趋势", True)
        else:
            record_result("仪表盘趋势", False, f"HTTP {resp.status_code}")
    except Exception as e:
        record_result("仪表盘趋势", False, str(e))

def test_security():
    """安全测试：弱密码防护、XSS防护、SQL注入防护、认证绕过"""
    print("\n🛡️ 测试8: 安全测试")
    
    # 测试弱密码注册被拒绝
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/register",
            json={
                "username": f"weak_{int(time.time())}",
                "email": f"weak_{int(time.time())}@example.com",
                "password": "password"
            },
            timeout=TIMEOUT
        )
        record_result("弱密码注册被拒绝", resp.status_code in (400, 422))
    except Exception as e:
        record_result("弱密码注册被拒绝", False, str(e))
    
    # 测试短密码注册被拒绝
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/register",
            json={
                "username": f"short_{int(time.time())}",
                "email": f"short_{int(time.time())}@example.com",
                "password": "123"
            },
            timeout=TIMEOUT
        )
        record_result("短密码注册被拒绝", resp.status_code in (400, 422))
    except Exception as e:
        record_result("短密码注册被拒绝", False, str(e))
    
    # 测试无Token访问受保护端点
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            timeout=TIMEOUT
        )
        record_result("无Token访问被拒绝", resp.status_code in (401, 403))
    except Exception as e:
        record_result("无Token访问被拒绝", False, str(e))
    
    # 测试无效Token访问
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            headers={"Authorization": "Bearer invalid_token_12345"},
            timeout=TIMEOUT
        )
        record_result("无效Token被拒绝", resp.status_code in (401, 403))
    except Exception as e:
        record_result("无效Token被拒绝", False, str(e))
    
    # 测试SQL注入防护（登录接口）
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"username": "admin' OR '1'='1", "password": "anything"},
            timeout=TIMEOUT
        )
        record_result("SQL注入防护", resp.status_code in (400, 401, 404, 422))
    except Exception as e:
        record_result("SQL注入防护", False, str(e))


def test_compatibility():
    """兼容性测试：不同Content-Type、CORS、错误格式"""
    print("\n🌐 测试9: 兼容性测试")
    
    # 测试CORS预检请求
    try:
        resp = requests.options(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            headers={
                "Origin": "http://localhost:80",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
            timeout=TIMEOUT
        )
        record_result("CORS预检请求", resp.status_code in (200, 204))
    except Exception as e:
        record_result("CORS预检请求", False, str(e))
    
    # 测试错误请求格式
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            data="not json",
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        record_result("错误格式处理", resp.status_code == 422)
    except Exception as e:
        record_result("错误格式处理", False, str(e))
    
    # 测试不存在的路由
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/nonexistent",
            timeout=TIMEOUT
        )
        record_result("404路由处理", resp.status_code == 404)
    except Exception as e:
        record_result("404路由处理", False, str(e))
    
    # 测试API文档可访问性
    try:
        resp = requests.get(f"{BASE_URL}/docs", timeout=TIMEOUT, allow_redirects=True)
        record_result("API文档可访问", resp.status_code == 200)
    except Exception as e:
        record_result("API文档可访问", False, str(e))
    
    # 测试OpenAPI规范可访问
    try:
        resp = requests.get(f"{BASE_URL}/openapi.json", timeout=TIMEOUT)
        record_result("OpenAPI规范可访问", resp.status_code == 200 and "openapi" in resp.text)
    except Exception as e:
        record_result("OpenAPI规范可访问", False, str(e))


def test_performance():
    """性能测试：响应时间测量"""
    print("\n⚡ 测试10: 性能测试")
    
    # 测试健康检查响应时间
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        elapsed = time.time() - start
        record_result("健康检查响应<500ms", elapsed < 0.5 and resp.status_code == 200)
    except Exception as e:
        record_result("健康检查响应<500ms", False, str(e))
    
    # 测试登录响应时间
    try:
        start = time.time()
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=TIMEOUT
        )
        elapsed = time.time() - start
        record_result("登录响应<2s", elapsed < 2.0 and resp.status_code == 200)
    except Exception as e:
        record_result("登录响应<2s", False, str(e))
    
    # 测试仪表盘响应时间
    token = None
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token")
    except:
        pass
    
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试仪表盘概览响应时间
        try:
            start = time.time()
            resp = requests.get(
                f"{BASE_URL}{API_PREFIX}/dashboard/overview",
                headers=headers,
                timeout=TIMEOUT
            )
            elapsed = time.time() - start
            record_result("仪表盘响应<1s", elapsed < 1.0 and resp.status_code == 200)
        except Exception as e:
            record_result("仪表盘响应<1s", False, str(e))
        
        # 测试知识库列表响应时间
        try:
            start = time.time()
            resp = requests.get(
                f"{BASE_URL}{API_PREFIX}/knowledge/documents",
                headers=headers,
                timeout=TIMEOUT
            )
            elapsed = time.time() - start
            record_result("知识库列表响应<1s", elapsed < 1.0 and resp.status_code == 200)
        except Exception as e:
            record_result("知识库列表响应<1s", False, str(e))


def main():
    """主测试函数"""
    print("=" * 60)
    print("  智法通 - 全面功能测试")
    print("=" * 60)
    print(f"  后端地址: {BASE_URL}")
    print(f"  测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 健康检查
    test_health()
    
    # 2. 认证模块
    token = test_auth()
    if not token:
        print("\n❌ 认证失败，无法继续测试")
        print_summary()
        return
    
    # 3. 法律问答
    test_qa(token)
    
    # 4. 合同审查
    test_contract(token)
    
    # 5. 知识库
    test_knowledge(token)
    
    # 6. 数据分析
    test_analysis(token)
    
    # 7. 仪表盘
    test_dashboard(token)
    
    # 8. 安全测试
    test_security()
    
    # 9. 兼容性测试
    test_compatibility()
    
    # 10. 性能测试
    test_performance()
    
    # 输出总结
    print_summary()

def print_summary():
    """输出测试总结"""
    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    print(f"  总测试数: {test_results['total']}")
    print(f"  通过: {test_results['passed']}")
    print(f"  失败: {test_results['failed']}")
    pass_rate = (test_results['passed'] / test_results['total'] * 100) if test_results['total'] > 0 else 0
    print(f"  通过率: {pass_rate:.1f}%")
    print("=" * 60)
    
    if test_results['errors']:
        print("\n  失败详情:")
        for err in test_results['errors']:
            print(f"    ❌ {err}")
    
    print()
    return test_results['failed'] == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
