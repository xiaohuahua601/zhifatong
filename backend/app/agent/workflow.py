"""
智法通 - LangGraph工作流构建模块

使用LangGraph构建合同审查的有向图工作流，
定义节点间的执行顺序和条件分支。

V4.0增强内容（参考文档4.3节"多Agent对抗式审查"）：
- 两阶段并行结构：split→(completeness_check+classify_clauses)→risk_detect→(compliance_check+consistency_check)
- V4.0新增：对抗式审查阶段，三方博弈提升风险识别准确率
  * adverse_attack（反方Agent攻击）：汇总主审风险 + 规则复检 + 站在弱势方质疑
  * debate（对抗辩论）：主审Agent回应反方质疑，记录debate_log与unresolved_issues
- 条件路由：高风险(risk_score>=80)→直接报告，低/中风险→生成建议
- MemorySaver checkpointer：支持中断恢复
- interrupt_before=["risk_detect"]：风险识别前可中断人工确认
- run方法支持thread_id配置和中断恢复

工作流拓扑（V4.0）：
  parse_doc → split_clauses
    → [completeness_check || classify_clauses] → risk_detect
    → [compliance_check || consistency_check]
    → adverse_attack → debate → risk_score
    → route_by_risk_level
       - high_risk → report_generate → END
       - normal    → suggestions → report_generate → END
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agent.state import ContractReviewState
from app.agent.nodes import (
    parse_document,
    split_clauses,
    check_completeness,
    classify_clauses,
    detect_risk_clauses,
    check_compliance,
    check_consistency,
    adverse_agent_attack,
    debate_round,
    calculate_risk_score,
    generate_suggestions,
    generate_report,
)


class ContractReviewWorkflow:
    """合同审查工作流类

    构建并管理LangGraph合同审查工作流。

    工作流步骤（V4.0，参考文档4.3节状态图）：
    1. 文档解析(parse_doc) → 2. 条款分割(split_clauses)
    3. 第一阶段并行：完整性检查(completeness_check) + 条款分类(classify_clauses)
    4. 风险检测(risk_detect)  [支持中断人工确认]
    5. 第二阶段并行：合规性检查(compliance_check) + 一致性检查(consistency_check)
    6. V4.0新增 对抗式审查：
       - 反方Agent攻击(adverse_attack)：汇总主审风险 + 规则复检 + 弱势方质疑
       - 对抗辩论(debate)：主审回应反方质疑，识别unresolved_issues
    7. 风险评分(risk_score) → 条件路由
       - 高风险 → 直接报告生成(report_generate) [标记人工审查]
       - 低/中风险 → 建议生成(suggestions) → 报告生成(report_generate)
    8. 报告生成(report_generate) → END
    """

    def __init__(self):
        """初始化工作流

        构建工作流图并使用MemorySaver编译。
        V4.0修复：移除 interrupt_before=["risk_detect"]，
        因为自动化审查API需要工作流一次跑完。
        MemorySaver checkpointer 保留，支持未来需要中断恢复的场景（如调用方显式调用 resume）。
        """
        self.graph = self._build_graph()
        # 使用MemorySaver作为checkpointer，支持中断恢复和状态查询
        checkpointer = MemorySaver()
        # 编译工作流图（不启用自动中断，让工作流一次跑完）
        self.app = self.graph.compile(
            checkpointer=checkpointer,
        )

    def _build_graph(self) -> StateGraph:
        """构建工作流图（V4.0，参考文档4.3.3节）

        定义节点和边，构建合同审查的完整工作流。
        采用两阶段并行结构 + V4.0新增的对抗式审查阶段：
        - 第一阶段：完整性检查 + 条款分类（并行）
        - 第二阶段：合规性检查 + 一致性检查（并行）
        - V4.0新增：反方Agent攻击 → 对抗辩论（线性，串接在二阶段并行后）
        条件路由：高风险→直接报告，低/中风险→生成建议

        Returns:
            StateGraph实例
        """
        # 创建状态图
        workflow = StateGraph(ContractReviewState)

        # ==================== 添加所有12个节点（V4.0新增2个）====================
        workflow.add_node("parse_doc", parse_document)                       # 文档解析
        workflow.add_node("split_clauses", split_clauses)                    # 条款分割
        workflow.add_node("completeness_check", check_completeness)          # 完整性检查
        workflow.add_node("classify_clauses", classify_clauses)              # 条款分类
        workflow.add_node("risk_detect", detect_risk_clauses)                # 风险检测
        workflow.add_node("compliance_check", check_compliance)              # 合规性检查
        workflow.add_node("consistency_check", check_consistency)            # 一致性检查
        # V4.0新增：多Agent对抗式审查节点
        workflow.add_node("adverse_attack", adverse_agent_attack)            # 反方Agent攻击
        workflow.add_node("debate", debate_round)                            # 对抗辩论
        workflow.add_node("risk_score", calculate_risk_score)                # 风险评分
        workflow.add_node("suggestions", generate_suggestions)               # 建议生成
        workflow.add_node("report_generate", generate_report)                # 报告生成

        # ==================== 设置入口 ====================
        workflow.set_entry_point("parse_doc")

        # ==================== 线性边：解析→拆分 ====================
        workflow.add_edge("parse_doc", "split_clauses")

        # ==================== 第一阶段并行：完整性检查 + 条款分类 ====================
        workflow.add_edge("split_clauses", "completeness_check")
        workflow.add_edge("split_clauses", "classify_clauses")

        # 汇合后进入风险检测
        workflow.add_edge("completeness_check", "risk_detect")
        workflow.add_edge("classify_clauses", "risk_detect")

        # ==================== 第二阶段并行：合规性检查 + 一致性检查 ====================
        workflow.add_edge("risk_detect", "compliance_check")
        workflow.add_edge("risk_detect", "consistency_check")

        # V4.0修改：二阶段并行汇合后进入反方Agent攻击（而非直接进入风险评分）
        # 让对抗式审查基于合规性+一致性+风险检测的完整结果进行三方博弈
        workflow.add_edge("compliance_check", "adverse_attack")
        workflow.add_edge("consistency_check", "adverse_attack")

        # ==================== V4.0新增：对抗式审查串联 ====================
        # 反方Agent攻击 → 对抗辩论 → 风险评分
        workflow.add_edge("adverse_attack", "debate")
        workflow.add_edge("debate", "risk_score")

        # ==================== 建议生成与条件路由 ====================
        # V6.0.4修复：高风险合同同样需要生成修改建议（此前risk_score>=80直接跳过
        # suggestions节点，导致综合评分为0的极高风险合同报告"修改建议"为空——
        # 而高风险合同恰恰是最需要修改建议的场景）。现统一走建议生成节点，
        # 高风险标记（needs_manual_review）仍在generate_report节点内基于分数判定。
        workflow.add_edge("risk_score", "suggestions")

        # 建议生成后进入报告
        workflow.add_edge("suggestions", "report_generate")

        # 报告生成后结束
        workflow.add_edge("report_generate", END)

        return workflow

    async def run(
        self,
        contract_content: str,
        contract_type: str = "通用合同",
        thread_id: str = None,
    ) -> dict:
        """执行合同审查工作流（V2.0增强版）

        支持thread_id配置和中断恢复：
        - 接受可选的thread_id参数，用于关联会话和检查点
        - 使用config = {"configurable": {"thread_id": thread_id}}调用graph.ainvoke
        - 处理中断情况（返回中断信息）
        - 支持恢复执行（传入None state从checkpoint恢复）

        Args:
            contract_content: 合同全文内容
            contract_type: 合同类型
            thread_id: 会话线程ID（用于检查点和中断恢复）。
                       如果未提供，自动生成基于时间戳的ID。

        Returns:
            审查结果字典，包含：
            - 正常完成：report/review_report等字段
            - 中断时：__interrupt__字段包含中断信息
        """
        import uuid

        # 生成thread_id（如果未提供）
        if thread_id is None:
            thread_id = f"contract-{uuid.uuid4().hex[:8]}"

        # 构建LangGraph配置（关联thread_id用于检查点）
        config = {"configurable": {"thread_id": thread_id}}

        # 初始化状态（同时设置contract_content和contract_text以兼容V2.0）
        initial_state = ContractReviewState(
            contract_content=contract_content,
            contract_text=contract_content,
            contract_type=contract_type,
            retry_count=0,
        )

        # 执行工作流（可能在interrupt_before=["risk_detect"]处中断）
        result = await self.app.ainvoke(initial_state, config)

        # 检查是否在中断点暂停
        # LangGraph在中断时会返回当前状态，可通过app.get_state(config)检查
        try:
            state_snapshot = await self.app.aget_state(config)
            # 如果next不为空，说明工作流在中断点暂停
            if state_snapshot and state_snapshot.next:
                return {
                    "__interrupt__": True,
                    "thread_id": thread_id,
                    "interrupted_at": str(state_snapshot.next),
                    "current_step": result.get("current_step", ""),
                    "message": f"工作流在 {state_snapshot.next} 前中断，等待人工确认后恢复",
                    "partial_state": result,
                    # 提供恢复说明
                    "resume_hint": "调用 run(contract_content=None, thread_id=当前thread_id) 恢复执行",
                }
        except Exception:
            # aget_state不可用时忽略，按正常流程处理
            pass

        # 返回最终报告（兼容新旧字段名）
        return result.get("report") or result.get("review_report") or result

    async def resume(
        self,
        thread_id: str,
    ) -> dict:
        """从检查点恢复执行工作流

        当工作流在interrupt_before=["risk_detect"]处中断后，
        人工确认完成后调用此方法恢复执行。

        Args:
            thread_id: 会话线程ID（与run方法使用相同的thread_id）

        Returns:
            审查结果字典
        """
        config = {"configurable": {"thread_id": thread_id}}

        # 传入None作为state，从checkpoint恢复继续执行
        result = await self.app.ainvoke(None, config)

        # 返回最终报告（兼容新旧字段名）
        return result.get("report") or result.get("review_report") or result
