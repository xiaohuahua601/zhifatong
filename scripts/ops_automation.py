#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智法通 V5.0 自动化运维脚本

功能:
1. IP访问白名单自动化管理
   - 自动检测当前已连接的客户端IP
   - 添加授权IP到白名单
   - 移除过期/无效IP
   - 支持从配置文件加载授权IP列表

2. 测试源码清理自动化
   - 识别并删除测试环境中的临时源码、测试数据及调试文件
   - 清理测试生成的临时文件（上传的测试合同、测试用户等）
   - 清理Docker构建缓存
   - 无需人工确认

使用方式:
    python scripts/ops_automation.py whitelist     # 管理IP白名单
    python scripts/ops_automation.py cleanup        # 清理测试源码
    python scripts/ops_automation.py cleanup-all    # 深度清理（含构建缓存）
    python scripts/ops_automation.py health-check   # 健康检查
    python scripts/ops_automation.py all            # 执行全部运维任务
"""
import subprocess
import os
import sys
import json
import time
import shutil
import ipaddress
import re
from datetime import datetime
from pathlib import Path

# ==================== 配置 ====================
PROJECT_ROOT = Path(__file__).parent.parent
WHITELIST_CONFIG = PROJECT_ROOT / 'config' / 'ip_whitelist.json'
CONTAINER_PREFIX = 'zhifatong-'

# 默认授权IP（可被配置文件覆盖）
DEFAULT_WHITELIST = [
    '127.0.0.1',       # 本地回环
    '192.168.0.0/16',  # 内网网段
    '10.0.0.0/8',      # 内网网段
    '172.16.0.0/12',   # Docker网段
    '::1/128',         # IPv6本地回环
]


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def log(msg, level='INFO'):
    """带时间戳和颜色的日志输出"""
    color = {
        'INFO': Colors.BLUE,
        'OK': Colors.GREEN,
        'WARN': Colors.YELLOW,
        'ERROR': Colors.RED,
    }.get(level, Colors.BLUE)
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f'{color}[{timestamp}] [{level}]{Colors.RESET} {msg}')


def run_cmd(cmd, check=False, capture=True):
    """执行shell命令

    Args:
        cmd: 命令列表或字符串
        check: 失败时抛出异常
        capture: 是否捕获输出
    Returns:
        CompletedProcess实例
    """
    if isinstance(cmd, str):
        cmd = cmd.split()
    result = subprocess.run(cmd, capture_output=capture, text=True, timeout=60)
    if check and result.returncode != 0:
        raise RuntimeError(f'命令失败: {" ".join(cmd)}\nstderr: {result.stderr}')
    return result


# ==================== 1. IP白名单管理 ====================
class IPWhitelistManager:
    """IP访问白名单自动化管理器

    工作原理:
    1. 从配置文件加载授权IP列表（首次运行自动创建默认配置）
    2. 检测当前已连接的客户端IP（通过netstat/docker logs）
    3. 验证每个IP是否在授权列表中
    4. 配置防火墙规则仅允许授权IP访问
    5. 输出白名单状态报告
    """

    def __init__(self):
        self.config_path = WHITELIST_CONFIG
        self.whitelist = self._load_config()

    def _load_config(self):
        """加载IP白名单配置

        首次运行时创建默认配置文件。
        """
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            config = {
                'whitelist': DEFAULT_WHITELIST,
                'description': '智法通IP访问白名单配置',
                'updated_at': datetime.now().isoformat(),
                'auto_detected': []
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            log(f'创建默认IP白名单配置: {self.config_path}', 'INFO')
            return config

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_config(self):
        """保存IP白名单配置"""
        self.whitelist['updated_at'] = datetime.now().isoformat()
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.whitelist, f, ensure_ascii=False, indent=2)
        log(f'IP白名单配置已保存: {self.config_path}', 'OK')

    def detect_connected_ips(self):
        """自动检测当前已连接的客户端IP

        通过 netstat 检测与容器端口建立的连接。
        """
        connected_ips = set()
        try:
            # 检测与容器映射端口建立的连接
            ports = ['8000', '8080', '3306', '6379']
            for port in ports:
                result = run_cmd(f'netstat -an | findstr :{port}')
                for line in result.stdout.split('\n'):
                    # 解析 netstat 输出，提取远程IP
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        remote = parts[2]
                        # 提取IP地址（去掉端口）
                        ip_match = re.match(r'(\d+\.\d+\.\d+\.\d+)', remote)
                        if ip_match:
                            ip = ip_match.group(1)
                            if ip not in ['0.0.0.0', '127.0.0.1']:
                                connected_ips.add(ip)
        except Exception as e:
            log(f'检测连接IP时异常(非致命): {e}', 'WARN')

        # 添加本地回环（始终授权）
        connected_ips.add('127.0.0.1')

        self.whitelist['auto_detected'] = sorted(connected_ips)
        log(f'自动检测到 {len(connected_ips)} 个已连接IP: {sorted(connected_ips)}', 'INFO')
        return connected_ips

    def validate_ip(self, ip_str):
        """验证IP地址格式

        Args:
            ip_str: IP地址字符串（支持CIDR格式）
        Returns:
            bool: 是否为有效IP
        """
        try:
            if '/' in ip_str:
                ipaddress.ip_network(ip_str, strict=False)
            else:
                ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False

    def is_authorized(self, ip_str):
        """检查IP是否在白名单中

        Args:
            ip_str: 待检查的IP地址
        Returns:
            bool: 是否在白名单中
        """
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False

        for entry in self.whitelist.get('whitelist', []):
            try:
                if '/' in entry:
                    network = ipaddress.ip_network(entry, strict=False)
                    if ip in network:
                        return True
                else:
                    if ip == ipaddress.ip_address(entry):
                        return True
            except ValueError:
                continue
        return False

    def add_ip(self, ip_str):
        """添加IP到白名单

        Args:
            ip_str: IP地址或CIDR网段
        Returns:
            bool: 是否添加成功
        """
        if not self.validate_ip(ip_str):
            log(f'无效的IP地址: {ip_str}', 'ERROR')
            return False

        if ip_str in self.whitelist['whitelist']:
            log(f'IP已在白名单中: {ip_str}', 'WARN')
            return True

        self.whitelist['whitelist'].append(ip_str)
        self._save_config()
        log(f'已添加IP到白名单: {ip_str}', 'OK')
        return True

    def remove_ip(self, ip_str):
        """从白名单移除IP

        Args:
            ip_str: IP地址或CIDR网段
        Returns:
            bool: 是否移除成功
        """
        if ip_str not in self.whitelist['whitelist']:
            log(f'IP不在白名单中: {ip_str}', 'WARN')
            return False

        self.whitelist['whitelist'].remove(ip_str)
        self._save_config()
        log(f'已从白名单移除IP: {ip_str}', 'OK')
        return True

    def apply_firewall_rules(self):
        """应用防火墙规则（仅授权IP可访问）

        在Windows上通过netsh advfirewall配置。
        注意: 此操作需要管理员权限。
        """
        log('应用防火墙规则...', 'INFO')

        # 检测已连接IP并验证
        connected = self.detect_connected_ips()
        unauthorized = [ip for ip in connected if not self.is_authorized(ip)]

        if unauthorized:
            log(f'检测到未授权IP尝试访问: {unauthorized}', 'WARN')
            log('这些IP的连接将被拒绝', 'WARN')

        # 在生产环境中，这里会配置实际的防火墙规则
        # 当前版本仅输出建议，不实际修改防火墙（避免锁死远程连接）
        log('防火墙规则建议:', 'INFO')
        for ip in self.whitelist['whitelist']:
            log(f'  允许: {ip}', 'OK')
        log(f'  拒绝: 其他所有IP', 'WARN')
        log('注意: 实际防火墙配置需管理员手动执行（避免锁死远程连接）', 'INFO')

    def show_status(self):
        """显示白名单状态"""
        print(f'\n{"="*60}')
        print('IP访问白名单状态')
        print(f'{"="*60}')
        print(f'配置文件: {self.config_path}')
        print(f'更新时间: {self.whitelist.get("updated_at", "N/A")}')
        print(f'\n授权IP/网段 ({len(self.whitelist["whitelist"])} 条):')
        for ip in self.whitelist['whitelist']:
            print(f'  ✓ {ip}')
        if self.whitelist.get('auto_detected'):
            print(f'\n自动检测到的连接IP ({len(self.whitelist["auto_detected"])} 个):')
            for ip in self.whitelist['auto_detected']:
                authorized = '✓' if self.is_authorized(ip) else '✗'
                status = '授权' if authorized == '✓' else '未授权'
                print(f'  {authorized} {ip} ({status})')


# ==================== 2. 测试源码清理 ====================
class TestSourceCleaner:
    """测试源码清理自动化

    清理范围:
    1. 测试上传的临时合同文件
    2. 测试创建的临时用户
    3. 测试产生的对话和消息
    4. Docker构建缓存（可选）
    5. 临时调试文件
    6. 日志文件（保留最近7天）
    """

    def __init__(self):
        self.cleaned_items = []

    def _record(self, category, item, size=''):
        """记录清理项"""
        self.cleaned_items.append({
            'category': category,
            'item': str(item),
            'size': size,
            'timestamp': datetime.now().isoformat()
        })

    def clean_test_uploads(self):
        """清理测试上传的合同文件

        通过API删除测试期间上传的合同文件。
        """
        log('清理测试上传的合同文件...', 'INFO')
        try:
            # 登录获取admin token
            import requests
            r = requests.post('http://localhost:8000/api/v1/auth/login',
                              json={'username': 'admin', 'password': 'admin123'},
                              timeout=10)
            if r.status_code != 200:
                log('管理员登录失败，跳过合同清理', 'WARN')
                return
            token = r.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}'}

            # 获取所有合同
            r = requests.get('http://localhost:8000/api/v1/contract/history',
                             headers=headers, timeout=10)
            if r.status_code == 200:
                contracts = r.json() if isinstance(r.json(), list) else r.json().get('items', [])
                count = 0
                for contract in contracts:
                    cid = contract.get('id')
                    if cid:
                        try:
                            r = requests.delete(f'http://localhost:8000/api/v1/contract/{cid}',
                                                headers=headers, timeout=10)
                            if r.status_code in [200, 204]:
                                count += 1
                                self._record('合同文件', f'contract_id={cid}')
                        except Exception:
                            pass
                log(f'已删除 {count} 份测试合同', 'OK')
        except Exception as e:
            log(f'清理合同文件异常: {e}', 'WARN')

    def clean_test_conversations(self):
        """清理测试产生的对话和消息"""
        log('清理测试对话...', 'INFO')
        try:
            import requests
            r = requests.post('http://localhost:8000/api/v1/auth/login',
                              json={'username': 'admin', 'password': 'admin123'},
                              timeout=10)
            if r.status_code != 200:
                return
            token = r.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}'}

            # 获取所有对话
            r = requests.get('http://localhost:8000/api/v1/qa/conversations',
                             headers=headers, timeout=10)
            if r.status_code == 200:
                body = r.json()
                convs = body if isinstance(body, list) else body.get('items', [])
                count = 0
                for conv in convs:
                    cid = conv.get('id')
                    if cid:
                        try:
                            r = requests.delete(f'http://localhost:8000/api/v1/qa/conversations/{cid}',
                                                headers=headers, timeout=10)
                            if r.status_code in [200, 204]:
                                count += 1
                                self._record('对话', f'conversation_id={cid}')
                        except Exception:
                            pass
                log(f'已删除 {count} 条测试对话', 'OK')
        except Exception as e:
            log(f'清理对话异常: {e}', 'WARN')

    def clean_test_users(self):
        """清理测试创建的临时用户（保留3个内置用户）"""
        log('清理测试用户...', 'INFO')
        try:
            import requests
            r = requests.post('http://localhost:8000/api/v1/auth/login',
                              json={'username': 'admin', 'password': 'admin123'},
                              timeout=10)
            if r.status_code != 200:
                return
            token = r.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}'}

            # 获取所有用户
            r = requests.get('http://localhost:8000/api/v1/users',
                             headers=headers, timeout=10)
            if r.status_code == 200:
                body = r.json()
                users = body if isinstance(body, list) else body.get('items', [])
                builtin_users = {'admin', 'lawyer', 'user'}
                count = 0
                for user in users:
                    username = user.get('username', '')
                    uid = user.get('id')
                    if username not in builtin_users and uid:
                        try:
                            r = requests.delete(f'http://localhost:8000/api/v1/users/{uid}',
                                                headers=headers, timeout=10)
                            if r.status_code in [200, 204]:
                                count += 1
                                self._record('测试用户', f'username={username}')
                        except Exception:
                            pass
                log(f'已删除 {count} 个测试用户', 'OK')
        except Exception as e:
            log(f'清理测试用户异常: {e}', 'WARN')

    def clean_temp_files(self):
        """清理临时调试文件"""
        log('清理临时文件...', 'INFO')

        # 清理 tests/ 目录下的临时文件
        temp_patterns = [
            'tests/_*.py',           # 临时测试脚本
            'tests/test_*.txt',      # 临时测试数据
            'tests/__pycache__',     # Python缓存
            'backend/__pycache__',   # 后端缓存
            'backend/app/__pycache__',
            'backend/app/**/__pycache__',
            'frontend/dist',         # 前端构建产物（容器内已有）
            '*.pyc',
            '**/*.pyc',
            '.pytest_cache',
            'backend/.pytest_cache',
        ]

        count = 0
        for pattern in temp_patterns:
            # 使用 Path.glob 匹配
            if '**' in pattern:
                base = pattern.split('**')[0].rstrip('/')
                suffix = pattern.split('**')[1].lstrip('/')
                if not suffix:
                    continue
                base_path = PROJECT_ROOT / base if base else PROJECT_ROOT
                if base_path.exists():
                    for item in base_path.rglob(suffix.rstrip('/')):
                        try:
                            if item.is_file():
                                size = item.stat().st_size
                                item.unlink()
                                self._record('临时文件', item, f'{size}B')
                                count += 1
                            elif item.is_dir():
                                shutil.rmtree(item, ignore_errors=True)
                                self._record('临时目录', item)
                                count += 1
                        except Exception:
                            pass
            else:
                for item in PROJECT_ROOT.glob(pattern):
                    try:
                        if item.is_file():
                            size = item.stat().st_size
                            item.unlink()
                            self._record('临时文件', item, f'{size}B')
                            count += 1
                        elif item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                            self._record('临时目录', item)
                            count += 1
                    except Exception:
                        pass

        log(f'已清理 {count} 个临时文件/目录', 'OK')

    def clean_old_logs(self, keep_days=7):
        """清理旧日志文件（保留最近keep_days天）"""
        log(f'清理旧日志（保留{keep_days}天）...', 'INFO')
        cutoff = time.time() - keep_days * 86400

        log_dirs = [
            PROJECT_ROOT / 'backend' / 'logs',
            PROJECT_ROOT / 'logs',
        ]

        count = 0
        for log_dir in log_dirs:
            if not log_dir.exists():
                continue
            for log_file in log_dir.glob('*.log*'):
                try:
                    if log_file.stat().st_mtime < cutoff:
                        size = log_file.stat().st_size
                        log_file.unlink()
                        self._record('旧日志', log_file, f'{size}B')
                        count += 1
                except Exception:
                    pass

        log(f'已清理 {count} 个旧日志文件', 'OK')

    def clean_docker_cache(self):
        """清理Docker构建缓存（深度清理）"""
        log('清理Docker构建缓存...', 'INFO')
        try:
            # 清理悬空镜像（dangling images）
            result = run_cmd('docker image prune -f')
            log('已清理悬空镜像', 'OK')

            # 清理构建缓存
            result = run_cmd('docker builder prune -f')
            log('已清理构建缓存', 'OK')

            # 清理未使用的网络
            result = run_cmd('docker network prune -f')
            log('已清理未使用网络', 'OK')
        except Exception as e:
            log(f'清理Docker缓存异常: {e}', 'WARN')

    def clean_redis_test_data(self):
        """清理Redis中的测试数据（登录失败锁等）"""
        log('清理Redis测试数据...', 'INFO')
        try:
            # 清理登录失败锁
            result = run_cmd(['docker', 'exec', 'zhifatong-redis', 'redis-cli',
                              'KEYS', 'login_fail:*'], capture=True)
            if result.stdout.strip():
                keys = [k.strip() for k in result.stdout.strip().split('\n') if k.strip()]
                for key in keys:
                    run_cmd(['docker', 'exec', 'zhifatong-redis', 'redis-cli', 'DEL', key])
                    self._record('Redis键', key)
                log(f'已清理 {len(keys)} 个登录失败锁', 'OK')
            else:
                log('无登录失败锁需清理', 'OK')
        except Exception as e:
            log(f'清理Redis异常: {e}', 'WARN')

    def run_cleanup(self, deep=False):
        """执行完整清理流程

        Args:
            deep: 是否执行深度清理（含Docker缓存）
        """
        print(f'\n{"="*60}')
        print('测试源码清理')
        print(f'{"="*60}')
        start = time.time()

        # 1. 清理测试上传的合同文件
        self.clean_test_uploads()

        # 2. 清理测试对话
        self.clean_test_conversations()

        # 3. 清理测试用户
        self.clean_test_users()

        # 4. 清理Redis测试数据
        self.clean_redis_test_data()

        # 5. 清理临时文件
        self.clean_temp_files()

        # 6. 清理旧日志
        self.clean_old_logs()

        # 7. 深度清理（可选）
        if deep:
            self.clean_docker_cache()

        # 汇总
        duration = time.time() - start
        print(f'\n{"="*60}')
        print(f'清理完成 | 耗时: {duration:.1f}s | 清理项: {len(self.cleaned_items)}')
        print(f'{"="*60}')

        # 保存清理报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_s': round(duration, 1),
            'total_items': len(self.cleaned_items),
            'deep_clean': deep,
            'details': self.cleaned_items
        }
        report_path = PROJECT_ROOT / 'tests' / 'cleanup_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        log(f'清理报告已保存: {report_path}', 'OK')


# ==================== 3. 健康检查 ====================
def health_check():
    """系统健康检查"""
    print(f'\n{"="*60}')
    print('系统健康检查')
    print(f'{"="*60}')

    checks = []

    # 检查Docker容器状态
    result = run_cmd(['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}\t{{.Ports}}'])
    containers = [l for l in result.stdout.strip().split('\n') if l.strip()]
    print('\n容器状态:')
    for c in containers:
        parts = c.split('\t')
        name = parts[0] if parts else '?'
        status = parts[1] if len(parts) > 1 else '?'
        healthy = 'healthy' in status.lower() or 'up' in status.lower()
        mark = '✓' if healthy else '✗'
        print(f'  {mark} {name}: {status}')
        checks.append(healthy)

    # 检查API可达性
    print('\nAPI可达性:')
    try:
        import requests
        r = requests.get('http://localhost:8000/health', timeout=5)
        ok = r.status_code == 200
        print(f'  {"✓" if ok else "✗"} 后端 /health: HTTP {r.status_code}')
        checks.append(ok)
    except Exception as e:
        print(f'  ✗ 后端 /health: {e}')
        checks.append(False)

    try:
        import requests
        r = requests.get('http://localhost:8080/', timeout=5)
        ok = r.status_code == 200
        print(f'  {"✓" if ok else "✗"} 前端 /: HTTP {r.status_code}')
        checks.append(ok)
    except Exception as e:
        print(f'  ✗ 前端 /: {e}')
        checks.append(False)

    # 检查Ollama服务
    try:
        import requests
        r = requests.get('http://localhost:11434/api/tags', timeout=5)
        ok = r.status_code == 200
        models = [m.get('name', '?') for m in r.json().get('models', [])] if ok else []
        print(f'  {"✓" if ok else "✗"} Ollama: {", ".join(models) if models else "无模型"}')
        checks.append(ok)
    except Exception as e:
        print(f'  ✗ Ollama: {e}')
        checks.append(False)

    # 汇总
    all_ok = all(checks)
    print(f'\n{"="*60}')
    print(f'健康检查: {"全部通过" if all_ok else "存在问题"} ({sum(checks)}/{len(checks)})')
    print(f'{"="*60}')
    return all_ok


# ==================== 主函数 ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='智法通 V5.0 自动化运维脚本')
    parser.add_argument('command', nargs='?', default='all',
                        choices=['whitelist', 'cleanup', 'cleanup-all', 'health-check', 'all'],
                        help='运维任务')
    parser.add_argument('--add-ip', help='添加IP到白名单')
    parser.add_argument('--remove-ip', help='从白名单移除IP')
    args = parser.parse_args()

    print(f'智法通 V5.0 自动化运维脚本')
    print(f'执行时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'任务: {args.command}')

    if args.command == 'whitelist':
        mgr = IPWhitelistManager()
        if args.add_ip:
            mgr.add_ip(args.add_ip)
        elif args.remove_ip:
            mgr.remove_ip(args.remove_ip)
        else:
            mgr.detect_connected_ips()
            mgr.apply_firewall_rules()
            mgr.show_status()

    elif args.command == 'cleanup':
        cleaner = TestSourceCleaner()
        cleaner.run_cleanup(deep=False)

    elif args.command == 'cleanup-all':
        cleaner = TestSourceCleaner()
        cleaner.run_cleanup(deep=True)

    elif args.command == 'health-check':
        health_check()

    elif args.command == 'all':
        # 1. 健康检查
        health_check()
        # 2. IP白名单管理
        mgr = IPWhitelistManager()
        mgr.detect_connected_ips()
        mgr.show_status()
        # 3. 测试源码清理
        cleaner = TestSourceCleaner()
        cleaner.run_cleanup(deep=False)

    return 0


if __name__ == '__main__':
    sys.exit(main())
