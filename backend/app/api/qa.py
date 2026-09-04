"""
智法通 - 法律问答路由模块

提供法律问答相关的API端点，包括提问、流式回答、对话历史和反馈。
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
import json

from app.database import get_db
from app.services.qa_service import QAService
from app.services.quota_service import QuotaService
from app.utils.deps import get_current_user
from app.utils.security import sanitize_html_content
from app.models.user import User

router = APIRouter(prefix="/qa", tags=["法律问答"])


# ==================== XSS 净化工具 ====================
# 统一委托至 app.utils.security.sanitize_html_content，避免与 qa_service.py
# 的 sanitize_answer 存在两套不一致实现。此处保留包装函数以维持本文件内
# 调用点的可读性，实际净化逻辑由统一工具函数提供（defense-in-depth）。


def _sanitize_ai_answer(answer: str) -> str:
    """净化AI回答中的危险HTML内容（委托至统一工具函数）

    覆盖：<script>转义、事件处理器移除（含无引号形式）、
    <iframe>/<object>/<embed>/<svg>危险标签转义、javascript:协议移除。
    前端已使用DOMPurify做二次净化，此处为后端兜底。

    Args:
        answer: AI原始回答文本

    Returns:
        净化后的安全文本
    """
    return sanitize_html_content(answer)


# ==================== 请求/响应模型 ====================

class AskRequest(BaseModel):
    """提问请求"""
    question: str = Field(..., min_length=1, max_length=2000, description="法律问题")
    conversation_id: Optional[int] = Field(None, description="对话ID（为空则创建新对话）")
    stream: bool = Field(default=False, description="是否使用流式回答")


class AskResponse(BaseModel):
    """提问响应"""
    conversation_id: int = Field(..., description="对话ID")
    message_id: int = Field(..., description="消息ID")
    answer: str = Field(..., description="AI回答")
    citations: list = Field(default_factory=list, description="引用来源")
    confidence: Optional[float] = Field(None, description="置信度")


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    title: Optional[str] = None
    message_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    role: str
    content: str
    citations: Optional[str] = None
    confidence: Optional[float] = None
    created_at: str = ""

    class Config:
        from_attributes = True


class FeedbackRequest(BaseModel):
    """反馈请求"""
    message_id: int = Field(..., description="消息ID")
    is_positive: bool = Field(..., description="是否正面评价")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分（1-5）")
    comment: Optional[str] = Field(None, max_length=1000, description="反馈内容")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    id: int
    message_id: int
    is_positive: bool


# ==================== API端点 ====================

@router.post("/ask", response_model=AskResponse, summary="法律提问")
async def ask_question(
    request: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """法律提问接口

    - 支持多轮对话（传入conversation_id继续对话）
    - 返回AI回答和引用来源
    - 如需流式回答，请使用 /qa/ask/stream 端点
    - 普通用户每日限制50次提问，超额返回429
    """
    # 额度检查：校验用户今日剩余问答次数
    quota_service = QuotaService(db)
    allowed, remaining, limit = await quota_service.check_and_consume(
        user_id=current_user.id, resource_type="qa"
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日咨询次数已用完（限制{limit}次/日），请明日再试",
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Limit": str(limit)},
        )

    qa_service = QAService(db)
    result = await qa_service.ask(
        user_id=current_user.id,
        question=request.question,
        conversation_id=request.conversation_id,
    )
    # XSS防御性净化：中和AI回答中可能包含的危险HTML标签
    if "answer" in result and result["answer"]:
        result["answer"] = _sanitize_ai_answer(result["answer"])
    return AskResponse(**result)


@router.post("/ask/stream", summary="流式法律提问")
async def ask_question_stream(
    request: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """流式法律提问接口

    - 使用Server-Sent Events (SSE)实时推送AI回答
    - 适合长回答场景，用户无需等待完整生成
    - 返回text/event-stream格式
    - 普通用户每日限制50次提问，超额返回429
    """
    # 额度检查：校验用户今日剩余问答次数
    quota_service = QuotaService(db)
    allowed, remaining, limit = await quota_service.check_and_consume(
        user_id=current_user.id, resource_type="qa"
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日咨询次数已用完（限制{limit}次/日），请明日再试",
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Limit": str(limit)},
        )

    qa_service = QAService(db)

    async def event_generator():
        """SSE事件生成器"""
        async for chunk in qa_service.ask_stream(
            user_id=current_user.id,
            question=request.question,
            conversation_id=request.conversation_id,
        ):
            # XSS防御性净化：中和分块中可能包含的危险HTML标签
            if isinstance(chunk, dict) and chunk.get("content"):
                chunk["content"] = _sanitize_ai_answer(chunk["content"])
            # 将每个分块编码为SSE格式
            data = json.dumps(chunk, ensure_ascii=False)
            yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Limit": str(limit),
        },
    )


@router.get("/conversations", summary="获取对话列表")
async def get_conversations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的对话列表

    - 按更新时间倒序排列
    - 支持分页
    """
    qa_service = QAService(db)
    result = await qa_service.get_conversations(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/conversations/{conversation_id}/messages", summary="获取对话消息")
async def get_conversation_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定对话的所有消息

    - 按时间顺序排列
    - 包含用户提问和AI回答
    """
    qa_service = QAService(db)
    result = await qa_service.get_messages(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )
    return result


@router.post("/feedback", response_model=FeedbackResponse, summary="提交问答反馈")
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交对AI回答的反馈

    - 支持正面/负面评价
    - 支持评分和文字反馈
    - 用于持续优化回答质量
    """
    qa_service = QAService(db)
    result = await qa_service.submit_feedback(
        user_id=current_user.id,
        message_id=request.message_id,
        is_positive=request.is_positive,
        rating=request.rating,
        comment=request.comment,
    )
    return FeedbackResponse(**result)


@router.delete("/conversations/{conversation_id}", summary="删除对话")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除指定对话

    - 软删除，标记为已删除状态
    - 只能删除自己的对话
    """
    qa_service = QAService(db)
    await qa_service.delete_conversation(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )
    return {"message": "对话已删除"}


class RenameRequest(BaseModel):
    """重命名对话请求"""
    title: str = Field(..., min_length=1, max_length=200, description="新对话标题")


@router.patch("/conversations/{conversation_id}", summary="重命名对话")
async def rename_conversation(
    conversation_id: int,
    request: RenameRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重命名指定对话标题

    - 只能修改自己的对话标题
    - 标题长度1-200字符
    """
    qa_service = QAService(db)
    result = await qa_service.rename_conversation(
        user_id=current_user.id,
        conversation_id=conversation_id,
        title=request.title,
    )
    return result


@router.get("/suggestions", summary="获取推荐问题")
async def get_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取推荐问题

    - 优先返回 query_logs 中高频查询问题
    - 数据不足时回退到默认推荐问题
    - 用于问答页面欢迎界面展示
    """
    from sqlalchemy import select, func
    from app.models.analysis import QueryLog

    # 默认推荐问题（兜底）
    default_suggestions = [
        "劳动合同解除后，经济补偿金如何计算？",
        "房屋租赁合同中承租人的权利有哪些？",
        "什么是格式条款？哪些格式条款无效？",
        "买卖合同中标的物风险何时转移？",
    ]

    # 尝试从查询日志中提取高频问题
    try:
        result = await db.execute(
            select(QueryLog.query_text, func.count(QueryLog.id).label("cnt"))
            .where(QueryLog.query_text.isnot(None))
            .group_by(QueryLog.query_text)
            .order_by(func.count(QueryLog.id).desc())
            .limit(4)
        )
        hot_questions = [row[0] for row in result.all() if row[0]]
        if len(hot_questions) >= 2:
            return {"suggestions": hot_questions}
    except Exception:
        pass

    return {"suggestions": default_suggestions}


# ==================== 额度查询端点 ====================

@router.get("/quota", summary="查询今日剩余咨询次数")
async def get_qa_quota(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询当前用户今日法律问答剩余额度

    - 普通用户每日限制50次提问
    - 管理员不限额度（返回 limit=-1）
    - 返回已用次数、剩余次数和每日限额
    """
    quota_service = QuotaService(db)
    used, remaining, limit = await quota_service.get_quota(
        user_id=current_user.id, resource_type="qa"
    )
    return {
        "resource_type": "qa",
        "used": used,
        "remaining": remaining,
        "limit": limit,
        "reset_at": "次日00:00",
    }
