"""
智法通 - 仪表盘路由模块

提供仪表盘概览统计、最近活动和趋势数据的API端点。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

from app.database import get_db
from app.config import settings
from app.utils.deps import require_permission
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


# ==================== 请求/响应模型 ====================

class OverviewStats(BaseModel):
    """概览统计"""
    total_users: int = Field(0, description="总用户数")
    total_conversations: int = Field(0, description="总对话数")
    total_contracts: int = Field(0, description="总合同数")
    total_documents: int = Field(0, description="总文档数")
    today_queries: int = Field(0, description="今日查询数")
    today_new_users: int = Field(0, description="今日新用户")
    avg_confidence: float = Field(0.0, description="平均置信度")
    positive_feedback_rate: float = Field(0.0, description="正面反馈率")


class RecentActivity(BaseModel):
    """最近活动"""
    id: int
    type: str = Field(..., description="活动类型（query/contract/document）")
    title: str = Field(..., description="活动标题")
    description: str = Field("", description="活动描述")
    user: str = Field("", description="操作用户")
    created_at: str = Field("", description="时间")


class DashboardTrend(BaseModel):
    """仪表盘趋势数据"""
    date: str
    queries: int = 0
    contracts: int = 0
    users: int = 0


class GraphNodeData(BaseModel):
    """知识图谱节点（ECharts graph格式）"""
    id: str = Field(..., description="节点唯一标识")
    name: str = Field(..., description="节点显示名称")
    category: int = Field(..., description="节点分类索引（0法律/1法条/2案例/3概念）")
    symbolSize: float = Field(30, description="节点大小（按关联度动态计算）")
    value: str = Field("", description="节点详情（类型·关联数·描述）")
    degree: int = Field(0, description="节点关联关系数量")


class GraphLinkData(BaseModel):
    """知识图谱关系边"""
    source: str = Field(..., description="源节点ID")
    target: str = Field(..., description="目标节点ID")
    value: str = Field(..., description="关系类型（HAS_ARTICLE/REFERENCES/MENTIONS/INVOLVES）")


class KnowledgeGraphData(BaseModel):
    """知识图谱数据（Neo4j真实实体关系）"""
    nodes: list[GraphNodeData] = Field(default_factory=list, description="节点列表")
    links: list[GraphLinkData] = Field(default_factory=list, description="关系列表")
    source: str = Field("neo4j", description="数据来源（neo4j=图谱实时查询/local=内存降级）")
    total_nodes: int = Field(0, description="节点总数")
    total_links: int = Field(0, description="关系总数")


# ==================== API端点 ====================

@router.get("/overview", response_model=OverviewStats, summary="概览统计")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analysis:view")),
):
    """获取仪表盘概览统计数据

    - 用户总数、对话总数、合同总数、文档总数
    - 今日查询数、今日新用户
    - 平均置信度、正面反馈率
    """
    from sqlalchemy import select, func
    from app.models.user import User
    from app.models.qa import Conversation
    from app.models.contract import Contract
    from app.models.knowledge import LegalDocument
    from app.models.analysis import QueryLog
    from datetime import datetime, timedelta

    # 总用户数
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    # 总对话数
    total_conversations_result = await db.execute(select(func.count(Conversation.id)))
    total_conversations = total_conversations_result.scalar() or 0

    # 总合同数
    total_contracts_result = await db.execute(select(func.count(Contract.id)))
    total_contracts = total_contracts_result.scalar() or 0

    # 总文档数
    total_documents_result = await db.execute(select(func.count(LegalDocument.id)))
    total_documents = total_documents_result.scalar() or 0

    # 今日查询数
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_queries_result = await db.execute(
        select(func.count(QueryLog.id)).where(QueryLog.created_at >= today_start)
    )
    today_queries = today_queries_result.scalar() or 0

    # 今日新用户
    today_new_users_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    today_new_users = today_new_users_result.scalar() or 0

    # 平均置信度
    avg_confidence_result = await db.execute(
        select(func.avg(QueryLog.confidence)).where(QueryLog.confidence.isnot(None))
    )
    avg_confidence = avg_confidence_result.scalar() or 0.0

    # 正面反馈率
    total_feedback_result = await db.execute(
        select(func.count(QueryLog.id)).where(QueryLog.feedback_score != 0)
    )
    positive_feedback_result = await db.execute(
        select(func.count(QueryLog.id)).where(QueryLog.feedback_score == 1)
    )
    total_feedback = total_feedback_result.scalar() or 0
    positive_feedback = positive_feedback_result.scalar() or 0
    positive_feedback_rate = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0.0

    return OverviewStats(
        total_users=total_users,
        total_conversations=total_conversations,
        total_contracts=total_contracts,
        total_documents=total_documents,
        today_queries=today_queries,
        today_new_users=today_new_users,
        avg_confidence=round(avg_confidence, 2),
        positive_feedback_rate=round(positive_feedback_rate, 2),
    )


@router.get("/recent-activities", summary="最近活动")
async def get_recent_activities(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analysis:view")),
):
    """获取最近的系统活动

    - 包括最新的查询、合同审查、文档上传等
    - 按时间倒序排列
    """
    from sqlalchemy import select
    from app.models.analysis import QueryLog
    from app.models.contract import Contract
    from app.models.knowledge import LegalDocument

    activities = []

    # 最近的查询
    query_result = await db.execute(
        select(QueryLog)
        .order_by(QueryLog.created_at.desc())
        .limit(limit)
    )
    for log in query_result.scalars().all():
        activities.append({
            "id": log.id,
            "type": "query",
            "title": log.query_text[:50] + "..." if len(log.query_text) > 50 else log.query_text,
            "description": f"分类：{log.category or '未分类'}，置信度：{log.confidence or 'N/A'}",
            "user": f"用户{log.user_id}",
            "created_at": log.created_at.isoformat() if log.created_at else "",
        })

    # 最近的合同
    contract_result = await db.execute(
        select(Contract)
        .order_by(Contract.created_at.desc())
        .limit(limit)
    )
    for contract in contract_result.scalars().all():
        activities.append({
            "id": contract.id,
            "type": "contract",
            "title": contract.title,
            "description": f"状态：{contract.status}，类型：{contract.contract_type or '未分类'}",
            "user": f"用户{contract.user_id}",
            "created_at": contract.created_at.isoformat() if contract.created_at else "",
        })

    # 最近的文档
    doc_result = await db.execute(
        select(LegalDocument)
        .order_by(LegalDocument.created_at.desc())
        .limit(limit)
    )
    for doc in doc_result.scalars().all():
        activities.append({
            "id": doc.id,
            "type": "document",
            "title": doc.title,
            "description": f"类型：{doc.doc_type or '未分类'}，分块数：{doc.chunk_count}",
            "user": f"用户{doc.uploaded_by}",
            "created_at": doc.created_at.isoformat() if doc.created_at else "",
        })

    # 按时间排序并截取
    activities.sort(key=lambda x: x["created_at"], reverse=True)
    return {"activities": activities[:limit]}


@router.get("/domain-distribution", summary="法律领域分布")
async def get_domain_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analysis:view")),
):
    """获取法律领域分布统计

    - 从 query_logs 表按 category 分组统计
    - 返回 [{name: "劳动法", value: 35}, ...] 格式
    - 用于仪表盘饼图展示
    """
    from sqlalchemy import select, func
    from app.models.analysis import QueryLog

    # 按 category 分组统计查询次数
    result = await db.execute(
        select(
            QueryLog.category,
            func.count(QueryLog.id).label("count"),
        )
        .where(QueryLog.category.isnot(None))
        .group_by(QueryLog.category)
        .order_by(func.count(QueryLog.id).desc())
    )

    distribution = []
    for row in result.all():
        category, count = row
        distribution.append({
            "name": category,
            "value": count,
        })

    return {"distribution": distribution}


@router.get("/trends", summary="趋势数据")
async def get_dashboard_trends(
    days: int = Query(30, ge=7, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analysis:view")),
):
    """获取仪表盘趋势数据

    - 按天统计查询量、合同数、新用户数
    - 用于折线图展示
    """
    from sqlalchemy import select, func, cast, Date
    from app.models.analysis import QueryLog
    from app.models.contract import Contract
    from app.models.user import User
    from datetime import datetime, timedelta

    trends = []
    for i in range(days - 1, -1, -1):
        target_date = (datetime.utcnow() - timedelta(days=i)).date()
        date_start = datetime.combine(target_date, datetime.min.time())
        date_end = datetime.combine(target_date, datetime.max.time())

        # 当日查询数
        query_count_result = await db.execute(
            select(func.count(QueryLog.id)).where(
                QueryLog.created_at.between(date_start, date_end)
            )
        )
        query_count = query_count_result.scalar() or 0

        # 当日合同数
        contract_count_result = await db.execute(
            select(func.count(Contract.id)).where(
                Contract.created_at.between(date_start, date_end)
            )
        )
        contract_count = contract_count_result.scalar() or 0

        # 当日新用户
        user_count_result = await db.execute(
            select(func.count(User.id)).where(
                User.created_at.between(date_start, date_end)
            )
        )
        user_count = user_count_result.scalar() or 0

        trends.append({
            "date": target_date.isoformat(),
            "queries": query_count,
            "contracts": contract_count,
            "users": user_count,
        })

    return {"trends": trends}


@router.get("/graph", response_model=KnowledgeGraphData, summary="法律知识图谱数据")
async def get_knowledge_graph(
    limit: int = Query(250, ge=20, le=500, description="最大返回节点数（按关联度取TopN）"),
    current_user: User = Depends(require_permission("analysis:view")),
):
    """获取法律知识图谱数据（Neo4j真实实体关系）

    - 节点：Law(法律) / Article(法条) / Case(案例) / Concept(概念)
    - 关系：HAS_ARTICLE（法条归属）/ REFERENCES（案例引用法条）/
            MENTIONS（法条提及概念）/ INVOLVES（案例涉及概念）
    - 节点大小按关联度动态计算
    - Neo4j不可用时自动降级为内存计算（同一份法律数据）
    """
    from app.services.graph_service import query_graph

    result = await query_graph(limit=limit)
    return KnowledgeGraphData(**result)


@router.post("/graph/build", summary="构建法律知识图谱")
async def build_knowledge_graph(
    current_user: User = Depends(require_permission("analysis:view")),
):
    """手动触发Neo4j知识图谱构建（从项目法律数据导入，MERGE幂等可重复执行）

    - 数据源：法条库（law_articles.json）+ 案例库（cases.json）
    - 构建Law/Article/Case/Concept节点及四类真实关系
    """
    from app.services.graph_service import build_graph, close_driver

    try:
        stats = await build_graph()
        return {"message": "知识图谱构建完成", "stats": stats}
    except Exception as e:
        raise ValueError(f"图谱构建失败（请检查Neo4j服务是否启动）：{e}")
    finally:
        await close_driver()
