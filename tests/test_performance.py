"""
智法通企业级智能法律顾问平台 - 性能与用户体验测试脚本

测试内容：
1. 关键接口响应时间（P50/P95/P99）
2. 并发登录承载能力
3. AI问答端到端耗时
4. 前端首屏加载性能
5. 容器资源占用

运行方式：
    python tests/test_performance.py
"""

from __future__ import annotations

import concurrent.futures
import json
import statistics
import sys
import time
from typing import Optional

import requests

# ==================== 配置 ====================
BASE_URL = "http://localhost"
API_PREFIX = "/api/v1"
TIMEOUT = 30
CONCURRENT_USERS = 10  # 并发用户数
LOGIN_ROUNDS = 5       # 并发登录轮次

ACCOUNTS = {
    "admin": {"username": "admin", "password": "admin123"},
    "lawyer": {"username": "lawyer", "password": "lawyer123"},
    "user": {"username": "user", "password": "user123456"},
}


def measure_latency(func, repeats: int = 5) -> dict:
    """测量函数执行耗时（毫秒）

    Args:
        func: 待测函数（无参数，返回Response或None）
        repeats: 重复次数

    Returns:
        包含P50/P95/P99/平均/最小/最大的字典
    """
    latencies = []
    for _ in range(repeats):
        start = time.perf_counter()
        try:
            func()
        except Exception:
            pass
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

    latencies.sort()
    n = len(latencies)
    p50_idx = int(n * 0.5)
    p95_idx = int(n * 0.95)
    p99_idx = int(n * 0.99)

    return {
        "count": n,
        "avg_ms": round(statistics.mean(latencies), 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "p50_ms": round(latencies[p50_idx], 2),
        "p95_ms": round(latencies[min(p95_idx, n-1)], 2),
        "p99_ms": round(latencies[min(p99_idx, n-1)], 2),
    }


def get_token(account_key: str = "user") -> Optional[str]:
    """获取指定账号的访问令牌"""
    acc = ACCOUNTS[account_key]
    resp = requests.post(
        f"{BASE_URL}{API_PREFIX}/auth/login",
        json={"username": acc["username"], "password": acc["password"]},
        timeout=TIMEOUT,
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    return None


def test_api_latency():
    """测试1：关键API响应时间"""
    print("\n【测试1】关键API响应时间")
    print("-" * 70)

    token = get_token("user")
    headers = {"Authorization": f"Bearer {token}"}

    # 测试用例：(名称, 请求函数)
    test_cases = [
        ("后端健康检查 /health", lambda: requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)),
        ("前端首页 /", lambda: requests.get(f"{BASE_URL}/", timeout=TIMEOUT)),
        ("OpenAPI规范 /openapi.json", lambda: requests.get(f"{BASE_URL}/openapi.json", timeout=TIMEOUT)),
        ("获取用户信息 /auth/me", lambda: requests.get(f"{BASE_URL}{API_PREFIX}/auth/me", headers=headers, timeout=TIMEOUT)),
        ("QA额度查询 /qa/quota", lambda: requests.get(f"{BASE_URL}{API_PREFIX}/qa/quota", headers=headers, timeout=TIMEOUT)),
        ("QA推荐问题 /qa/suggestions", lambda: requests.get(f"{BASE_URL}{API_PREFIX}/qa/suggestions", headers=headers, timeout=TIMEOUT)),
        ("QA对话列表 /qa/conversations", lambda: requests.get(f"{BASE_URL}{API_PREFIX}/qa/conversations", headers=headers, timeout=TIMEOUT)),
        ("合同历史 /contract/history", lambda: requests.get(f"{BASE_URL}{API_PREFIX}/contract/history", headers=headers, timeout=TIMEOUT)),
        ("知识库文档 /knowledge/documents", lambda: requests.get(f"{BASE_URL}{API_PREFIX}/knowledge/documents", headers=headers, timeout=TIMEOUT)),
        ("知识库统计 /knowledge/stats", lambda: requests.get(f"{BASE_URL}{API_PREFIX}/knowledge/stats", headers=headers, timeout=TIMEOUT)),
        ("通知列表 /notifications/", lambda: requests.get(f"{BASE_URL}{API_PREFIX}/notifications/", headers=headers, timeout=TIMEOUT)),
    ]

    results = []
    for name, func in test_cases:
        stats = measure_latency(func, repeats=5)
        results.append((name, stats))
        # 性能等级判定：P95 < 500ms 优秀；< 1s 良好；< 2s 可接受；≥ 2s 需优化
        p95 = stats["p95_ms"]
        if p95 < 500:
            grade = "★优秀"
        elif p95 < 1000:
            grade = "良好"
        elif p95 < 2000:
            grade = "可接受"
        else:
            grade = "需优化"
        print(f"  {name:<40} avg={stats['avg_ms']:>8.2f}ms  P50={stats['p50_ms']:>8.2f}ms  P95={stats['p95_ms']:>8.2f}ms  [{grade}]")

    return results


def test_concurrent_login():
    """测试2：并发登录承载能力"""
    print("\n【测试2】并发登录承载能力")
    print("-" * 70)
    print(f"  并发用户数: {CONCURRENT_USERS}")
    print(f"  测试轮次: {LOGIN_ROUNDS}")

    all_latencies = []
    success_count = 0
    fail_count = 0

    def login_once(_):
        """单次登录"""
        start = time.perf_counter()
        try:
            resp = requests.post(
                f"{BASE_URL}{API_PREFIX}/auth/login",
                json={"username": "user", "password": "user123456"},
                timeout=TIMEOUT,
            )
            elapsed = (time.perf_counter() - start) * 1000
            if resp.status_code == 200:
                return (True, elapsed)
            return (False, elapsed)
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            return (False, elapsed)

    for round_idx in range(LOGIN_ROUNDS):
        round_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
            futures = [executor.submit(login_once, i) for i in range(CONCURRENT_USERS)]
            for f in concurrent.futures.as_completed(futures):
                ok, lat = f.result()
                all_latencies.append(lat)
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
        round_elapsed = (time.perf_counter() - round_start) * 1000
        print(f"  第{round_idx+1}轮: {CONCURRENT_USERS}并发  耗时={round_elapsed:.2f}ms")

    all_latencies.sort()
    n = len(all_latencies)
    total = success_count + fail_count
    success_rate = (success_count / total * 100) if total > 0 else 0

    print(f"\n  汇总:")
    print(f"    总请求数: {total}")
    print(f"    成功: {success_count} ({success_rate:.1f}%)")
    print(f"    失败: {fail_count}")
    print(f"    平均耗时: {statistics.mean(all_latencies):.2f}ms")
    print(f"    P50: {all_latencies[n//2]:.2f}ms")
    print(f"    P95: {all_latencies[int(n*0.95)]:.2f}ms")
    print(f"    最快: {min(all_latencies):.2f}ms")
    print(f"    最慢: {max(all_latencies):.2f}ms")

    return {
        "total": total,
        "success": success_count,
        "fail": fail_count,
        "success_rate": success_rate,
        "avg_ms": statistics.mean(all_latencies),
        "p50_ms": all_latencies[n//2],
        "p95_ms": all_latencies[int(n*0.95)],
    }


def test_ai_qa_latency():
    """测试3：AI问答端到端耗时"""
    print("\n【测试3】AI问答端到端耗时")
    print("-" * 70)

    token = get_token("user")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    questions = [
        "什么是劳动合同？",
        "经济补偿金如何计算？",
        "格式条款无效的情形有哪些？",
    ]

    latencies = []
    for i, q in enumerate(questions):
        start = time.perf_counter()
        try:
            resp = requests.post(
                f"{BASE_URL}{API_PREFIX}/qa/ask",
                json={"question": q, "stream": False},
                headers=headers,
                timeout=120,
            )
            elapsed = (time.perf_counter() - start) * 1000
            status = "成功" if resp.status_code == 200 else f"失败({resp.status_code})"
            answer_len = len(resp.json().get("answer", "")) if resp.status_code == 200 else 0
            latencies.append(elapsed)
            print(f"  问题{i+1}: {q}")
            print(f"    状态: {status}, 耗时: {elapsed:.2f}ms, 回答长度: {answer_len}字符")
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            print(f"  问题{i+1}: {q}")
            print(f"    异常: {e}, 耗时: {elapsed:.2f}ms")

    if latencies:
        print(f"\n  汇总:")
        print(f"    平均耗时: {statistics.mean(latencies):.2f}ms")
        print(f"    最快: {min(latencies):.2f}ms")
        print(f"    最慢: {max(latencies):.2f}ms")

    return {
        "avg_ms": statistics.mean(latencies) if latencies else 0,
        "min_ms": min(latencies) if latencies else 0,
        "max_ms": max(latencies) if latencies else 0,
    }


def test_frontend_performance():
    """测试4：前端首屏加载性能"""
    print("\n【测试4】前端首屏加载性能")
    print("-" * 70)

    # 测量首页HTML大小和加载时间
    stats = measure_latency(
        lambda: requests.get(f"{BASE_URL}/", timeout=TIMEOUT),
        repeats=5,
    )

    # 获取首页大小
    resp = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
    html_size = len(resp.content)

    print(f"  首页HTML大小: {html_size:,} 字节 ({html_size/1024:.2f} KB)")
    print(f"  首次加载平均: {stats['avg_ms']:.2f}ms")
    print(f"  P50: {stats['p50_ms']:.2f}ms")
    print(f"  P95: {stats['p95_ms']:.2f}ms")

    # 检查是否包含关键资源
    html = resp.text
    checks = [
        ("app挂载点 #app", "<div id=\"app\">" in html),
        ("加载占位 #app-loading", "app-loading" in html),
        ("Vue主脚本 main.ts", "main.ts" in html),
        ("UTF-8编码声明", 'charset="UTF-8"' in html or "charset=utf-8" in html.lower()),
        ("viewport移动适配", "viewport" in html),
    ]
    print(f"\n  首页内容检查:")
    for name, passed in checks:
        mark = "✓" if passed else "✗"
        print(f"    {mark} {name}")

    # 测试静态资源加载（CSS/JS）
    # 从HTML中提取资源引用
    import re
    js_files = re.findall(r'src="(/[^"]+\.js)"', html)
    css_files = re.findall(r'href="(/[^"]+\.css)"', html)

    print(f"\n  静态资源:")
    print(f"    JS文件数: {len(js_files)}")
    print(f"    CSS文件数: {len(css_files)}")

    if js_files:
        # 测试第一个JS文件加载时间
        js_url = f"{BASE_URL}{js_files[0]}"
        js_stats = measure_latency(lambda: requests.get(js_url, timeout=TIMEOUT), repeats=3)
        js_resp = requests.get(js_url, timeout=TIMEOUT)
        print(f"    首个JS: {js_files[0]}")
        print(f"      大小: {len(js_resp.content):,} 字节 ({len(js_resp.content)/1024:.2f} KB)")
        print(f"      加载P50: {js_stats['p50_ms']:.2f}ms")

    return stats


def test_container_resources():
    """测试5：容器资源占用"""
    print("\n【测试5】容器资源占用")
    print("-" * 70)

    import subprocess

    containers = ["zhifatong-mysql", "zhifatong-redis", "zhifatong-backend", "zhifatong-frontend"]
    results = []

    for name in containers:
        try:
            # 使用docker stats --no-stream获取单次快照
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format",
                 "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}",
                 name],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                line = result.stdout.strip().split("\t")
                if len(line) >= 6:
                    data = {
                        "name": line[0],
                        "cpu": line[1],
                        "mem_usage": line[2],
                        "mem_perc": line[3],
                        "net_io": line[4],
                        "block_io": line[5],
                    }
                    results.append(data)
                    print(f"  {data['name']:<25} CPU={data['cpu']:<8} 内存={data['mem_usage']:<20} ({data['mem_perc']})  网络={data['net_io']}")
        except Exception as e:
            print(f"  {name}: 获取资源占用失败 - {e}")

    return results


def main():
    print("=" * 70)
    print("智法通企业级智能法律顾问平台 - 性能与用户体验测试")
    print("=" * 70)
    print(f"测试目标: {BASE_URL}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"并发用户数: {CONCURRENT_USERS}")

    # 性能测试结果汇总
    all_results = {}

    # 1. API响应时间
    all_results["api_latency"] = test_api_latency()

    # 2. 并发登录
    all_results["concurrent_login"] = test_concurrent_login()

    # 3. AI问答耗时
    all_results["ai_qa"] = test_ai_qa_latency()

    # 4. 前端性能
    all_results["frontend"] = test_frontend_performance()

    # 5. 容器资源
    all_results["containers"] = test_container_resources()

    # 性能总结
    print("\n" + "=" * 70)
    print("性能测试总结")
    print("=" * 70)

    # API响应时间总结
    api_results = all_results["api_latency"]
    avg_p95 = statistics.mean([s["p95_ms"] for _, s in api_results])
    print(f"  API平均P95响应时间: {avg_p95:.2f}ms", end="")
    if avg_p95 < 500:
        print("  [优秀]")
    elif avg_p95 < 1000:
        print("  [良好]")
    else:
        print("  [需优化]")

    # 并发登录总结
    login = all_results["concurrent_login"]
    print(f"  并发登录成功率: {login['success_rate']:.1f}% ({login['success']}/{login['total']})")
    print(f"  并发登录P95耗时: {login['p95_ms']:.2f}ms")

    # AI问答总结
    ai = all_results["ai_qa"]
    print(f"  AI问答平均耗时: {ai['avg_ms']:.2f}ms")
    if ai['avg_ms'] < 5000:
        print("    [响应迅速]")
    elif ai['avg_ms'] < 15000:
        print("    [响应可接受]")
    else:
        print("    [响应较慢，建议优化模型]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
