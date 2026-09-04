"""
合规检查MCP服务器

提供合同条款合规检查和法规更新通知功能，支持：
- 检查合同条款与现行法规的一致性
- 使用Ollama qwen2.5:1.5b进行深度合规分析
- 提供法规更新通知
- 合规风险等级评估
"""

import json
import os
from datetime import datetime
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ============================================================
# 常量配置
# ============================================================

# Ollama服务地址和模型名称
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:1.5b"

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LAW_ARTICLES_FILE = os.path.join(DATA_DIR, "law_articles.json")

# 创建FastAPI应用实例
app = FastAPI(
    title="合规检查MCP服务器",
    description="提供合同条款合规检查和法规更新通知服务",
    version="1.0.0",
)


# ============================================================
# 数据模型定义
# ============================================================

class CheckComplianceRequest(BaseModel):
    """合规检查请求模型"""
    content: str = Field(..., description="待检查的合同条款或文本内容")
    contract_type: Optional[str] = Field(
        None,
        description="合同类型：sale(买卖)、lease(租赁)、employment(劳动)、service(服务)、nda(保密协议)",
    )
    check_scope: Optional[list[str]] = Field(
        None,
        description="检查范围，如'劳动法'、'合同法'、'公司法'，默认全部适用法律",
    )
    strict_mode: bool = Field(False, description="是否启用严格模式（更严格的合规标准）")


class GetRegulationUpdatesRequest(BaseModel):
    """获取法规更新请求模型"""
    law_name: Optional[str] = Field(None, description="法律名称筛选，如'民法典'、'劳动合同法'")
    since_date: Optional[str] = Field(None, description="起始日期筛选，格式YYYY-MM-DD")
    category: Optional[str] = Field(None, description="法规类别筛选，如'劳动'、'合同'、'公司'")


class ComplianceIssue(BaseModel):
    """合规问题模型"""
    issue_type: str = Field(..., description="问题类型：违法风险/合规建议/格式条款/权利义务失衡")
    severity: str = Field(..., description="严重程度：高/中/低")
    description: str = Field(..., description="问题描述")
    suggestion: str = Field(..., description="修改建议")
    related_law: Optional[str] = Field(None, description="相关法律条文")
    clause_reference: Optional[str] = Field(None, description="涉及的具体条款位置")


class CheckComplianceResult(BaseModel):
    """合规检查结果模型"""
    is_compliant: bool = Field(..., description="是否合规")
    risk_level: str = Field(..., description="整体风险等级：低/中/高")
    issues: list[ComplianceIssue] = Field(default_factory=list, description="合规问题列表")
    applicable_laws: list[str] = Field(default_factory=list, description="适用的法律法规列表")
    ai_analysis: Optional[str] = Field(None, description="AI综合合规分析")


class RegulationUpdate(BaseModel):
    """法规更新模型"""
    law_name: str = Field(..., description="法律名称")
    update_type: str = Field(..., description="更新类型：新颁布/修订/废止/司法解释")
    update_date: str = Field(..., description="更新日期")
    summary: str = Field(..., description="更新摘要")
    key_changes: list[str] = Field(default_factory=list, description="关键变化")
    impact_areas: list[str] = Field(default_factory=list, description="影响领域")


class GetRegulationUpdatesResult(BaseModel):
    """法规更新结果模型"""
    total: int = Field(..., description="更新总数")
    updates: list[RegulationUpdate] = Field(default_factory=list, description="法规更新列表")


# ============================================================
# 数据加载
# ============================================================

