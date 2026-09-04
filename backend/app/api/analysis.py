"""
智法通 - 数据分析路由模块

提供热点分析、引用统计、用户聚类和看板数据的API端点。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

from app.database import get_db
from app.services.analysis_service import AnalysisService
from app.utils.deps import require_permission
from app.models.user import User

router = APIRouter(prefix="/analysis", tags=["数据分析"])


# ==================== 请求/响应模型 ====================

class HotTopic(BaseModel):
    """热点话题"""
    category: str = Field(..., description="法律分类")
    count: int = Field(..., description="查询次数")
    trend: str = Field(..., description="趋势（up/down/stable）")
    sample_queries: list[str] = Field(default_factory=list, description="示例查询")


class CitationStatItem(BaseModel):
    """引用统计项"""
    document_id: int
    document_title: str
    citation_count: int
    positive_rate: float
    avg_confidence: Optional[float] = None


class UserCluster(BaseModel):
    """用户聚类"""
    cluster_id: int
    cluster_name: str
    user_count: int
    top_categories: list[str]
    avg_queries_per_user: float


class TrendDataPoint(BaseModel):
    """趋势数据点"""
    date: str
    query_count: int
    positive_feedback_rate: float
    avg_confidence: float


# ==================== API端点 ====================

@router.get("/hot-topics", summary="热点法律问题分析")
async def get_hot_topics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    top_n: int = Query(10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analysis:view")),
):
    """获取热点法律问题分析

    - 统计指定时间段内的热门法律问题分类
    - 显示查询次数和趋势
    - 提供每个分类的示例查询
    """
    analysis_service = AnalysisService(db)
    result = await analysis_service.get_hot_topics(days=days, top_n=top_n)
    return {"topics": result}


@router.get("/citations", summary="引用统计")
async def get_citation_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    top_n: int = Query(20, ge=1, le=100, description="返回数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analysis:view")),
):
    """获取法律文档引用统计

    - 统计法律文档被引用的频次
    - 计算正面反馈率
    - 按引用次数排序
    """
    analysis_service = AnalysisService(db)
    result = await analysis_service.get_citation_stats(days=days, top_n=top_n)
    return {"citations": result}


@router.get("/user-clusters", summary="用户行为聚类")
async def get_user_clusters(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analysis:view")),
):
    """获取用户行为聚类分析

    - 基于查询行为将用户分为不同群体
    - 显示每个群体的特征和规模
    - 返回 scatter_data 字段用于散点图可视化
    - 用于个性化推荐和运营决策
    """
    analysis_service = AnalysisService(db)
    result = await analysis_service.get_user_clusters(days=days)
    # 返回聚类概况数组与散点数据，供前端散点图使用
    return {
        "clusters": result.get("cluster_profiles", []),
        "scatter_data": result.get("scatter_data", []),
    }


@router.get("/trends", summary="查询趋势数据")
async def get_trend_data(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    granularity: str = Query("day", description="粒度（day/week/month）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analysis:view")),
):
    """获取查询趋势数据

    - 支持按日/周/月粒度统计
    - 显示查询量、正面反馈率、平均置信度
    - 用于数据看板展示
    """
    analysis_service = AnalysisService(db)
    result = await analysis_service.get_trend_data(
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )
    return {"trends": result}


@router.get("/overview", summary="分析概览")
async def get_analysis_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analysis:view")),
):
    """获取数据分析概览

    - 汇总关键指标
    - 用于管理后台首页展示
    """
    analysis_service = AnalysisService(db)
    result = await analysis_service.get_overview()
    return result
