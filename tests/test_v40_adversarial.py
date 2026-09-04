"""V4.0 多Agent对抗式审查端到端API测试

验证流程：
1. 用户登录获取token
2. 上传合同文件
3. 启动合同审查（触发V4.0对抗式审查工作流）
4. 获取审查报告，验证V4.0字段全部填充
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"
API = "/api/v1"
CONTRACT_FILE = r"e:\临时项目\3_大模型项目_实施\项目1_智法通_企业级智能法律顾问平台\tests\test_contract.txt"


def main():
    print("=" * 70)
    print("智法通 V4.0 多Agent对抗式审查 端到端API测试")
    print("=" * 70)

    # ==================== 1. 登录 ====================
    print("\n[1/4] 用户登录...")
    login_resp = requests.post(
        f"{BASE_URL}{API}/auth/login",
        json={"username": "user", "password": "user123456"},
        timeout=10,
    )
    assert login_resp.status_code == 200, f"登录失败: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  ✓ 登录成功, token长度={len(token)}")

    # ==================== 2. 上传合同 ====================
    print("\n[2/4] 上传合同文件...")
    with open(CONTRACT_FILE, "rb") as f:
        upload_resp = requests.post(
            f"{BASE_URL}{API}/contract/upload",
            headers=headers,
            files={"file": ("test_contract.txt", f, "text/plain")},
            timeout=30,
        )
    assert upload_resp.status_code == 200, f"上传失败: {upload_resp.text}"
    contract_id = upload_resp.json()["id"]
    print(f"  ✓ 上传成功, contract_id={contract_id}, status={upload_resp.json()['status']}")

    # ==================== 3. 启动审查（V4.0对抗式审查工作流）====================
    print("\n[3/4] 启动合同审查（V4.0多Agent对抗式审查，含主审/复核/反方/辩论节点）...")
    print("  等待中...（本地qwen2.5:1.5b推理，约30-90秒）")
    start_time = time.time()
    review_resp = requests.post(
        f"{BASE_URL}{API}/contract/review",
        headers=headers,
        json={"contract_id": contract_id, "contract_type": "租赁合同"},
        timeout=300,  # 5分钟超时
    )
    duration = time.time() - start_time
    assert review_resp.status_code == 200, f"审查失败: {review_resp.text}"
    review_data = review_resp.json()
    print(f"  ✓ 审查完成, 耗时={duration:.1f}s, report_id={review_data.get('report_id')}")
    print(f"    overall_score={review_data.get('overall_score')}, risk_level={review_data.get('risk_level')}")

    # ==================== 4. 获取完整报告，验证V4.0字段 ====================
    print("\n[4/4] 获取审查报告，验证V4.0对抗式审查字段...")
    report_resp = requests.get(
        f"{BASE_URL}{API}/contract/report/{contract_id}",
        headers=headers,
        timeout=10,
    )
    assert report_resp.status_code == 200, f"获取报告失败: {report_resp.text}"
    report = report_resp.json()

    print(f"\n报告基础字段:")
    print(f"  id={report['id']}, contract_id={report['contract_id']}")
    print(f"  overall_score={report['overall_score']}")
    print(f"  risk_level={report['risk_level']}")
    print(f"  risk_clause_count={report['risk_clause_count']}")
    print(f"  review_duration_ms={report['review_duration_ms']}ms")
    print(f"  summary长度={len(report.get('summary') or '')}")

    print(f"\nV4.0对抗式审查字段验证:")
    v40_fields = [
        ("primary_risks", list),
        ("review_check", dict),
        ("adverse_opinions", list),
        ("debate_log", list),
        ("unresolved_issues", list),
        ("adverse_opinion_count", int),
        ("unresolved_count", int),
    ]
    all_pass = True
    for field, expected_type in v40_fields:
        raw = report.get(field)
        if field in ("adverse_opinion_count", "unresolved_count"):
            value = raw
            status = "✓" if isinstance(value, int) and value >= 0 else "✗"
            print(f"  {status} {field}: {value}")
            if not isinstance(value, int) or value < 0:
                all_pass = False
        else:
            # JSON字符串字段
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, expected_type):
                    status = "✓"
                    print(f"  {status} {field}: {expected_type.__name__} (长度={len(parsed)})")
                else:
                    status = "✗"
                    print(f"  {status} {field}: 类型错误, 期望{expected_type.__name__}, 实际{type(parsed).__name__}")
                    all_pass = False
            except Exception as e:
                status = "✗"
                print(f"  {status} {field}: 解析失败 - {e}")
                all_pass = False

    # ==================== 5. 打印V4.0审查详情 ====================
    print("\n" + "=" * 70)
    print("V4.0 多Agent对抗式审查详情")
    print("=" * 70)

    primary_risks = json.loads(report.get("primary_risks") or "[]")
    print(f"\n【主审Agent】识别风险 {len(primary_risks)} 条:")
    for i, risk in enumerate(primary_risks[:5], 1):
        print(f"  [{i}] 条款{risk.get('clause_index')} | {risk.get('risk_type')} | {risk.get('risk_level')}")
        desc = risk.get('description', '')
        print(f"      {desc[:100]}")

    review_check = json.loads(report.get("review_check") or "{}")
    print(f"\n【复核Agent】规则复检:")
    print(f"  approved(规则确认): {review_check.get('approved_count', 0)}条")
    print(f"  disputed(待争议):   {review_check.get('disputed_count', 0)}条")
    print(f"  missed(主审遗漏):   {review_check.get('missed_count', 0)}条")

    adverse_opinions = json.loads(report.get("adverse_opinions") or "[]")
    print(f"\n【反方Agent】反对意见 {len(adverse_opinions)} 条:")
    for i, ao in enumerate(adverse_opinions[:3], 1):
        opp = ao.get('opposition', '')
        print(f"  [{i}] 条款{ao.get('clause_index')}: {opp[:80]}")

    debate_log = json.loads(report.get("debate_log") or "[]")
    print(f"\n【对抗辩论】{len(debate_log)} 轮:")
    for dl in debate_log[:3]:
        print(f"  轮次{dl.get('round')} [{dl.get('status', '')}]")
        print(f"    主审: {dl.get('primary_response', '')[:80]}")
        print(f"    反方: {dl.get('adverse_response', '')[:80]}")

    unresolved = json.loads(report.get("unresolved_issues") or "[]")
    print(f"\n【未解决问题】{len(unresolved)} 条:")
    for u in unresolved:
        print(f"  - 条款{u.get('clause_index')}: {u.get('issue', '')[:80]}")

    # ==================== 6. 测试结论 ====================
    print("\n" + "=" * 70)
    if all_pass and report['overall_score'] is not None:
        print("✓ 测试通过：V4.0多Agent对抗式审查工作流端到端验证成功")
        print(f"  审查耗时: {report['review_duration_ms']/1000:.1f}s")
        print(f"  风险评分: {report['overall_score']} (level={report['risk_level']})")
        print(f"  风险条款: {report['risk_clause_count']}条")
        print(f"  反对意见: {report['adverse_opinion_count']}条")
        print(f"  辩论轮数: {len(debate_log)}")
        print(f"  未解决:   {report['unresolved_count']}条")
        sys.exit(0)
    else:
        print("✗ 测试失败：V4.0字段未完全填充")
        sys.exit(1)


if __name__ == "__main__":
    main()