def load_law_articles() -> list[dict[str, Any]]:
    """从JSON文件加载法条数据"""
    try:
        with open(LAW_ARTICLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("法律数据", [])
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


# 全局加载法条数据
LAW_ARTICLES: list[dict[str, Any]] = load_law_articles()


# ============================================================
# 内置法规更新数据（模拟数据源）
# ============================================================

REGULATION_UPDATES: list[dict[str, Any]] = [
    {
        "law_name": "中华人民共和国公司法",
        "update_type": "修订",
        "update_date": "2024-07-01",
        "summary": "新修订的《公司法》正式施行，主要涉及注册资本认缴制改革、股东权利保护强化等",
        "key_changes": [
            "有限责任公司股东认缴出资额须自公司成立之日起五年内缴足",
            "完善股东知情权，股东可查阅会计凭证",
            "强化控股股东和实际控制人责任",
            "新增审计委员会制度替代监事会的选择",
        ],
        "impact_areas": ["公司治理", "注册资本", "股东权利", "企业合规"],
    },
    {
        "law_name": "最高人民法院关于适用《中华人民共和国民法典》合同编通则若干问题的解释",
        "update_type": "司法解释",
        "update_date": "2023-12-05",
        "summary": "民法典合同编通则司法解释施行，对合同订立、效力、履行等问题作出明确规定",
        "key_changes": [
            "明确预约合同与本约合同的区分标准",
            "细化格式条款的认定和效力规则",
            "完善代位权和撤销权的行使条件",
            "明确抵销的效力及顺序",
        ],
        "impact_areas": ["合同订立", "格式条款", "债权保全", "合同履行"],
    },
    {
        "law_name": "中华人民共和国劳动合同法",
        "update_type": "修订",
        "update_date": "2012-12-28",
        "summary": "劳动合同法修正案施行，主要修改劳务派遣相关规定",
        "key_changes": [
            "劳务派遣用工比例不得超过用工总量的10%",
            "劳务派遣只能用于临时性、辅助性、替代性岗位",
            "同工同酬原则进一步明确",
            "加大违法劳务派遣的处罚力度",
        ],
        "impact_areas": ["劳务派遣", "用工合规", "同工同酬"],
    },
    {
        "law_name": "最高人民法院关于审理民间借贷案件适用法律若干问题的规定",
        "update_type": "修订",
        "update_date": "2020-08-20",
        "summary": "民间借贷司法解释修订，调整利率保护上限为LPR四倍",
        "key_changes": [
            "以LPR四倍取代原24%/36%的利率标准",
            "职业放贷人签订的借贷合同无效",
            "完善民间借贷举证责任分配",
            "明确P2P网络借贷的法律适用",
        ],
        "impact_areas": ["民间借贷", "利率上限", "借贷合同效力"],
    },
    {
        "law_name": "中华人民共和国反不正当竞争法",
        "update_type": "修订",
        "update_date": "2019-04-23",
        "summary": "反不正当竞争法修订，强化商业秘密保护",
        "key_changes": [
            "扩大商业秘密保护范围",
            "降低商业秘密侵权举证门槛",
            "提高商业秘密侵权赔偿标准",
            "增加惩罚性赔偿规定",
        ],
        "impact_areas": ["商业秘密", "不正当竞争", "知识产权保护"],
    },
    {
        "law_name": "中华人民共和国个人信息保护法",
        "update_type": "新颁布",
        "update_date": "2021-11-01",
        "summary": "个人信息保护法正式施行，确立个人信息处理的基本规则",
        "key_changes": [
            "确立个人信息处理的合法依据",
            "规定敏感个人信息的特殊保护规则",
            "明确个人信息跨境提供的条件",
            "加大违法处理个人信息的处罚力度",
        ],
        "impact_areas": ["个人信息保护", "数据合规", "跨境数据传输"],
    },
]


# ============================================================
# Ollama合规分析辅助函数
# ============================================================

async def compliance_analysis_with_ollama(
    content: str,
    contract_type: Optional[str] = None,
    check_scope: Optional[list[str]] = None,
    strict_mode: bool = False,
) -> dict[str, Any]:
    """
    使用Ollama本地模型进行合规分析

    Args:
        content: 待检查的文本内容
        contract_type: 合同类型
        check_scope: 检查范围
        strict_mode: 是否严格模式

    Returns:
        合规分析结果字典
    """
    # 构建上下文信息
    type_map = {
        "sale": "买卖合同",
        "lease": "租赁合同",
        "employment": "劳动合同",
        "service": "服务合同",
        "nda": "保密协议",
    }
    contract_context = f"（合同类型：{type_map.get(contract_type, '通用')}）" if contract_type else ""
    scope_desc = f"检查范围：{', '.join(check_scope)}" if check_scope else "检查范围：全部适用法律"
    mode_desc = "严格模式" if strict_mode else "标准模式"

    prompt = (
        f"请对以下合同条款进行法律合规检查{contract_context}，{scope_desc}，{mode_desc}。\n\n"
        f"条款内容：{content}\n\n"
        f"请按以下JSON格式返回结果（不要返回其他内容）：\n"
        f'{{"is_compliant": true/false, "risk_level": "低/中/高", '
        f'"issues": [{{"issue_type": "问题类型（违法风险/合规建议/格式条款/权利义务失衡）", '
        f'"severity": "高/中/低", "description": "问题描述", "suggestion": "修改建议", '
        f'"related_law": "相关法条", "clause_reference": "涉及条款位置"}}], '
        f'"applicable_laws": ["适用的法律法规"], '
        f'"analysis": "综合合规分析"}}'
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 1000},
                },
            )
            if response.status_code == 200:
                result_text = response.json().get("response", "").strip()
                try:
                    json_start = result_text.find("{")
                    json_end = result_text.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = result_text[json_start:json_end]
                        return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                return {
                    "is_compliant": True,
                    "risk_level": "低",
                    "issues": [],
                    "applicable_laws": [],
                    "analysis": result_text if result_text else "AI合规分析服务返回格式异常，建议人工复核",
                }
            return {
                "is_compliant": True,
                "risk_level": "低",
                "issues": [],
                "applicable_laws": [],
                "analysis": "AI合规分析服务暂时不可用，建议人工复核",
            }
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        return {
            "is_compliant": True,
            "risk_level": "低",
            "issues": [],
            "applicable_laws": [],
            "analysis": "AI合规分析服务暂时不可用，建议人工复核",
        }


