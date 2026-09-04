"""调试工作流返回值结构（V4.0对抗式审查验证）"""
import asyncio
import sys
import os
import json

# 添加backend路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.agent.workflow import ContractReviewWorkflow


CONTRACT_TEXT = """房屋租赁合同

甲方（出租方）：张三
乙方（承租方）：李四

第一条 租赁物
甲方将位于北京市朝阳区的房屋出租给乙方使用，建筑面积100平方米。

第二条 租赁期限
租赁期限为12个月，自2026年1月1日起至2026年12月31日止。乙方无权提前解除合同，否则甲方有权扣除全部押金。

第三条 租金
月租金为人民币5000元，乙方应于每月1日前支付。甲方有权随时单方面调整租金。

第四条 押金
乙方应于合同签订时支付押金10000元。合同期满后，甲方有权以任何理由不退还押金，且乙方不得提出任何异议。

第五条 维修责任
房屋的所有维修费用由乙方承担，甲方不承担任何责任。

第六条 违约责任
乙方违约应支付违约金50000元，甲方违约无需承担任何违约责任。

第七条 争议解决
因本合同引起的争议，由甲方所在地法院管辖。最终解释权归甲方所有。

第八条 合同生效
本合同自双方签字之日起生效。
"""


async def main():
    print("=" * 60)
    print("智法通 V4.0 多Agent对抗式审查工作流调试")
    print("=" * 60)

    workflow = ContractReviewWorkflow()
    print(f"工作流节点数: {len(workflow.graph.nodes)}")
    print(f"工作流边数: {len(workflow.graph.edges)}")

    print("\n开始执行合同审查工作流...")
    result = await workflow.run(
        contract_content=CONTRACT_TEXT,
        contract_type="租赁合同",
    )

    print("\n工作流返回值字段:")
    if isinstance(result, dict):
        for key in sorted(result.keys()):
            value = result[key]
            if isinstance(value, (list, dict)):
                print(f"  {key}: {type(value).__name__} (长度={len(value) if hasattr(value, '__len__') else 'N/A'})")
            else:
                print(f"  {key}: {value}")

    # 验证V4.0对抗式审查字段
    print("\n" + "=" * 60)
    print("V4.0 多Agent对抗式审查字段验证")
    print("=" * 60)
    v40_fields = [
        "primary_risks", "review_check", "adverse_opinions",
        "debate_log", "unresolved_issues",
        "adverse_opinion_count", "unresolved_count",
    ]
    for field in v40_fields:
        value = result.get(field)
        if value is None:
            print(f"  ✗ {field}: 缺失")
        elif isinstance(value, (list, dict)):
            print(f"  ✓ {field}: {type(value).__name__} (长度={len(value)})")
        else:
            print(f"  ✓ {field}: {value}")

    # 打印主审风险
    print("\n主审Agent识别的风险:")
    for i, risk in enumerate(result.get("primary_risks", [])[:5]):
        print(f"  [{i+1}] 条款{risk.get('clause_index')} | {risk.get('risk_type')} | {risk.get('risk_level')}")
        print(f"      {risk.get('description', '')[:80]}")

    # 打印复核结果
    print("\n复核Agent规则复检:")
    rc = result.get("review_check", {})
    print(f"  approved: {rc.get('approved_count', 0)}条")
    print(f"  disputed: {rc.get('disputed_count', 0)}条")
    print(f"  missed:   {rc.get('missed_count', 0)}条")

    # 打印反方意见
    print("\n反方Agent反对意见:")
    for i, ao in enumerate(result.get("adverse_opinions", [])[:5]):
        print(f"  [{i+1}] 条款{ao.get('clause_index')}: {ao.get('opposition', '')[:80]}")

    # 打印辩论记录
    print("\n对抗辩论记录:")
    for i, dl in enumerate(result.get("debate_log", [])[:5]):
        print(f"  [轮次{dl.get('round')}] {dl.get('status', '')}")
        print(f"    主审: {dl.get('primary_response', '')[:80]}")
        print(f"    反方: {dl.get('adverse_response', '')[:80]}")

    # 打印最终评分
    print("\n" + "=" * 60)
    print("最终审查结论")
    print("=" * 60)
    print(f"  risk_score:    {result.get('risk_score')}")
    print(f"  overall_score: {result.get('overall_score')}")
    print(f"  risk_level:    {result.get('risk_level')}")
    print(f"  needs_manual_review: {result.get('needs_manual_review')}")


if __name__ == "__main__":
    asyncio.run(main())
