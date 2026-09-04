"""
智法通 - Function Calling工具定义模块

定义合同审查Agent可调用的工具函数，
供LLM通过Function Calling机制使用。
"""

from typing import Optional


# ==================== 工具定义 ====================

# 工具定义遵循OpenAI Function Calling格式

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_law_database",
            "description": "搜索法律数据库，查找与指定关键词相关的法律法规条文",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词，如'劳动合同解除'、'违约金上限'等",
                    },
                    "law_name": {
                        "type": "string",
                        "description": "法律名称，如'民法典'、'劳动合同法'等（可选）",
                    },
                },
                "required": ["keywords"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_clause_legality",
            "description": "检查合同条款是否违反法律强制性规定",
            "parameters": {
                "type": "object",
                "properties": {
                    "clause_text": {
                        "type": "string",
                        "description": "待检查的合同条款文本",
                    },
                    "contract_type": {
                        "type": "string",
                        "description": "合同类型，如'劳动合同'、'租赁合同'等",
                    },
                },
                "required": ["clause_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_standard_clause",
            "description": "获取指定类型合同的标准条款模板，用于对比和参考",
            "parameters": {
                "type": "object",
                "properties": {
                    "contract_type": {
                        "type": "string",
                        "description": "合同类型，如'劳动合同'、'租赁合同'、'买卖合同'等",
                    },
                    "clause_type": {
                        "type": "string",
                        "description": "条款类型，如'违约责任'、'保密条款'、'争议解决'等",
                    },
                },
                "required": ["contract_type", "clause_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_damages",
            "description": "根据合同条款和法律规定计算违约金或赔偿金额",
            "parameters": {
                "type": "object",
                "properties": {
                    "contract_amount": {
                        "type": "number",
                        "description": "合同金额",
                    },
                    "breach_type": {
                        "type": "string",
                        "description": "违约类型，如'逾期付款'、'提前解约'等",
                    },
                    "penalty_rate": {
                        "type": "number",
                        "description": "违约金比例（百分比），如0.05表示5%",
                    },
                },
                "required": ["contract_amount", "breach_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_legal_time_limit",
            "description": "查询法律规定的时效期限，如诉讼时效、仲裁时效等",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_type": {
                        "type": "string",
                        "description": "案件类型，如'合同纠纷'、'劳动争议'、'侵权'等",
                    },
                    "law_name": {
                        "type": "string",
                        "description": "法律名称（可选）",
                    },
                },
                "required": ["case_type"],
            },
        },
    },
]


# ==================== 工具执行函数 ====================

async def search_law_database(keywords: str, law_name: Optional[str] = None) -> str:
    """搜索法律数据库

    在实际应用中，这里会调用RAG检索或外部法律数据库API。
    当前为模拟实现，返回提示信息。

    Args:
        keywords: 搜索关键词
        law_name: 法律名称（可选）

    Returns:
        搜索结果文本
    """
    # TODO: 接入实际的法律数据库检索
    return f"已搜索关键词'{keywords}'相关的法律条文（功能待接入实际数据库）"


async def check_clause_legality(clause_text: str, contract_type: Optional[str] = None) -> str:
    """检查条款合法性

    Args:
        clause_text: 条款文本
        contract_type: 合同类型

    Returns:
        合法性检查结果
    """
    # TODO: 接入实际的法律合规检查逻辑
    return f"已检查条款合法性（功能待完善）"


async def get_standard_clause(contract_type: str, clause_type: str) -> str:
    """获取标准条款模板

    Args:
        contract_type: 合同类型
        clause_type: 条款类型

    Returns:
        标准条款文本
    """
    # TODO: 接入标准条款模板库
    return f"已获取{contract_type}的{clause_type}标准条款（功能待完善）"


async def calculate_damages(
    contract_amount: float,
    breach_type: str,
    penalty_rate: Optional[float] = None,
) -> str:
    """计算违约金

    Args:
        contract_amount: 合同金额
        breach_type: 违约类型
        penalty_rate: 违约金比例

    Returns:
        计算结果
    """
    if penalty_rate:
        damages = contract_amount * penalty_rate
        return f"违约金计算：{contract_amount} × {penalty_rate*100}% = {damages}"
    return f"请提供违约金比例以计算具体金额"


async def get_legal_time_limit(case_type: str, law_name: Optional[str] = None) -> str:
    """查询法律时效期限

    Args:
        case_type: 案件类型
        law_name: 法律名称

    Returns:
        时效期限信息
    """
    # 常见时效期限
    time_limits = {
        "合同纠纷": "诉讼时效为3年（民法典第188条）",
        "劳动争议": "仲裁时效为1年（劳动争议调解仲裁法第27条）",
        "侵权": "诉讼时效为3年（民法典第188条）",
    }
    return time_limits.get(case_type, f"请查询具体法律规定的时效期限")


# 工具名称到执行函数的映射
TOOL_FUNCTIONS = {
    "search_law_database": search_law_database,
    "check_clause_legality": check_clause_legality,
    "get_standard_clause": get_standard_clause,
    "calculate_damages": calculate_damages,
    "get_legal_time_limit": get_legal_time_limit,
}
