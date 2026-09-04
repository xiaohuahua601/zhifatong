#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智法通 V4.0.5 回归测试脚本
验证 4 项修复未影响系统核心功能
"""
import requests
import sys

BASE = 'http://localhost:8000/api/v1'
results = []


def test(name, condition, detail):
    status = 'PASS' if condition else 'FAIL'
    results.append((name, status, detail))


# 1. 管理员登录
r = requests.post(f'{BASE}/auth/login', json={'username': 'admin', 'password': 'admin123'}, timeout=10)
admin_token = r.json().get('access_token') if r.status_code == 200 else None
test('管理员登录', r.status_code == 200 and admin_token, f'HTTP {r.status_code}')
H = {'Authorization': f'Bearer {admin_token}'}

# 2. 法务登录
r = requests.post(f'{BASE}/auth/login', json={'username': 'lawyer', 'password': 'lawyer123'}, timeout=10)
test('法务登录', r.status_code == 200, f'HTTP {r.status_code}')

# 3. 普通用户登录
r = requests.post(f'{BASE}/auth/login', json={'username': 'user', 'password': 'user123456'}, timeout=10)
test('普通用户登录', r.status_code == 200, f'HTTP {r.status_code}')

# 4. 健康检查
r = requests.get('http://localhost:8000/health', timeout=10)
test('健康检查', r.status_code == 200, f'HTTP {r.status_code}')

# 5. 获取个人信息（正确端点：/auth/me）
r = requests.get(f'{BASE}/auth/me', headers=H, timeout=10)
test('获取个人信息', r.status_code == 200, f'HTTP {r.status_code}')

# 6. 用户列表
r = requests.get(f'{BASE}/users', headers=H, timeout=10)
user_count = len(r.json()) if r.status_code == 200 else 0
test('用户列表', r.status_code == 200 and user_count >= 3, f'count={user_count}')

# 7. 热点分析
r = requests.get(f'{BASE}/analysis/hot-topics?days=30', headers=H, timeout=10)
d = r.json()
topics_count = len(d.get('topics', []))
test('热点分析', topics_count > 0, f'{topics_count} categories')

# 8. 法条排行
r = requests.get(f'{BASE}/analysis/citations?days=30', headers=H, timeout=10)
d = r.json()
cit_count = len(d.get('citations', []))
test('法条排行', cit_count > 0, f'{cit_count} docs')

# 9. 趋势分析
r = requests.get(f'{BASE}/analysis/trends?granularity=day', headers=H, timeout=10)
d = r.json()
trend_count = len(d.get('trends', []))
test('趋势分析', trend_count > 0, f'{trend_count} days')

# 10. 用户聚类
r = requests.get(f'{BASE}/analysis/user-clusters?days=30', headers=H, timeout=10)
d = r.json()
cluster_count = len(d.get('clusters', []))
test('用户聚类', cluster_count > 0, f'{cluster_count} clusters')

# 11. 知识库搜索（POST 方法）
r = requests.post(f'{BASE}/knowledge/search', json={'query': '劳动', 'limit': 3}, headers=H, timeout=10)
test('知识库搜索', r.status_code == 200, f'HTTP {r.status_code}')

# 12. 通知列表
r = requests.get(f'{BASE}/notifications', headers=H, timeout=10)
test('通知列表', r.status_code == 200, f'HTTP {r.status_code}')

# 输出结果
print('=' * 60)
print('智法通 V4.0.5 回归测试报告')
print('=' * 60)
passed = sum(1 for _, s, _ in results if s == 'PASS')
for name, status, detail in results:
    mark = '✓' if status == 'PASS' else '✗'
    print(f'{mark} [{status}] {name}: {detail}')
print('=' * 60)
print(f'总计: {passed}/{len(results)} 通过')
sys.exit(0 if passed == len(results) else 1)