# ============================================================
# 基于规则的合规预检查
# ============================================================

def rule_based_compliance_check(
    content: str,
    contract_type: Optional[str] = None,
    check_scope: Optional[list[str]] = None,
) -> tuple[list[ComplianceIssue], list[str]]:
    """
    基于规则的合规预检查（不依赖LLM）

    检查常见的合规风险模式：
    - 劳动合同：排除劳动者权利、违反强制性规定
    - 格式条款：不合理免除责任、限制权利
    - 通用：违反强制性规定、公序良俗

    Args:
        content: 待检查的文本内容
        contract_type: 合同类型
        check_scope: 检查范围

    Returns:
        (合规问题列表, 适用法律列表)
    """
    issues: list[ComplianceIssue] = []
    applicable_laws: list[str] = []

    # 劳动合同合规检查
    if contract_type == "employment" or (check_scope and "劳动法" in check_scope):
        applicable_laws.extend(["劳动合同法", "劳动法"])

        labor_patterns = [
            ("不缴纳社保", "违法风险", "高", "约定不缴纳社会保险违反强制性规定", "建议依法缴纳社会保险", "劳动法第72条"),
            ("自愿放弃社保", "违法风险", "高", "劳动者自愿放弃社保的约定无效", "建议删除该条款，依法缴纳社会保险", "劳动法第72条"),
            ("不支付加班费", "违法风险", "高", "不支付加班费违反强制性规定", "建议依法支付加班费", "劳动法第44条"),
            ("自愿放弃加班费", "违法风险", "高", "劳动者自愿放弃加班费的约定无效", "建议删除该条款", "劳动法第44条"),
            ("一律不调岗", "合规建议", "中", "完全禁止调岗可能限制用人单位合理用工自主权", "建议约定合理的调岗条件和程序", "劳动合同法第40条"),
            ("工资中包含社保", "违法风险", "高", "工资中包含社保个人缴纳部分的约定可能无效", "建议社保单独缴纳，不计入工资", "社会保险法第60条"),
            ("离职扣工资", "违法风险", "高", "离职扣发工资的约定违反强制性规定", "建议删除该条款，工资应按时足额支付", "劳动法第50条"),
        ]
        for pattern, issue_type, severity, desc, suggestion, law in labor_patterns:
            if pattern in content:
                issues.append(
                    ComplianceIssue(
                        issue_type=issue_type,
                        severity=severity,
                        description=desc,
                        suggestion=suggestion,
                        related_law=law,
                    )
                )

    # 格式条款合规检查
    format_patterns = [
        ("最终解释权归", "格式条款", "中", "最终解释权条款属于无效格式条款", "建议删除该条款", "民法典第497条"),
        ("概不退换", "格式条款", "中", "概不退换条款可能被认定为无效格式条款", "建议约定合理的退换条件", "民法典第497条"),
        ("概不负责", "格式条款", "高", "单方免责条款可能被认定为无效格式条款", "建议约定合理的责任分担", "民法典第497条"),
        ("不得提出异议", "权利义务失衡", "中", "排除对方异议权的条款可能无效", "建议保留合理的异议渠道", "民法典第497条"),
        ("单方面变更", "权利义务失衡", "中", "单方面变更合同的权利可能构成权利义务失衡", "建议约定双方协商变更的机制", "民法典第497条"),
        ("不可转让", "合规建议", "低", "完全禁止转让可能限制合同权利的行使", "建议约定合理的转让条件", "民法典第545条"),
    ]
    for pattern, issue_type, severity, desc, suggestion, law in format_patterns:
        if pattern in content:
            issues.append(
                ComplianceIssue(
                    issue_type=issue_type,
                    severity=severity,
                    description=desc,
                    suggestion=suggestion,
                    related_law=law,
                )
            )

    # 通用合规检查
    general_patterns = [
        ("违反法律", "违法风险", "高", "合同中涉及违反法律的约定无效", "建议删除违法内容", "民法典第153条"),
        ("损害社会公共利益", "违法风险", "高", "损害社会公共利益的合同条款无效", "建议修改相关条款", "民法典第153条"),
    ]
    for pattern, issue_type, severity, desc, suggestion, law in general_patterns:
        if pattern in content:
            issues.append(
                ComplianceIssue(
                    issue_type=issue_type,
                    severity=severity,
                    description=desc,
                    suggestion=suggestion,
                    related_law=law,
                )
            )

    # 添加通用适用法律
    if "合同法" not in applicable_laws and "民法典" not in applicable_laws:
        applicable_laws.append("民法典")

    return issues, applicable_laws


