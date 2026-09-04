"""
法律法规检索MCP服务器

提供法律法规和司法解释的智能检索功能，支持：
- 按法条编号检索
- 按关键词语义匹配检索
- 按效力级别筛选
- 使用本地Ollama qwen2.5:1.5b模型进行语义增强匹配
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

# 数据文件路径（当前文件同级的data目录下）
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LAW_ARTICLES_FILE = os.path.join(DATA_DIR, "law_articles.json")

# 创建FastAPI应用实例
app = FastAPI(
    title="法律法规检索MCP服务器",
    description="提供法律法规和司法解释的智能检索服务",
    version="1.0.0",
)


# ============================================================
# 数据模型定义
# ============================================================

class SearchArticlesRequest(BaseModel):
    """搜索法条请求模型"""
    model_config = {"populate_by_name": True}

    query: str = Field(..., description="搜索关键词或法条编号")
    law_name: Optional[str] = Field(None, description="法律名称筛选，如'民法典'、'劳动合同法'")
    effect_level: Optional[str] = Field(None, description="效力级别筛选，如'法律'、'行政法规'", alias="效力_level")
    max_results: int = Field(10, description="最大返回结果数", ge=1, le=50)


class SearchInterpretationsRequest(BaseModel):
    """搜索司法解释请求模型"""
    query: str = Field(..., description="搜索关键词")
    keyword: Optional[str] = Field(None, description="额外关键词筛选")
    max_results: int = Field(10, description="最大返回结果数", ge=1, le=50)


class ArticleResult(BaseModel):
    """单条法条结果"""
    法条编号: str
    法律名称: str
    编章: str
    条款内容: str
    效力级别: str
    是否有效: bool
    生效日期: Optional[str] = None
    关键词: list[str] = []
    relevance_score: float = Field(0.0, description="相关度评分，0-1之间")


class SearchResult(BaseModel):
    """搜索结果模型"""
    total: int = Field(..., description="匹配结果总数")
    articles: list[ArticleResult] = Field(..., description="法条列表")


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


# 全局加载法条数据（服务启动时加载一次）
LAW_ARTICLES: list[dict[str, Any]] = load_law_articles()


# ============================================================
# Ollama语义匹配辅助函数
# ============================================================

async def get_semantic_score(query: str, article_content: str) -> float:
    """
    使用Ollama本地模型计算查询与法条内容的语义相关度

    Args:
        query: 用户查询文本
        article_content: 法条内容文本

    Returns:
        语义相关度评分（0.0-1.0）
    """
    prompt = (
        f"请评估以下查询与法条内容的相关程度，只返回0到1之间的数字，"
        f"1表示完全相关，0表示完全不相关。不要返回任何其他文字。\n\n"
        f"查询：{query}\n\n法条内容：{article_content}\n\n相关度评分："
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
                # 尝试从返回文本中提取数字
                try:
                    # 提取第一个浮点数
                    score = float("".join(c for c in result_text if c.isdigit() or c == "."))
                    return max(0.0, min(1.0, score))
                except ValueError:
                    return 0.0
            return 0.0
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        # Ollama服务不可用时返回0分，不影响关键词匹配
        return 0.0


# ============================================================
# 关键词匹配辅助函数
# ============================================================

def keyword_match_score(query: str, article: dict[str, Any]) -> float:
    """
    基于关键词的匹配评分（不依赖LLM，作为基础匹配方式）

    匹配策略：
    1. 法条编号精确匹配 → 最高分
    2. 法律名称匹配 → 高分
    3. 关键词匹配 → 中等分
    4. 条款内容包含查询词 → 基础分

    Args:
        query: 搜索查询
        article: 法条数据字典

    Returns:
        匹配评分（0.0-1.0）
    """
    score = 0.0
    query_lower = query.lower().strip()

    # 1. 法条编号精确匹配（最高优先级）
    法条编号 = article.get("法条编号", "")
    if query_lower in 法条编号.lower():
        score = max(score, 1.0)
    # 法条编号中包含查询关键词
    elif any(word in 法条编号.lower() for word in query_lower.split() if len(word) > 1):
        score = max(score, 0.9)

    # 2. 法律名称匹配
    法律名称 = article.get("法律名称", "").lower()
    if query_lower in 法律名称:
        score = max(score, 0.85)
    elif any(word in 法律名称 for word in query_lower.split() if len(word) > 1):
        score = max(score, 0.75)

    # 3. 关键词匹配
    关键词列表 = article.get("关键词", [])
    关键词匹配数 = sum(
        1 for kw in 关键词列表
        if query_lower in kw.lower() or kw.lower() in query_lower
    )
    if 关键词列表 and 关键词匹配数 > 0:
        关键词得分 = 0.5 + 0.3 * (关键词匹配数 / len(关键词列表))
        score = max(score, 关键词得分)

    # 4. 条款内容包含查询词
    条款内容 = article.get("条款内容", "").lower()
    query_words = [w for w in query_lower.split() if len(w) > 1]
    if query_words:
        内容匹配数 = sum(1 for word in query_words if word in 条款内容)
        if 内容匹配数 > 0:
            内容得分 = 0.2 + 0.3 * (内容匹配数 / len(query_words))
            score = max(score, 内容得分)

    return score


# ============================================================
# MCP工具定义（OpenAI Function Calling格式）
# ============================================================

SEARCH_ARTICLES_TOOL = {
    "type": "function",
    "function": {
        "name": "search_articles",
        "description": "搜索中国法律法规法条。支持按法条编号、关键词、法律名称、效力级别检索，并使用AI语义匹配提升结果相关性。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或法条编号，如'劳动合同法第47条'、'违约金'、'经济补偿'"
                },
                "law_name": {
                    "type": "string",
                    "description": "法律名称筛选，如'民法典'、'劳动合同法'、'公司法'"
                },
                "效力_level": {
                    "type": "string",
                    "description": "效力级别筛选，如'法律'、'行政法规'"
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

SEARCH_INTERPRETATIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "search_interpretations",
        "description": "搜索司法解释。根据关键词检索相关司法解释条文，支持语义匹配。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，如'民间借贷利率'、'劳动争议'、'合同解除'"
                },
                "keyword": {
                    "type": "string",
                    "description": "额外关键词筛选，用于缩小搜索范围"
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

# 工具列表，供管理器注册使用
TOOLS = [SEARCH_ARTICLES_TOOL, SEARCH_INTERPRETATIONS_TOOL]


# ============================================================
# API路由
# ============================================================

@app.get("/tools", summary="获取工具列表")
async def get_tools():
    """返回当前MCP服务器提供的所有工具定义（OpenAI Function Calling格式）"""
    return {"tools": TOOLS}


@app.post("/tools/search_articles", summary="搜索法条")
async def search_articles(request: SearchArticlesRequest) -> SearchResult:
    """
    搜索法条工具

    支持按法条编号、关键词、法律名称、效力级别检索。
    先进行关键词匹配，再通过Ollama语义匹配增强排序。
    """
    if not LAW_ARTICLES:
        raise HTTPException(status_code=500, detail="法条数据未加载，请检查数据文件")

    results: list[ArticleResult] = []

    # 第一步：关键词匹配筛选候选结果
    candidates: list[tuple[float, dict]] = []
    for article in LAW_ARTICLES:
        # 按法律名称筛选
        if request.law_name and request.law_name not in article.get("法律名称", ""):
            continue
        # 按效力级别筛选
        if request.effect_level and request.effect_level != article.get("效力级别", ""):
            continue

        score = keyword_match_score(request.query, article)
        if score > 0:
            candidates.append((score, article))

    # 按关键词匹配分数排序，取前max_results*2作为语义增强候选
    candidates.sort(key=lambda x: x[0], reverse=True)
    top_candidates = candidates[: request.max_results * 2]

    # 第二步：对排名靠前的候选结果使用Ollama语义匹配增强评分
    for base_score, article in top_candidates:
        semantic_score = await get_semantic_score(request.query, article.get("条款内容", ""))
        # 综合评分：关键词匹配权重60%，语义匹配权重40%
        final_score = base_score * 0.6 + semantic_score * 0.4

        results.append(
            ArticleResult(
                法条编号=article.get("法条编号", ""),
                法律名称=article.get("法律名称", ""),
                编章=article.get("编章", ""),
                条款内容=article.get("条款内容", ""),
                效力级别=article.get("效力级别", ""),
                是否有效=article.get("是否有效", True),
                生效日期=article.get("生效日期"),
                关键词=article.get("关键词", []),
                relevance_score=round(final_score, 4),
            )
        )

    # 按综合评分排序
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    # 截取指定数量
    results = results[: request.max_results]

    return SearchResult(total=len(results), articles=results)


@app.post("/tools/search_interpretations", summary="搜索司法解释")
async def search_interpretations(request: SearchInterpretationsRequest) -> SearchResult:
    """
    搜索司法解释工具

    基于法条数据中与司法解释相关的内容进行检索，
    并通过Ollama语义匹配增强结果相关性。
    """
    if not LAW_ARTICLES:
        raise HTTPException(status_code=500, detail="法条数据未加载，请检查数据文件")

    results: list[ArticleResult] = []
    # 司法解释检索：在法条数据中搜索与查询相关的条款
    # 实际项目中应加载专门的司法解释数据集
    combined_query = request.query
    if request.keyword:
        combined_query = f"{request.query} {request.keyword}"

    candidates: list[tuple[float, dict]] = []
    for article in LAW_ARTICLES:
        score = keyword_match_score(combined_query, article)
        if score > 0:
            candidates.append((score, article))

    candidates.sort(key=lambda x: x[0], reverse=True)
    top_candidates = candidates[: request.max_results * 2]

    for base_score, article in top_candidates:
        semantic_score = await get_semantic_score(combined_query, article.get("条款内容", ""))
        final_score = base_score * 0.6 + semantic_score * 0.4

        results.append(
            ArticleResult(
                法条编号=article.get("法条编号", ""),
                法律名称=article.get("法律名称", ""),
                编章=article.get("编章", ""),
                条款内容=article.get("条款内容", ""),
                效力级别=article.get("效力级别", ""),
                是否有效=article.get("是否有效", True),
                生效日期=article.get("生效日期"),
                关键词=article.get("关键词", []),
                relevance_score=round(final_score, 4),
            )
        )

    results.sort(key=lambda x: x.relevance_score, reverse=True)
    results = results[: request.max_results]

    return SearchResult(total=len(results), articles=results)


@app.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查接口"""
    return {
        "status": "healthy",
        "service": "law_search",
        "articles_loaded": len(LAW_ARTICLES),
    }


# ============================================================
# 应用启动事件
# ============================================================

@app.on_event("startup")
async def startup():
    """服务启动时重新加载法条数据"""
    global LAW_ARTICLES
    LAW_ARTICLES = load_law_articles()
    print(f"[法律法规检索MCP] 已加载 {len(LAW_ARTICLES)} 条法条数据")


# ============================================================
# 直接运行入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
