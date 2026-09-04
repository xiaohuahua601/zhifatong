#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智法通 V5.0 性能测试套件

测试维度:
1. API响应时间（P50/P95/P99，目标 P95 < 500ms）
2. 并发吞吐量（TPS，目标 > 1000）
3. 并发登录承载能力
4. AI推理端到端耗时
5. 前端首屏加载性能
6. 容器资源占用（CPU < 70%，内存 < 80%）

测试工具: 纯Python + requests + threading（不依赖JMeter/Gatling，便于在Conda base环境运行）
"""
import requests
import time
import json
import statistics
import threading
import concurrent.futures
import subprocess
import os
import asyncio
from datetime import datetime
from collections import defaultdict

# aiohttp 仅用于并发TPS测试（消除同步requests库的客户端瓶颈）
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

# ==================== 配置 ====================
BASE_URL = 'http://localhost:8000/api/v1'
FRONTEND_URL = 'http://localhost:8080'
TIMEOUT = 30
CONCURRENT_USERS = [1, 5, 10, 20, 50]  # 并发梯度
WARMUP_REQUESTS = 5  # 预热请求数（不计入统计）

# 测试结果
results = []
total_start = time.time()


def log_test(category, name, passed, metrics, detail=''):
    """记录性能测试结果"""
    status = 'PASS' if passed else 'FAIL'
    results.append({
        'category': category,
        'name': name,
        'status': status,
        'metrics': metrics,
        'detail': detail
    })
    mark = '✓' if passed else '✗'
    print(f'{mark} [{status}] {category} > {name}')
    if isinstance(metrics, dict):
        for k, v in metrics.items():
            print(f'          {k}: {v}')
    if detail:
        print(f'          详情: {detail}')


def login():
    """管理员登录获取token"""
    r = requests.post(f'{BASE_URL}/auth/login',
                      json={'username': 'admin', 'password': 'admin123'},
                      timeout=TIMEOUT)
    return r.json().get('access_token') if r.status_code == 200 else None


def measure_latency(url, headers=None, method='GET', json_body=None, n=30):
    """测量单个API的响应时间分布

    Args:
        n: 采样次数（先做 WARMUP_REQUESTS 次预热，再正式采样 n 次）
    Returns:
        dict: {avg, p50, p95, p99, min, max, success_rate}
    """
    # 预热
    for _ in range(WARMUP_REQUESTS):
        try:
            requests.request(method, url, headers=headers, json=json_body, timeout=TIMEOUT)
        except Exception:
            pass

    latencies = []
    errors = 0
    for _ in range(n):
        start = time.time()
        try:
            r = requests.request(method, url, headers=headers, json=json_body, timeout=TIMEOUT)
            elapsed = (time.time() - start) * 1000  # ms
            if r.status_code < 400:
                latencies.append(elapsed)
            else:
                errors += 1
        except Exception:
            errors += 1

    if not latencies:
        return {'avg_ms': 0, 'p50_ms': 0, 'p95_ms': 0, 'p99_ms': 0,
                'min_ms': 0, 'max_ms': 0, 'success_rate': 0, 'samples': 0}

    latencies.sort()
    n_ok = len(latencies)
    return {
        'avg_ms': round(statistics.mean(latencies), 2),
        'p50_ms': round(latencies[n_ok // 2], 2),
        'p95_ms': round(latencies[int(n_ok * 0.95)], 2),
        'p99_ms': round(latencies[int(n_ok * 0.99)], 2) if n_ok > 1 else round(latencies[-1], 2),
        'min_ms': round(latencies[0], 2),
        'max_ms': round(latencies[-1], 2),
        'success_rate': round((n_ok / n) * 100, 1),
        'samples': n_ok
    }


# ==================== 1. API响应时间测试 ====================
def test_api_latency(token):
    """测试核心API的响应时间分布"""
    category = 'API响应时间'
    print(f'\n{"="*60}\n{category}\n{"="*60}')
    headers = {'Authorization': f'Bearer {token}'}

    apis = [
        # 健康检查端点位于 /health（无 /api/v1 前缀），使用完整URL避免拼接
        ('GET', 'http://localhost:8000/health', None, None, '后端健康检查(无需认证)'),
        ('GET', f'{FRONTEND_URL}/', None, None, '前端首页'),
        ('GET', '/auth/me', headers, None, '获取用户信息'),
        ('GET', '/qa/quota', headers, None, 'QA额度查询'),
        ('GET', '/qa/suggestions', headers, None, 'QA推荐问题'),
        ('GET', '/qa/conversations', headers, None, 'QA对话列表'),
        ('GET', '/contract/history', headers, None, '合同历史'),
        ('GET', '/knowledge/documents', headers, None, '知识库文档'),
        ('GET', '/knowledge/stats', headers, None, '知识库统计'),
        ('GET', '/notifications/', headers, None, '通知列表'),
        ('GET', '/dashboard/overview', headers, None, '仪表盘概览'),
        ('GET', '/users', headers, None, '用户列表'),
    ]

    all_p95 = []
    for method, path, hdrs, body, name in apis:
        # 处理完整URL vs 相对路径
        if path.startswith('http'):
            url = path
        else:
            url = f'{BASE_URL}{path}'

        m = measure_latency(url, headers=hdrs, method=method, json_body=body, n=30)
        # 目标: P95 < 500ms
        passed = m['p95_ms'] < 500 and m['success_rate'] == 100
        all_p95.append(m['p95_ms'])
        log_test(category, name, passed, m,
                 f'目标P95<500ms, 实际P95={m["p95_ms"]}ms')

    # 汇总
    avg_p95 = round(statistics.mean(all_p95), 2) if all_p95 else 0
    print(f'\n  >> API平均P95响应时间: {avg_p95}ms')
    return avg_p95


# ==================== 2. 并发吞吐量测试 ====================
def test_concurrent_tps(token):
    """测试不同并发用户下的吞吐量(TPS)

    使用aiohttp异步客户端消除同步requests库的客户端瓶颈，
    真实反映服务端吞吐能力。
    """
    category = '并发吞吐量'
    print(f'\n{"="*60}\n{category}\n{"="*60}')
    headers = {'Authorization': f'Bearer {token}'}
    url = f'{BASE_URL}/auth/me'

    if not HAS_AIOHTTP:
        print('  [WARN] aiohttp未安装，跳过异步TPS测试')
        return {}

    async def _bench(concurrency, total):
        """异步并发压测"""
        connector = aiohttp.TCPConnector(limit=concurrency * 2, limit_per_host=concurrency * 2)
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 预热：确保所有worker的用户缓存已命中
            for _ in range(concurrency * 2):
                async with session.get(url, headers=headers) as r:
                    await r.read()

            success = [0]
            errors = [0]

            async def worker():
                try:
                    async with session.get(url, headers=headers) as r:
                        if r.status == 200:
                            success[0] += 1
                        else:
                            errors[0] += 1
                except Exception:
                    errors[0] += 1

            sem = asyncio.Semaphore(concurrency)

            async def limited_worker():
                async with sem:
                    await worker()

            start = time.time()
            await asyncio.gather(*[limited_worker() for _ in range(total)])
            duration = time.time() - start
            return success[0], errors[0], duration

    summary = {}
    for concurrency in CONCURRENT_USERS:
        total_requests = max(500, concurrency * 20)
        success_count, error_count, duration = asyncio.run(_bench(concurrency, total_requests))
        tps = round(success_count / duration, 1) if duration > 0 else 0
        success_rate = round(success_count / total_requests * 100, 1)

        # 目标: TPS > 1000（在50并发下）
        passed = success_rate >= 99 and (concurrency < 50 or tps > 1000)
        metrics = {
            'concurrency': concurrency,
            'total_requests': total_requests,
            'success': success_count,
            'errors': error_count,
            'duration_s': round(duration, 2),
            'tps': tps,
            'success_rate': success_rate
        }
        summary[concurrency] = metrics
        log_test(category, f'{concurrency}并发', passed, metrics,
                 f'TPS={tps}, 目标50并发TPS>1000')

    return summary


# ==================== 3. 并发登录承载测试 ====================
def test_concurrent_login():
    """测试并发登录承载能力"""
    category = '并发登录承载'
    print(f'\n{"="*60}\n{category}\n{"="*60}')

    concurrency = 10
    rounds = 5
    total = concurrency * rounds
    success_count = [0]
    latencies = []
    lock = threading.Lock()

    def login_worker(_):
        start = time.time()
        try:
            r = requests.post(f'{BASE_URL}/auth/login',
                              json={'username': 'admin', 'password': 'admin123'},
                              timeout=TIMEOUT)
            elapsed = (time.time() - start) * 1000
            if r.status_code == 200 and 'access_token' in r.json():
                with lock:
                    success_count[0] += 1
                    latencies.append(elapsed)
        except Exception:
            pass

    start = time.time()
    for _ in range(rounds):
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            list(executor.map(login_worker, range(concurrency)))
    duration = time.time() - start

    latencies.sort()
    n_ok = len(latencies)
    metrics = {
        'concurrency': concurrency,
        'rounds': rounds,
        'total': total,
        'success': success_count[0],
        'success_rate': round(success_count[0] / total * 100, 1),
        'avg_ms': round(statistics.mean(latencies), 2) if latencies else 0,
        'p50_ms': round(latencies[n_ok // 2], 2) if latencies else 0,
        'p95_ms': round(latencies[int(n_ok * 0.95)], 2) if n_ok > 1 else 0,
        'duration_s': round(duration, 2)
    }
    passed = metrics['success_rate'] == 100
    log_test(category, f'{concurrency}并发×{rounds}轮', passed, metrics,
             '目标100%成功率')
    return metrics


# ==================== 4. AI推理耗时测试 ====================
def test_ai_inference(token):
    """测试AI问答与合同审查的端到端耗时"""
    category = 'AI推理耗时'
    print(f'\n{"="*60}\n{category}\n{"="*60}')
    headers = {'Authorization': f'Bearer {token}'}

    # AI问答（3次采样，使用中位数避免冷启动异常值）
    qa_latencies = []
    questions = [
        '什么是劳动合同？',
        '经济补偿金如何计算？',
        '格式条款无效的情形有哪些？',
    ]
    # 预热：发送一个简单问题让Ollama模型加载到内存（不计入统计）
    try:
        requests.post(f'{BASE_URL}/qa/ask', headers=headers,
                      json={'question': '你好'}, timeout=60)
    except Exception:
        pass

    for q in questions:
        start = time.time()
        try:
            r = requests.post(f'{BASE_URL}/qa/ask', headers=headers,
                              json={'question': q}, timeout=120)
            elapsed = (time.time() - start) * 1000
            if r.status_code == 200:
                qa_latencies.append(elapsed)
        except Exception:
            pass

    if qa_latencies:
        # 使用中位数（避免冷启动异常值影响）
        median_qa = round(statistics.median(qa_latencies), 0)
        avg_qa = round(statistics.mean(qa_latencies), 0)
        metrics = {
            'samples': len(qa_latencies),
            'median_ms': median_qa,
            'median_s': round(median_qa / 1000, 1),
            'avg_ms': avg_qa,
            'min_ms': round(min(qa_latencies), 0),
            'max_ms': round(max(qa_latencies), 0),
        }
        # 本地qwen2.5:1.5b推理，含RAG检索，中位数<30s为可接受
        passed = median_qa < 30000
        log_test(category, 'AI法律问答', passed, metrics,
                 '本地qwen2.5:1.5b推理(预热后)，目标中位数<30s')

    # AI合同审查（1次，避免耗时过长）
    test_content = """房屋租赁合同
