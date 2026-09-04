"""
案例检索MCP服务器

提供典型裁判文书的智能检索功能，支持：
- 按案由检索相似案例
- 按法院层级筛选
- 按裁判结果筛选
- 获取案例详情
- 使用本地Ollama qwen2.5:1.5b模型进行语义匹配
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
CASES_FILE = os.path.join(DATA_DIR, "cases.json")

# 创建FastAPI应用实例
app = FastAPI(
    title="案例检索MCP服务器",
    description="提供典型裁判文书的智能检索服务",
    version="1.0.0",
)


# ============================================================
# 数据模型定义
# ============================================================

class SearchCasesRequest(BaseModel):
    """检索相似案例请求模型"""
    query: str = Field(..., description="搜索关键词或案由")
    case_type: Optional[str] = Field(None, description="案由筛选，如'劳动争议'、'买卖合同纠纷'")
    court_level: Optional[str] = Field(None, description="法院层级筛选，如'基层人民法院'、'中级人民法院'、'高级人民法院'")
    judgment_result: Optional[str] = Field(None, description="裁判结果关键词筛选")
    max_results: int = Field(10, description="最大返回结果数", ge=1, le=50)


class GetCaseDetailRequest(BaseModel):
    """获取案例详情请求模型"""
    case_id: str = Field(..., description="案号，如'(2023)京01民终1234号'")


class CaseResult(BaseModel):
    """案例结果模型"""
    案号: str
    案由: str
    法院: str
    法院层级: str
    裁判日期: Optional[str] = None
    裁判结果: str
    核心要点: str
    争议焦点: Optional[str] = None
    适用法条: list[str] = []
    关键词: list[str] = []
    relevance_score: float = Field(0.0, description="相关度评分，0-1之间")


class CaseSearchResult(BaseModel):
    """案例搜索结果模型"""
    total: int = Field(..., description="匹配结果总数")
    cases: list[CaseResult] = Field(..., description="案例列表")


class CaseDetailResult(BaseModel):
    """案例详情结果模型"""
    found: bool = Field(..., description="是否找到案例")
    case: Optional[CaseResult] = None
    ai_analysis: Optional[str] = Field(None, description="AI生成的案例分析")


# ============================================================
# 数据加载
# ============================================================

def load_cases() -> list[dict[str, Any]]:
    """从JSON文件加载案例数据"""
    try:
        with open(CASES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("案例数据", [])
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


# 全局加载案例数据
CASES_DATA: list[dict[str, Any]] = load_cases()


# ============================================================
# Ollama语义匹配辅助函数
# ============================================================

async def get_semantic_score(query: str, case_content: str) -> float:
    """
    使用Ollama本地模型计算查询与案例内容的语义相关度

    Args:
        query: 用户查询文本
        case_content: 案例内容文本

    Returns:
        语义相关度评分（0.0-1.0）
    """
    prompt = (
        f"请评估以下查询与案例内容的相关程度，只返回0到1之间的数字，"
        f"1表示完全相关，0表示完全不相关。不要返回任何其他文字。\n\n"
        f"查询：{query}\n\n案例内容：{case_content}\n\n相关度评分："
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 10},
                },
            )
            if response.status_code == 200:
                result_text = response.json().get("response", "0").strip()
                try:
                    score = float("".join(c for c in result_text if c.isdigit() or c == "."))
                    return max(0.0, min(1.0, score))
                except ValueError:
                    return 0.0
            return 0.0
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        return 0.0


async def generate_case_analysis(case: dict[str, Any]) -> str:
    """
    使用Ollama生成案例分析

    Args:
        case: 案例数据字典

    Returns:
        AI生成的案例分析文本
    """
    case_summary = (
        f"案号：{case.get('案号', '')}\n"
        f"案由：{case.get('案由', '')}\n"
        f"核心要点：{case.get('核心要点', '')}\n"
        f"裁判结果：{case.get('裁判结果', '')}\n"
        f"适用法条：{', '.join(case.get('适用法条', []))}"
    )
    prompt = (
        f"请对以下案例进行简要分析，包括法律适用要点和实务建议，200字以内：\n\n"
        f"{case_summary}\n\n分析："
    )
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 300},
                },
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            return "AI分析服务暂时不可用"
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        return "AI分析服务暂时不可用"


# ============================================================
# 关键词匹配辅助函数
# ============================================================

def case_keyword_match_score(query: str, case: dict[str, Any]) -> float:
    """
    基于关键词的案例匹配评分

    匹配策略：
    1. 案号精确匹配 → 最高分
    2. 案由匹配 → 高分
    3. 关键词匹配 → 中等分
    4. 核心要点/争议焦点包含查询词 → 基础分

    Args:
        query: 搜索查询
        case: 案例数据字典

    Returns:
        匹配评分（0.0-1.0）
    """
    score = 0.0
    query_lower = query.lower().strip()

    # 1. 案号精确匹配
    案号 = case.get("案号", "").lower()
    if query_lower in 案号:
        score = max(score, 1.0)

    # 2. 案由匹配
    案由 = case.get("案由", "").lower()
    if query_lower in 案由 or 案由 in query_lower:
        score = max(score, 0.9)
    elif any(word in 案由 for word in query_lower.split() if len(word) > 1):
        score = max(score, 0.75)

    # 3. 关键词匹配
    关键词列表 = case.get("关键词", [])
    关键词匹配数 = sum(
        1 for kw in 关键词列表
        if query_lower in kw.lower() or kw.lower() in query_lower
    )
    if 关键词列表 and 关键词匹配数 > 0:
        关键词得分 = 0.5 + 0.3 * (关键词匹配数 / len(关键词列表))
        score = max(score, 关键词得分)

    # 4. 核心要点/争议焦点包含查询词
    for field in ["核心要点", "争议焦点", "裁判结果"]:
        content = case.get(field, "").lower()
        query_words = [w for w in query_lower.split() if len(w) > 1]
        if query_words:
            匹配数 = sum(1 for word in query_words if word in content)
            if 匹配数 > 0:
                内容得分 = 0.2 + 0.3 * (匹配数 / len(query_words))
                score = max(score, 内容得分)

    return score


# ============================================================
# MCP工具定义（OpenAI Function Calling格式）
# ============================================================

SEARCH_CASES_TOOL = {
    "type": "function",
    "function": {
        "name": "search_cases",
        "description": "检索相似案例。支持按案由、法院层级、裁判结果筛选，并使用AI语义匹配提升结果相关性。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或案由，如'劳动争议'、'买卖合同纠纷'、'股权转让'"
                },
                "case_type": {
                    "type": "string",
                    "description": "案由筛选，如'劳动争议'、'买卖合同纠纷'、'租赁合同纠纷'"
                },
                "court_level": {
                    "type": "string",
                    "description": "法院层级筛选，如'基层人民法院'、'中级人民法院'、'高级人民法院'"
                },
                "judgment_result": {
                    "type": "string",
                    "description": "裁判结果关键词筛选，如'驳回'、'支持'、'撤销'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数，默认10",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    }
}

GET_CASE_DETAIL_TOOL = {
    "type": "function",
    "function": {
        "name": "get_case_detail",
        "description": "获取案例详情。根据案号获取案例的完整信息，包括AI生成的案例分析。",
        "parameters": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "案号，如'(2023)京01民终1234号'"
                }
            },
            "required": ["case_id"]
        }
    }
}

# 工具列表
TOOLS = [SEARCH_CASES_TOOL, GET_CASE_DETAIL_TOOL]


# ============================================================
# API路由
# ============================================================

@app.get("/tools", summary="获取工具列表")
async def get_tools():
    """返回当前MCP服务器提供的所有工具定义"""
    return {"tools": TOOLS}


@app.post("/tools/search_cases", summary="检索相似案例")
async def search_cases(request: SearchCasesRequest) -> CaseSearchResult:
    """
    检索相似案例工具

    支持按案由、法院层级、裁判结果筛选，
    先进行关键词匹配，再通过Ollama语义匹配增强排序。
    """
    if not CASES_DATA:
        raise HTTPException(status_code=500, detail="案例数据未加载，请检查数据文件")

    results: list[CaseResult] = []

    # 第一步：关键词匹配筛选候选结果
    candidates: list[tuple[float, dict]] = []
    for case in CASES_DATA:
        # 按案由筛选
        if request.case_type and request.case_type not in case.get("案由", ""):
            continue
        # 按法院层级筛选
        if request.court_level and request.court_level != case.get("法院层级", ""):
            continue
        # 按裁判结果筛选
        if request.judgment_result and request.judgment_result not in case.get("裁判结果", ""):
            continue

        score = case_keyword_match_score(request.query, case)
        if score > 0:
            candidates.append((score, case))

    # 按关键词匹配分数排序
    candidates.sort(key=lambda x: x[0], reverse=True)
    top_candidates = candidates[: request.max_results * 2]

    # 第二步：对排名靠前的候选结果使用Ollama语义匹配增强评分
    for base_score, case in top_candidates:
        # 将案例核心信息组合为语义匹配内容
        case_content = (
            f"{case.get('案由', '')} {case.get('核心要点', '')} "
            f"{case.get('争议焦点', '')} {case.get('裁判结果', '')}"
        )
        semantic_score = await get_semantic_score(request.query, case_content)
        # 综合评分：关键词匹配权重60%，语义匹配权重40%
        final_score = base_score * 0.6 + semantic_score * 0.4

        results.append(
            CaseResult(
                案号=case.get("案号", ""),
                案由=case.get("案由", ""),
                法院=case.get("法院", ""),
                法院层级=case.get("法院层级", ""),
                裁判日期=case.get("裁判日期"),
                裁判结果=case.get("裁判结果", ""),
                核心要点=case.get("核心要点", ""),
                争议焦点=case.get("争议焦点"),
                适用法条=case.get("适用法条", []),
                关键词=case.get("关键词", []),
                relevance_score=round(final_score, 4),
            )
        )

    # 按综合评分排序
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    results = results[: request.max_results]

    return CaseSearchResult(total=len(results), cases=results)


@app.post("/tools/get_case_detail", summary="获取案例详情")
async def get_case_detail(request: GetCaseDetailRequest) -> CaseDetailResult:
    """
    获取案例详情工具

    根据案号获取案例完整信息，并使用Ollama生成AI案例分析。
    """
    if not CASES_DATA:
        raise HTTPException(status_code=500, detail="案例数据未加载，请检查数据文件")

    # 在案例数据中查找匹配的案号
    matched_case = None
    for case in CASES_DATA:
        if case.get("案号") == request.case_id:
            matched_case = case
            break

    if not matched_case:
        return CaseDetailResult(found=False, case=None, ai_analysis=None)

    # 使用Ollama生成AI案例分析
    ai_analysis = await generate_case_analysis(matched_case)

    case_result = CaseResult(
        案号=matched_case.get("案号", ""),
        案由=matched_case.get("案由", ""),
        法院=matched_case.get("法院", ""),
        法院层级=matched_case.get("法院层级", ""),
        裁判日期=matched_case.get("裁判日期"),
        裁判结果=matched_case.get("裁判结果", ""),
        核心要点=matched_case.get("核心要点", ""),
        争议焦点=matched_case.get("争议焦点"),
        适用法条=matched_case.get("适用法条", []),
        关键词=matched_case.get("关键词", []),
        relevance_score=1.0,
    )

    return CaseDetailResult(found=True, case=case_result, ai_analysis=ai_analysis)


@app.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查接口"""
    return {
        "status": "healthy",
        "service": "case_search",
        "cases_loaded": len(CASES_DATA),
    }


# ============================================================
# 应用启动事件
# ============================================================

@app.on_event("startup")
async def startup():
    """服务启动时重新加载案例数据"""
    global CASES_DATA
    CASES_DATA = load_cases()
    print(f"[案例检索MCP] 已加载 {len(CASES_DATA)} 个案例数据")


# ============================================================
# 直接运行入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
