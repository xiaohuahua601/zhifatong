"""
智法通 - LangGraph状态定义模块

定义合同审查工作流的状态数据结构，
包含合同内容、解析结果、各类检查结果和最终报告。

参考V2.0文档4.3.1节的状态定义，同时保留向后兼容字段。

重要说明：
    本工作流包含两处并行节点（fan-out/fan-in）：
    1. split_clauses → completeness_check + classify_clauses → risk_detect
    2. risk_detect → compliance_check + consistency_check → risk_score
    当多个并行节点同时返回相同的状态键时，LangGraph 需要 reducer 函数来合并值。
    因此所有字段均使用 Annotated[type, last_value] 注解，确保并行节点返回值时
    保留最后一个非None值，避免 "Can receive only one value per step" 错误。
"""

from typing import TypedDict, Optional, List, Annotated


# ============================================================
# Reducer 函数：用于合并并行节点返回的状态值
# ============================================================

def last_value(left, right):
    """保留最后一个非None值的reducer函数

    LangGraph并行节点（fan-out）同时返回相同的状态键时，
    使用此函数合并：优先返回right（最新值），若right为None则返回left。

    Args:
        left:  前一个节点返回的值（或初始值）
        right: 当前节点返回的值

    Returns:
        合并后的值（优先返回right）
    """
    # 如果right不为None，返回right（最新值优先）
    if right is not None:
        return right
    # 否则返回left（保留之前的值）
    return left


def merge_list(left, right):
    """列表合并reducer函数

    用于合并并行节点返回的列表字段（如风险条款、合规问题等）。
    将两个列表拼接去重后返回。

    Args:
        left:  前一个节点返回的列表
        right: 当前节点返回的列表

    Returns:
        合并后的列表
    """
    if left is None and right is None:
        return []
    if left is None:
        return right if isinstance(right, list) else []
    if right is None:
        return left if isinstance(left, list) else []
    # 合并并去重（基于dict的id字段或直接值比较）
    result = list(left) + list(right)
    return result


# ============================================================
# 合同审查工作流状态定义
# ============================================================

