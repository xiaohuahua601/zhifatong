"""
合同工具MCP服务器

提供合同模板获取和条款合法性验证功能，支持：
- 获取5种常见合同类型模板（买卖、租赁、劳动合同、服务合同、保密协议）
- 使用Ollama qwen2.5:1.5b进行条款法律合规检查
- 合同必备条款清单查询
"""

import json
import os
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
CONTRACT_TEMPLATES_FILE = os.path.join(DATA_DIR, "contract_templates.json")

# 创建FastAPI应用实例
app = FastAPI(
    title="合同工具MCP服务器",
    description="提供合同模板获取和条款合法性验证服务",
    version="1.0.0",
)


# ============================================================
# 数据模型定义
# ============================================================

class GetTemplateRequest(BaseModel):
    """获取合同模板请求模型"""
    contract_type: str = Field(
        ...,
        description="合同类型编码：sale(买卖)、lease(租赁)、employment(劳动)、service(服务)、nda(保密协议)",
    )


class ValidateClauseRequest(BaseModel):
    """验证条款合法性请求模型"""
    clause_text: str = Field(..., description="待验证的合同条款文本")
    contract_type: Optional[str] = Field(
        None,
        description="合同类型编码，用于上下文关联验证",
    )
    check_items: Optional[list[str]] = Field(
        None,
        description="指定检查项，如'合法性'、'公平性'、'可执行性'，默认全部检查",
    )


class TemplateResult(BaseModel):
    """合同模板结果模型"""
    类型编码: str
    类型名称: str
    描述: str
    必备条款清单: list[str] = []
    模板文本: str


class ClauseValidationIssue(BaseModel):
    """条款验证问题"""
    issue_type: str = Field(..., description="问题类型：合法性/公平性/可执行性/完整性")
    severity: str = Field(..., description="严重程度：高/中/低")
    description: str = Field(..., description="问题描述")
    suggestion: str = Field(..., description="修改建议")
    related_law: Optional[str] = Field(None, description="相关法律条文")


class ValidateClauseResult(BaseModel):
    """条款验证结果模型"""
    is_valid: bool = Field(..., description="条款是否合法合规")
    risk_level: str = Field(..., description="整体风险等级：低/中/高")
    issues: list[ClauseValidationIssue] = Field(default_factory=list, description="发现的问题列表")
    ai_analysis: Optional[str] = Field(None, description="AI综合分析")


# ============================================================
# 数据加载
# ============================================================