# ============================================================
# MCP工具定义（OpenAI Function Calling格式）
# ============================================================

CHECK_COMPLIANCE_TOOL = {
    "type": "function",
    "function": {
        "name": "check_compliance",
        "description": "合规检查。检查合同条款与现行法规的一致性，使用AI和规则引擎双重检查，评估违法风险、格式条款、权利义务失衡等合规问题。",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "待检查的合同条款或文本内容"
                },
                "contract_type": {
                    "type": "string",
                    "description": "合同类型：sale(买卖)、lease(租赁)、employment(劳动)、service(服务)、nda(保密协议)",
                    "enum": ["sale", "lease", "employment", "service", "nda"]
                },
                "check_scope": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "检查范围，如'劳动法'、'合同法'、'公司法'，默认全部适用法律"
                },
                "strict_mode": {
                    "type": "boolean",
                    "description": "是否启用严格模式（更严格的合规标准）",
                    "default": False
                }
            },
            "required": ["content"]
        }
    }
}

GET_REGULATION_UPDATES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_regulation_updates",
        "description": "获取法规更新通知。查询近期法律法规的修订、新颁布、废止等更新信息，帮助企业及时了解法规变化。",
        "parameters": {
            "type": "object",
            "properties": {
                "law_name": {
                    "type": "string",
                    "description": "法律名称筛选，如'民法典'、'劳动合同法'、'公司法'"
                },
                "since_date": {
                    "type": "string",
                    "description": "起始日期筛选，格式YYYY-MM-DD"
                },
                "category": {
                    "type": "string",
                    "description": "法规类别筛选，如'劳动'、'合同'、'公司'、'数据'"
                }
            }
        }
    }
}

# 工具列表
TOOLS = [CHECK_COMPLIANCE_TOOL, GET_REGULATION_UPDATES_TOOL]


# ============================================================
# API路由
# ============================================================

@app.get("/tools", summary="获取工具列表")
async def get_tools():
    """返回当前MCP服务器提供的所有工具定义"""
    return {"tools": TOOLS}