class ContractReviewState(TypedDict, total=False):
    """合同审查工作流状态

    在LangGraph工作流的各个节点之间传递状态数据。
    每个节点读取需要的字段，处理后将结果写入状态。

    字段说明：
    - V2.0新增字段遵循文档4.3.1节定义
    - 保留旧字段以维持向后兼容（contract_content/parsed_text/overall_score等）
    - 所有字段使用Annotated[type, last_value]确保并行节点合并正确
    """

    # ==================== 输入数据 ====================
    # 合同全文内容（旧字段，向后兼容，与contract_text等价）
    contract_content: Annotated[str, last_value]
    # 合同全文（V2.0文档4.3.1节标准字段名）
    contract_text: Annotated[str, last_value]
    # 合同类型（如：买卖合同、租赁合同、劳动合同、服务合同、保密合同等）
    contract_type: Annotated[str, last_value]
    # 合同当事方信息列表（V2.0新增）
    # 每个元素形如 {"role": "甲方", "name": "xxx公司", "id": "统一社会信用代码"}
    parties: Annotated[list, last_value]

    # ==================== 解析阶段 ====================
    # 解析后的合同文本（清理格式后的，旧字段，向后兼容）
    parsed_text: Annotated[str, last_value]
    # 拆分后的条款列表（V2.0：list[dict]，每个元素含 index/text/type/risk_level）
    # 旧代码可能传入 list[str]，节点函数需兼容两种格式
    clauses: Annotated[list, last_value]
    # 条款数量
    clause_count: Annotated[int, last_value]

    # ==================== 完整性检查 ====================
    # 完整性检查结果（旧字段，向后兼容）
    completeness: Annotated[dict, last_value]
    # 完整性检查结果（V2.0文档4.3.1节标准字段名）
    # 结构：{"total_required": int, "missing_count": int,
    #        "missing_clauses": list, "completeness_ratio": float}
    completeness_check: Annotated[dict, last_value]
    # 缺失的必要条款列表（旧字段，向后兼容）
    missing_clauses: Annotated[list, last_value]
    # 完整性评分（0-100，旧字段，向后兼容）
    completeness_score: Annotated[float, last_value]

    # ==================== 条款分类 ====================
    # 条款分类结果（每个条款的类型标签）
    clause_categories: Annotated[list, last_value]
    # 关键条款列表
    key_clauses: Annotated[list, last_value]

    # ==================== 风险检测 ====================
    # 风险条款列表
    risk_clauses: Annotated[list, last_value]
    # 风险条款数量
    risk_clause_count: Annotated[int, last_value]
    # 最高风险等级
    max_risk_level: Annotated[str, last_value]

    # ==================== 多Agent对抗式审查（V4.0新增，参考文档4.3节）====================
    # 主审Agent风险清单：基于risk_clauses + compliance_issues汇总的中立专业审查结论
    primary_risks: Annotated[list, last_value]
    # 复核Agent复检结果：基于规则引擎对主审结论的二次校验
    # 结构：{"approved": [...], "disputed": [...], "missed": [...]}
    review_check: Annotated[dict, last_value]
    # 反方Agent反对意见：站在合同弱势方立场质疑每一条款
    # 每个元素形如 {"clause_index": int, "opposition": str, "weak_party_impact": str,
    #               "legal_basis": str, "demanded_revision": str}
    adverse_opinions: Annotated[list, last_value]
    # 对抗辩论记录（多轮）：主审回应反方质疑的过程留痕
    # 每个元素形如 {"round": int, "issue": str, "primary_response": str,
    #               "adverse_response": str, "status": "consensus/unresolved"}
    debate_log: Annotated[list, last_value]
    # 未达成共识的问题列表（辩论后仍存在分歧的条款）
    unresolved_issues: Annotated[list, last_value]

    # ==================== 合规性检查 ====================
    # 合规性检查结果（旧字段，向后兼容）
    compliance: Annotated[dict, last_value]
    # 合规问题列表（V2.0文档4.3.1节标准字段名）
    # 每个元素形如 {"clause_index": int, "clause_text": str,
    #               "conflicting_law": str, "conflict_description": str, "severity": str}
    compliance_issues: Annotated[list, last_value]
    # 违规条款列表（旧字段，向后兼容）
    violation_clauses: Annotated[list, last_value]
    # 合规性评分（0-100，旧字段，向后兼容）
    compliance_score: Annotated[float, last_value]

    # ==================== 一致性检查 ====================
    # 一致性检查结果（旧字段，向后兼容）
    consistency: Annotated[dict, last_value]
    # 一致性问题列表（V2.0文档4.3.1节标准字段名）
    # 每个元素形如 {"clause_a": int, "clause_b": int,
    #               "conflict_description": str, "severity": str}
    consistency_issues: Annotated[list, last_value]
    # 矛盾条款对（旧字段，向后兼容）
    contradiction_pairs: Annotated[list, last_value]
    # 一致性评分（0-100，旧字段，向后兼容）
    consistency_score: Annotated[float, last_value]

    # ==================== 风险评分 ====================
    # 综合风险评分（0-100，V2.0文档4.3.1节标准字段名，越高越危险）
    risk_score: Annotated[float, last_value]
    # 总体安全评分（0-100，旧字段，向后兼容，越高越安全）
    overall_score: Annotated[float, last_value]
    # 总体风险等级
    risk_level: Annotated[str, last_value]

    # ==================== 建议生成 ====================
    # 修改建议列表（V2.0文档4.3.1节标准字段名）
    modification_suggestions: Annotated[list, last_value]
    # 修改建议列表（旧字段，向后兼容）
    suggestions: Annotated[list, last_value]

    # ==================== 报告生成 ====================
    # 完整审查报告（V2.0文档4.3.1节标准字段名）
    review_report: Annotated[dict, last_value]
    # 完整审查报告（旧字段，向后兼容）
    report: Annotated[dict, last_value]
    # 审查摘要
    summary: Annotated[str, last_value]

    # ==================== 流程控制（V2.0文档4.3.1节）====================
    # 当前执行步骤名称
    current_step: Annotated[str, last_value]
    # 错误信息（某个节点处理失败时设置）
    error: Annotated[str, last_value]
    # 重试次数
    retry_count: Annotated[int, last_value]