def load_contract_templates() -> list[dict[str, Any]]:
    """从JSON文件加载合同模板数据"""
    try:
        with open(CONTRACT_TEMPLATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("合同模板数据", [])
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


# 全局加载合同模板数据
CONTRACT_TEMPLATES: list[dict[str, Any]] = load_contract_templates()

# 合同类型编码到名称的映射
CONTRACT_TYPE_MAP: dict[str, str] = {
    "sale": "买卖合同",
    "lease": "租赁合同",
    "employment": "劳动合同",
    "service": "服务合同",
    "nda": "保密协议",
}


# ============================================================
# Ollama条款验证辅助函数
# ============================================================

async def validate_clause_with_ollama(
    clause_text: str,
    contract_type: Optional[str] = None,
    check_items: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    使用Ollama本地模型验证合同条款的合法性

    Args:
        clause_text: 待验证的条款文本
        contract_type: 合同类型（可选）
        check_items: 指定检查项（可选）

    Returns:
        验证结果字典，包含是否合法、风险等级、问题列表等
    """
    # 构建检查项描述
    items_desc = "、".join(check_items) if check_items else "合法性、公平性、可执行性、完整性"
    contract_context = f"（合同类型：{CONTRACT_TYPE_MAP.get(contract_type, '通用')}）" if contract_type else ""

    prompt = (
        f"请对以下合同条款进行法律合规检查{contract_context}，检查项包括：{items_desc}。\n\n"
        f"条款内容：{clause_text}\n\n"
        f"请按以下JSON格式返回结果（不要返回其他内容）：\n"
        f'{{"is_valid": true/false, "risk_level": "低/中/高", '
        f'"issues": [{{"issue_type": "问题类型", "severity": "高/中/低", '
        f'"description": "问题描述", "suggestion": "修改建议", "related_law": "相关法条"}}], '
        f'"analysis": "综合分析"}}'
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 800},
                },
            )
            if response.status_code == 200:
                result_text = response.json().get("response", "").strip()
                # 尝试从返回文本中提取JSON
                try:
                    # 查找JSON部分
                    json_start = result_text.find("{")
                    json_end = result_text.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = result_text[json_start:json_end]
                        return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                # JSON解析失败时返回基础结果
                return {
                    "is_valid": True,
                    "risk_level": "低",
                    "issues": [],
                    "analysis": result_text if result_text else "AI验证服务返回格式异常，建议人工复核",
                }
            return {
                "is_valid": True,
                "risk_level": "低",
                "issues": [],
                "analysis": "AI验证服务暂时不可用，建议人工复核",
            }
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        return {
            "is_valid": True,
            "risk_level": "低",
            "issues": [],
            "analysis": "AI验证服务暂时不可用，建议人工复核",
        }


# ============================================================
# 基于规则的条款预检查
# ============================================================

def rule_based_check(clause_text: str, contract_type: Optional[str] = None) -> list[ClauseValidationIssue]:
    """
    基于规则的条款合法性预检查（不依赖LLM）

    检查常见的违法条款模式，如：
    - 排除劳动者权利的条款
    - 违反强制性规定的条款
    - 不合理的免责条款
    - 超出法定标准的违约金

    Args:
        clause_text: 待验证的条款文本
        contract_type: 合同类型

    Returns:
        发现的问题列表
    """
    issues: list[ClauseValidationIssue] = []

    # 劳动合同特殊检查
    if contract_type == "employment":
        # 检查是否排除劳动者权利
        exclusion_patterns = [
            ("不承担", "用人单位免除法定责任的条款可能无效", "劳动合同法第26条"),
            ("自愿放弃", "劳动者自愿放弃法定权利的条款可能无效", "劳动合同法第26条"),
            ("不缴纳社保", "不缴纳社会保险的约定违反强制性规定", "劳动法第72条"),
            ("不支付加班费", "不支付加班费的约定违反强制性规定", "劳动法第44条"),
            ("试用期超过", "试用期超过法定上限的约定无效", "劳动合同法第19条"),
        ]
        for pattern, desc, law in exclusion_patterns:
            if pattern in clause_text:
                issues.append(
                    ClauseValidationIssue(
                        issue_type="合法性",
                        severity="高",
                        description=desc,
                        suggestion=f"建议删除或修改该条款，{law}可能认定该条款无效",
                        related_law=law,
                    )
                )

    # 通用检查：不合理的免责条款
    unreasonable_exemption = [
        ("概不负责", "单方免责条款可能被认定为无效格式条款", "民法典第497条"),
        ("最终解释权", "最终解释权条款属于无效格式条款", "民法典第497条"),
        ("一律不退", "一律不退的条款可能被认定为无效格式条款", "民法典第497条"),
    ]
    for pattern, desc, law in unreasonable_exemption:
        if pattern in clause_text:
            issues.append(
                ClauseValidationIssue(
                    issue_type="公平性",
                    severity="中",
                    description=desc,
                    suggestion=f"建议修改为合理条件，避免被认定为无效格式条款",
                    related_law=law,
                )
            )

    # 通用检查：违约金过高
    if "违约金" in clause_text:
        high_penalty_patterns = ["50%", "100%", "双倍", "三倍", "全部"]
        for pattern in high_penalty_patterns:
            if pattern in clause_text:
                issues.append(
                    ClauseValidationIssue(
                        issue_type="可执行性",
                        severity="中",
                        description="违约金约定可能过高，法院有权予以调整",
                        suggestion="建议将违约金约定在合理范围内（通常不超过实际损失的30%）",
                        related_law="民法典第585条",
                    )
                )
                break

    return issues


# ============================================================
# MCP工具定义（OpenAI Function Calling格式）
# ============================================================

GET_TEMPLATE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_template",
        "description": "获取合同模板。支持买卖合同、租赁合同、劳动合同、服务合同、保密协议五种类型。",
        "parameters": {
            "type": "object",
            "properties": {
                "contract_type": {
                    "type": "string",
                    "description": "合同类型编码：sale(买卖合同)、lease(租赁合同)、employment(劳动合同)、service(服务合同)、nda(保密协议)",
                    "enum": ["sale", "lease", "employment", "service", "nda"]
                }
            },
            "required": ["contract_type"]
        }
    }
}

VALIDATE_CLAUSE_TOOL = {
    "type": "function",
    "function": {
        "name": "validate_clause",
        "description": "验证合同条款的合法性。使用AI和规则引擎双重检查，评估条款的合法性、公平性、可执行性和完整性。",
        "parameters": {
            "type": "object",
            "properties": {
                "clause_text": {
                    "type": "string",
                    "description": "待验证的合同条款文本"
                },
                "contract_type": {
                    "type": "string",
                    "description": "合同类型编码，用于上下文关联验证",
                    "enum": ["sale", "lease", "employment", "service", "nda"]
                },
                "check_items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "指定检查项，如'合法性'、'公平性'、'可执行性'，默认全部检查"
                }
            },
            "required": ["clause_text"]
        }
    }
}

# 工具列表
TOOLS = [GET_TEMPLATE_TOOL, VALIDATE_CLAUSE_TOOL]


# ============================================================
# API路由
# ============================================================

@app.get("/tools", summary="获取工具列表")
async def get_tools():
    """返回当前MCP服务器提供的所有工具定义"""
    return {"tools": TOOLS}


@app.post("/tools/get_template", summary="获取合同模板")
async def get_template(request: GetTemplateRequest) -> TemplateResult:
    """
    获取合同模板工具

    根据合同类型编码返回对应的合同模板，包括必备条款清单和模板文本。
    """
    if not CONTRACT_TEMPLATES:
        raise HTTPException(status_code=500, detail="合同模板数据未加载，请检查数据文件")

    # 查找匹配的合同模板
    for template in CONTRACT_TEMPLATES:
        if template.get("类型编码") == request.contract_type:
            return TemplateResult(
                类型编码=template.get("类型编码", ""),
                类型名称=template.get("类型名称", ""),
                描述=template.get("描述", ""),
                必备条款清单=template.get("必备条款清单", []),
                模板文本=template.get("模板文本", ""),
            )

    # 未找到模板
    available_types = [t.get("类型编码", "") for t in CONTRACT_TEMPLATES]
    raise HTTPException(
        status_code=404,
        detail=f"未找到类型为'{request.contract_type}'的合同模板，可用类型：{available_types}",
    )


@app.post("/tools/validate_clause", summary="验证条款合法性")
async def validate_clause(request: ValidateClauseRequest) -> ValidateClauseResult:
    """
    验证条款合法性工具

    使用规则引擎预检查 + Ollama AI验证双重机制：
    1. 先通过规则引擎进行快速预检查（检查常见违法模式）
    2. 再通过Ollama进行深度语义验证
    3. 合并结果并给出综合评估
    """
    # 第一步：基于规则的预检查
    rule_issues = rule_based_check(request.clause_text, request.contract_type)

    # 第二步：使用Ollama进行AI验证
    ai_result = await validate_clause_with_ollama(
        request.clause_text,
        request.contract_type,
        request.check_items,
    )

    # 第三步：合并结果
    all_issues: list[ClauseValidationIssue] = []

    # 添加规则引擎发现的问题（去重）
    rule_descriptions = set()
    for issue in rule_issues:
        if issue.description not in rule_descriptions:
            all_issues.append(issue)
            rule_descriptions.add(issue.description)

    # 添加AI发现的问题
    ai_issues = ai_result.get("issues", [])
    for ai_issue in ai_issues:
        issue = ClauseValidationIssue(
            issue_type=ai_issue.get("issue_type", "合法性"),
            severity=ai_issue.get("severity", "低"),
            description=ai_issue.get("description", ""),
            suggestion=ai_issue.get("suggestion", ""),
            related_law=ai_issue.get("related_law"),
        )
        if issue.description and issue.description not in rule_descriptions:
            all_issues.append(issue)
            rule_descriptions.add(issue.description)

    # 确定整体风险等级
    severity_order = {"高": 3, "中": 2, "低": 1}
    max_severity = max(
        (severity_order.get(issue.severity, 0) for issue in all_issues),
        default=0,
    )
    risk_level_map = {3: "高", 2: "中", 1: "低", 0: "低"}
    risk_level = risk_level_map.get(max_severity, "低")

    # 综合AI和规则的判断确定是否合法
    ai_is_valid = ai_result.get("is_valid", True)
    has_high_severity = any(issue.severity == "高" for issue in all_issues)
    is_valid = ai_is_valid and not has_high_severity

    return ValidateClauseResult(
        is_valid=is_valid,
        risk_level=risk_level,
        issues=all_issues,
        ai_analysis=ai_result.get("analysis"),
    )


@app.get("/templates/list", summary="列出所有合同模板类型")
async def list_templates():
    """列出所有可用的合同模板类型"""
    if not CONTRACT_TEMPLATES:
        return {"templates": []}

    templates = [
        {
            "类型编码": t.get("类型编码", ""),
            "类型名称": t.get("类型名称", ""),
            "描述": t.get("描述", ""),
            "必备条款数量": len(t.get("必备条款清单", [])),
        }
        for t in CONTRACT_TEMPLATES
    ]
    return {"templates": templates}


@app.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查接口"""
    return {
        "status": "healthy",
        "service": "contract_tools",
        "templates_loaded": len(CONTRACT_TEMPLATES),
    }


# ============================================================
# 应用启动事件
# ============================================================

@app.on_event("startup")
async def startup():
    """服务启动时重新加载合同模板数据"""
    global CONTRACT_TEMPLATES
    CONTRACT_TEMPLATES = load_contract_templates()
    print(f"[合同工具MCP] 已加载 {len(CONTRACT_TEMPLATES)} 个合同模板")


# ============================================================
# 直接运行入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