@app.post("/tools/check_compliance", summary="合规检查")
async def check_compliance(request: CheckComplianceRequest) -> CheckComplianceResult:
    """
    合规检查工具

    使用规则引擎预检查 + Ollama AI验证双重机制：
    1. 先通过规则引擎进行快速预检查（检查常见违法模式）
    2. 再通过Ollama进行深度合规分析
    3. 合并结果并给出综合评估
    """
    # 第一步：基于规则的预检查
    rule_issues, rule_laws = rule_based_compliance_check(
        request.content,
        request.contract_type,
        request.check_scope,
    )

    # 第二步：使用Ollama进行AI合规分析
    ai_result = await compliance_analysis_with_ollama(
        request.content,
        request.contract_type,
        request.check_scope,
        request.strict_mode,
    )

    # 第三步：合并结果
    all_issues: list[ComplianceIssue] = []

    # 添加规则引擎发现的问题
    seen_descriptions = set()
    for issue in rule_issues:
        if issue.description not in seen_descriptions:
            all_issues.append(issue)
            seen_descriptions.add(issue.description)

    # 添加AI发现的问题
    ai_issues = ai_result.get("issues", [])
    for ai_issue in ai_issues:
        issue = ComplianceIssue(
            issue_type=ai_issue.get("issue_type", "合规建议"),
            severity=ai_issue.get("severity", "低"),
            description=ai_issue.get("description", ""),
            suggestion=ai_issue.get("suggestion", ""),
            related_law=ai_issue.get("related_law"),
            clause_reference=ai_issue.get("clause_reference"),
        )
        if issue.description and issue.description not in seen_descriptions:
            all_issues.append(issue)
            seen_descriptions.add(issue.description)

    # 合并适用法律
    ai_laws = ai_result.get("applicable_laws", [])
    applicable_laws = list(set(rule_laws + ai_laws))

    # 确定整体风险等级
    severity_order = {"高": 3, "中": 2, "低": 1}
    max_severity = max(
        (severity_order.get(issue.severity, 0) for issue in all_issues),
        default=0,
    )
    risk_level_map = {3: "高", 2: "中", 1: "低", 0: "低"}
    risk_level = risk_level_map.get(max_severity, "低")

    # 严格模式下提升风险等级
    if request.strict_mode and risk_level == "低" and all_issues:
        risk_level = "中"

    # 综合判断是否合规
    ai_is_compliant = ai_result.get("is_compliant", True)
    has_high_severity = any(issue.severity == "高" for issue in all_issues)
    is_compliant = ai_is_compliant and not has_high_severity

    return CheckComplianceResult(
        is_compliant=is_compliant,
        risk_level=risk_level,
        issues=all_issues,
        applicable_laws=applicable_laws,
        ai_analysis=ai_result.get("analysis"),
    )


@app.post("/tools/get_regulation_updates", summary="获取法规更新")
async def get_regulation_updates(request: GetRegulationUpdatesRequest) -> GetRegulationUpdatesResult:
    """
    获取法规更新通知工具

    查询近期法律法规的修订、新颁布、废止等更新信息。
    支持按法律名称、日期、类别筛选。
    """
    updates: list[RegulationUpdate] = []

    for update_data in REGULATION_UPDATES:
        # 按法律名称筛选
        if request.law_name and request.law_name not in update_data.get("law_name", ""):
            continue

        # 按日期筛选
        if request.since_date:
            try:
                update_date = datetime.strptime(update_data.get("update_date", ""), "%Y-%m-%d")
                since = datetime.strptime(request.since_date, "%Y-%m-%d")
                if update_date < since:
                    continue
            except ValueError:
                continue

        # 按类别筛选
        if request.category:
            impact_areas = update_data.get("impact_areas", [])
            if not any(request.category in area for area in impact_areas):
                if request.category not in update_data.get("law_name", ""):
                    continue

        updates.append(
            RegulationUpdate(
                law_name=update_data.get("law_name", ""),
                update_type=update_data.get("update_type", ""),
                update_date=update_data.get("update_date", ""),
                summary=update_data.get("summary", ""),
                key_changes=update_data.get("key_changes", []),
                impact_areas=update_data.get("impact_areas", []),
            )
        )

    return GetRegulationUpdatesResult(total=len(updates), updates=updates)


@app.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查接口"""
    return {
        "status": "healthy",
        "service": "compliance",
        "articles_loaded": len(LAW_ARTICLES),
        "regulation_updates": len(REGULATION_UPDATES),
    }


# ============================================================
# 应用启动事件
# ============================================================

@app.on_event("startup")
async def startup():
    """服务启动时重新加载法条数据"""
    global LAW_ARTICLES
    LAW_ARTICLES = load_law_articles()
    print(f"[合规检查MCP] 已加载 {len(LAW_ARTICLES)} 条法条数据，{len(REGULATION_UPDATES)} 条法规更新")


# ============================================================
# 直接运行入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005)