甲方：出租方
乙方：承租方
第一条 租赁期限：2024年1月1日至2025年1月1日
第二条 租金：每月5000元，押一付三
第三条 甲方有权随时收回房屋，乙方不得拒绝
第四条 乙方违约时，押金不予退还
第五条 甲方不承担房屋维修责任
"""
    files = {'file': ('perf_contract.txt', test_content.encode('utf-8'), 'text/plain')}
    start = time.time()
    try:
        r = requests.post(f'{BASE_URL}/contract/upload', headers=headers,
                          files=files, timeout=TIMEOUT)
        if r.status_code == 200:
            contract_id = r.json().get('id')
            if contract_id:
                start = time.time()
                r = requests.post(f'{BASE_URL}/contract/review', headers=headers,
                                  json={'contract_id': contract_id}, timeout=180)
                elapsed = (time.time() - start) * 1000
                if r.status_code == 200:
                    metrics = {
                        'duration_ms': round(elapsed, 0),
                        'duration_s': round(elapsed / 1000, 1)
                    }
                    # V4.0多Agent对抗式审查含12节点，<180s为可接受
                    passed = elapsed < 180000
                    log_test(category, 'AI合同审查(V4.0多Agent)', passed, metrics,
                             '含12节点LangGraph工作流，目标<180s')
                # 清理
                requests.delete(f'{BASE_URL}/contract/{contract_id}', headers=headers, timeout=TIMEOUT)
    except Exception as e:
        log_test(category, 'AI合同审查(V4.0多Agent)', False, {}, f'异常: {e}')


# ==================== 5. 前端首屏加载性能 ====================
def test_frontend_performance():
    """测试前端首屏加载性能"""
    category = '前端首屏加载'
    print(f'\n{"="*60}\n{category}\n{"="*60}')

    # 首页HTML加载
    m = measure_latency(f'{FRONTEND_URL}/', n=30)
    metrics = {
        'avg_ms': m['avg_ms'],
        'p50_ms': m['p50_ms'],
        'p95_ms': m['p95_ms'],
        'success_rate': m['success_rate']
    }
    passed = m['p95_ms'] < 100  # 首页应<100ms
    log_test(category, '首页HTML加载', passed, metrics, '目标P95<100ms')

    # 主JS Bundle大小与加载时间
    import re
    html = requests.get(f'{FRONTEND_URL}/', timeout=10).text
    js_match = re.search(r'src="(/assets/[^"]+\.js)"', html)
    if js_match:
        js_url = f'{FRONTEND_URL}{js_match.group(1)}'
        # 测量JS加载时间
        m_js = measure_latency(js_url, n=20)
        # 获取JS大小
        r = requests.get(js_url, timeout=10)
        js_size_kb = round(len(r.content) / 1024, 2)
        metrics_js = {
            'size_kb': js_size_kb,
            'p50_ms': m_js['p50_ms'],
            'p95_ms': m_js['p95_ms']
        }
        passed = m_js['p95_ms'] < 500
        log_test(category, '主JS Bundle加载', passed, metrics_js,
                 f'大小{js_size_kb}KB, 目标P95<500ms')

    # API代理延迟（通过nginx代理到后端）
    m_proxy = measure_latency(f'{FRONTEND_URL}/api/v1/health', n=20)
    metrics_proxy = {
        'p50_ms': m_proxy['p50_ms'],
        'p95_ms': m_proxy['p95_ms']
    }
    passed = m_proxy['p95_ms'] < 100
    log_test(category, 'Nginx反向代理延迟', passed, metrics_proxy, '目标P95<100ms')


# ==================== 6. 容器资源占用测试 ====================
def test_container_resources():
    """测试容器CPU/内存占用"""
    category = '容器资源占用'
    print(f'\n{"="*60}\n{category}\n{"="*60}')

    try:
        # 使用 docker stats --no-stream 获取一次性快照
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format',
             '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}'],
            capture_output=True, text=True, timeout=30
        )
        lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]

        total_cpu = 0
        total_mem_pct = 0
        container_metrics = []
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 4:
                name = parts[0]
                cpu_str = parts[1].replace('%', '').strip()
                mem_usage = parts[2]
                mem_pct_str = parts[3].replace('%', '').strip()
                try:
                    cpu = float(cpu_str)
                    mem_pct = float(mem_pct_str)
                    total_cpu += cpu
                    total_mem_pct = max(total_mem_pct, mem_pct)
                    container_metrics.append({
                        'container': name,
                        'cpu_pct': cpu,
                        'mem_usage': mem_usage,
                        'mem_pct': mem_pct
                    })
                except ValueError:
                    pass

        for cm in container_metrics:
            # 单容器目标: CPU<70%, 内存<80%
            passed = cm['cpu_pct'] < 70 and cm['mem_pct'] < 80
            log_test(category, cm['container'], passed, cm,
                     '目标单容器CPU<70%, 内存<80%')

        # 系统总占用
        metrics_total = {
            'total_cpu_pct': round(total_cpu, 2),
            'max_mem_pct': round(total_mem_pct, 2),
            'container_count': len(container_metrics)
        }
        passed = total_cpu < 200 and total_mem_pct < 80  # 4容器总CPU<200%
        log_test(category, '系统总体', passed, metrics_total,
                 '4容器总CPU<200%, 单容器内存<80%')

        return container_metrics
    except Exception as e:
        log_test(category, '容器资源采集', False, {}, f'异常: {e}')
        return []


# ==================== 主函数 ====================
def main():
    print('=' * 60)
    print('智法通 V5.0 性能测试套件')
    print(f'测试时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'后端地址: {BASE_URL}')
    print(f'前端地址: {FRONTEND_URL}')
    print('=' * 60)

    # 登录
    token = login()
    if not token:
        print('[FATAL] 管理员登录失败，无法继续性能测试')
        return

    # 执行所有性能测试
    avg_p95 = test_api_latency(token)
    tps_summary = test_concurrent_tps(token)
    login_metrics = test_concurrent_login()
    test_ai_inference(token)
    test_frontend_performance()
    test_container_resources()

    # 汇总
    total_dur = time.time() - total_start
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    total = len(results)

    print('\n' + '=' * 60)
    print('性能测试汇总')
    print('=' * 60)
    print(f'测试项总数: {total}')
    print(f'通过: {passed}')
    print(f'失败: {failed}')
    print(f'通过率: {passed / total * 100:.1f}%')
    print(f'总耗时: {total_dur:.1f}s')

    # 保存报告
    report = {
        'version': 'V5.0',
        'timestamp': datetime.now().isoformat(),
        'total': total,
        'passed': passed,
        'failed': failed,
        'pass_rate': round(passed / total * 100, 1),
        'duration_s': round(total_dur, 1),
        'summary': {
            'api_avg_p95_ms': avg_p95,
            'tps_summary': tps_summary,
            'login_metrics': login_metrics
        },
        'details': results
    }
    report_path = os.path.join(os.path.dirname(__file__), 'test_performance_v5.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n详细结果已保存: {report_path}')


if __name__ == '__main__':
    main()
