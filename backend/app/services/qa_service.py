"""
智法通 - 问答服务模块

提供法律问答核心业务逻辑，包括调用RAG管线、管理对话上下文、
流式回答生成和反馈处理。
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from datetime import datetime
from typing import AsyncGenerator, Optional
import json
import time
import logging

from app.models.qa import Conversation, Message, QAFeedback, MessageRole, ConversationStatus
from app.models.user import User
from app.rag.pipeline import RAGPipeline
from app.config import settings
from app.utils.security import sanitize_html_content

logger = logging.getLogger(__name__)


# ==================== XSS防护：HTML内容 sanitize ====================
# 统一委托至 app.utils.security.sanitize_html_content，避免多处实现不一致。
# 历史上本文件曾内联一份 sanitize_answer 实现，与 app/api/qa.py 的
# _sanitize_ai_answer 存在行为差异（事件处理器正则覆盖范围不同），
# 现统一为单一来源，降低维护成本与遗漏风险。


def sanitize_answer(text: str) -> str:
    """对AI回答进行XSS防护处理（委托至统一工具函数）

    保留本函数以维持向后兼容（pipeline.py 等模块已 import sanitize_answer）。
    实际净化逻辑由 app.utils.security.sanitize_html_content 提供，
    覆盖：<script>转义、事件处理器移除（含无引号形式）、危险标签转义、
    javascript:协议移除。

    Args:
        text: 待处理的AI回答文本

    Returns:
        经过安全处理后的文本
    """
    return sanitize_html_content(text)


class QAService:
    """法律问答服务类

    封装问答相关的业务逻辑，协调RAG管线和数据库操作。
    """

    def __init__(self, db: AsyncSession):
        """初始化问答服务

        Args:
            db: 异步数据库会话
        """
        self.db = db
        self.rag_pipeline = RAGPipeline()

    async def ask(
        self,
        user_id: int,
        question: str,
        conversation_id: Optional[int] = None,
    ) -> dict:
        """法律提问（非流式）

        调用RAG管线生成回答，保存对话和消息记录。

        Args:
            user_id: 用户ID
            question: 法律问题
            conversation_id: 对话ID（为空则创建新对话）

        Returns:
            包含对话ID、消息ID、回答、引用和置信度的字典
        """
        start_time = time.time()

        # 获取或创建对话
        conversation = await self._get_or_create_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            question=question,
        )

        # 保存用户消息
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=question,
        )
        self.db.add(user_message)
        await self.db.flush()

        # 获取对话历史上下文
        history = await self._get_conversation_history(conversation.id)

        # 调用RAG管线生成回答
        rag_result = await self.rag_pipeline.query(
            question=question,
            history=history,
        )

        # 计算耗时
        latency_ms = int((time.time() - start_time) * 1000)

        # 对AI回答进行XSS防护处理
        safe_answer = sanitize_answer(rag_result.get("answer", ""))

        # 法律合规：在AI回答末尾追加免责声明（满足《生成式AI服务管理暂行办法》要求）
        safe_answer = self._append_legal_disclaimer(safe_answer)

        # 保存AI回答消息
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=safe_answer,
            citations=json.dumps(rag_result.get("citations", []), ensure_ascii=False),
            confidence=rag_result.get("confidence"),
            latency_ms=latency_ms,
            token_count=rag_result.get("token_count"),
        )
        self.db.add(assistant_message)

        # 更新对话消息计数
        conversation.message_count += 2  # 用户消息 + AI回答
        await self.db.flush()

        return {
            "conversation_id": conversation.id,
            "message_id": assistant_message.id,
            "answer": safe_answer,
            "citations": rag_result.get("citations", []),
            "confidence": rag_result.get("confidence"),
        }

    async def ask_stream(
        self,
        user_id: int,
        question: str,
        conversation_id: Optional[int] = None,
    ) -> AsyncGenerator[dict, None]:
        """法律提问（流式）

        使用SSE实时推送AI回答的每个分块。

        Args:
            user_id: 用户ID
            question: 法律问题
            conversation_id: 对话ID

        Yields:
            每个分块的字典数据
        """
        start_time = time.time()

        # 获取或创建对话
        conversation = await self._get_or_create_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            question=question,
        )

        # 保存用户消息
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=question,
        )
        self.db.add(user_message)
        await self.db.flush()

        # 获取对话历史
        history = await self._get_conversation_history(conversation.id)

        # 流式调用RAG管线
        # 安全修复：对每个content chunk在yield前进行XSS净化，防止恶意内容实时到达前端
        full_answer = ""
        async for chunk in self.rag_pipeline.query_stream(
            question=question,
            history=history,
        ):
            if chunk.get("type") == "content":
                raw_content = chunk.get("content", "")
                # 对每个分块进行XSS净化后再发送给客户端
                safe_content = sanitize_answer(raw_content)
                full_answer += safe_content
                chunk["content"] = safe_content
            yield chunk

        # 保存完整的AI回答（进行XSS防护处理）
        latency_ms = int((time.time() - start_time) * 1000)
        safe_full_answer = sanitize_answer(full_answer)

        # 法律合规：在流式回答末尾发送免责声明
        disclaimer = self._get_legal_disclaimer()
        yield {"type": "content", "content": disclaimer}
        safe_full_answer = safe_full_answer + disclaimer

        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=safe_full_answer,
            latency_ms=latency_ms,
        )
        self.db.add(assistant_message)
        conversation.message_count += 2
        await self.db.flush()

    async def get_conversations(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取用户的对话列表

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量

        Returns:
            包含对话列表和分页信息的字典
        """
        # 查询总数
        count_result = await self.db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.user_id == user_id,
                Conversation.status != ConversationStatus.DELETED,
            )
        )
        total = count_result.scalar() or 0

        # 查询对话列表
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.status != ConversationStatus.DELETED,
            )
            .order_by(Conversation.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        conversations = result.scalars().all()

        return {
            "items": [
                {
                    "id": c.id,
                    "title": c.title,
                    "message_count": c.message_count,
                    "status": c.status,
                    "created_at": c.created_at.isoformat() if c.created_at else "",
                    "updated_at": c.updated_at.isoformat() if c.updated_at else "",
                }
                for c in conversations
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_messages(
        self,
        user_id: int,
        conversation_id: int,
    ) -> dict:
        """获取对话的所有消息

        Args:
            user_id: 用户ID
            conversation_id: 对话ID

        Returns:
            包含消息列表的字典
        """
        # 验证对话属于当前用户（使用 select() 替代 db.get() 避免 identity map 问题）
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation or conversation.user_id != user_id:
            raise ValueError("对话不存在或无权访问")

        # 查询消息列表
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()

        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    # 安全修复：对用户消息内容也进行XSS净化，防止存储型XSS
                    "content": sanitize_answer(m.content) if m.content else "",
                    "citations": m.citations,
                    "confidence": m.confidence,
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                }
                for m in messages
            ],
        }

    async def submit_feedback(
        self,
        user_id: int,
        message_id: int,
        is_positive: bool,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> dict:
        """提交问答反馈

        Args:
            user_id: 用户ID
            message_id: 消息ID
            is_positive: 是否正面评价
            rating: 评分（1-5）
            comment: 反馈内容

        Returns:
            包含反馈ID和消息ID的字典
        """
        # 验证消息存在并校验归属权（防止越权访问他人消息）
        # 使用 select() 替代 db.get() 避免 identity map 缓存问题
        msg_result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = msg_result.scalar_one_or_none()
        if not message:
            raise ValueError("消息不存在")

        # 安全校验：验证该消息所属对话是否属于当前用户，防止水平越权
        conv_result = await self.db.execute(
            select(Conversation).where(Conversation.id == message.conversation_id)
        )
        conversation = conv_result.scalar_one_or_none()
        if not conversation or conversation.user_id != user_id:
            raise ValueError("消息不存在或无权访问")

        # 创建或更新反馈（按 message_id + user_id 组合查询，确保用户只能修改自己的反馈）
        existing = await self.db.execute(
            select(QAFeedback).where(
                QAFeedback.message_id == message_id,
                QAFeedback.user_id == user_id,
            )
        )
        feedback = existing.scalar_one_or_none()

        if feedback:
            # 更新已有反馈
            feedback.is_positive = is_positive
            feedback.rating = rating
            feedback.comment = comment
        else:
            # 创建新反馈
            feedback = QAFeedback(
                message_id=message_id,
                user_id=user_id,
                is_positive=is_positive,
                rating=rating,
                comment=comment,
            )
            self.db.add(feedback)

        await self.db.flush()

        return {
            "id": feedback.id,
            "message_id": message_id,
            "is_positive": is_positive,
        }

    async def delete_conversation(
        self,
        user_id: int,
        conversation_id: int,
    ) -> None:
        """删除对话（软删除）

        Args:
            user_id: 用户ID
            conversation_id: 对话ID
        """
        # 使用 select() 替代 db.get() 避免 identity map 缓存问题
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation or conversation.user_id != user_id:
            raise ValueError("对话不存在或无权访问")

        conversation.status = ConversationStatus.DELETED
        await self.db.flush()

    async def rename_conversation(
        self,
        user_id: int,
        conversation_id: int,
        title: str,
    ) -> dict:
        """重命名对话标题

        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            title: 新标题

        Returns:
            包含对话ID和新标题的字典
        """
        # 校验标题非空且长度合法
        title = title.strip()
        if not title:
            raise ValueError("对话标题不能为空")
        if len(title) > 200:
            raise ValueError("对话标题不能超过200个字符")

        # 使用 select() 替代 db.get() 避免 identity map 缓存问题
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation or conversation.user_id != user_id:
            raise ValueError("对话不存在或无权访问")

        conversation.title = title
        await self.db.flush()

        return {
            "id": conversation.id,
            "title": conversation.title,
        }

    # ==================== 私有方法 ====================

    async def _get_or_create_conversation(
        self,
        user_id: int,
        conversation_id: Optional[int],
        question: str,
    ) -> Conversation:
        """获取已有对话或创建新对话

        使用 select() 查询替代 db.get()，避免 identity map 缓存导致的查找失败。
        db.get() 会先查 identity map，若对象被 expunge_all() 分离后可能出现
        查找异常；select() 直接走 SQL 查询，行为更可预测。

        Args:
            user_id: 当前用户ID
            conversation_id: 对话ID（为空则创建新对话）
            question: 用户问题（用于生成新对话标题）

        Returns:
            Conversation 对象

        Raises:
            ValueError: 对话不存在或不属于当前用户
        """
        if conversation_id:
            # 使用 select() 替代 db.get()，直接走 SQL 查询
            # 避免 identity map 被 expunge_all() 清空后的潜在缓存问题
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if not conversation or conversation.user_id != user_id:
                raise ValueError("对话不存在或无权访问")
            return conversation

        # 创建新对话，使用问题前20字作为标题
        title = question[:20] + "..." if len(question) > 20 else question
        conversation = Conversation(
            user_id=user_id,
            title=title,
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def _get_conversation_history(self, conversation_id: int) -> list[dict]:
        """获取对话历史，用于RAG管线上下文"""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(10)  # 最近10条消息作为上下文
        )
        messages = result.scalars().all()

        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    # ==================== 法律合规免责声明 ====================

    # 法律免责声明常量（满足《生成式AI服务管理暂行办法》第十二条规定）
    LEGAL_DISCLAIMER = (
        "\n\n---\n"
        "> ⚠️ **法律免责声明**：本回答由AI生成，仅供普法参考，不构成律师正式法律意见。"
        "重大法律事项建议咨询执业律师。回答中引用的法律法规请以官方最新发布文本为准。"
    )

    def _get_legal_disclaimer(self) -> str:
        """获取法律免责声明文本

        Returns:
            免责声明字符串
        """
        return self.LEGAL_DISCLAIMER

    def _append_legal_disclaimer(self, answer: str) -> str:
        """在AI回答末尾追加法律免责声明

        如果回答中尚未包含免责声明，则追加；
        避免重复追加（流式回答已在末尾发送过的情况）。

        Args:
            answer: AI回答文本

        Returns:
            追加免责声明后的完整回答
        """
        if not answer:
            return answer
        # 检查是否已包含免责声明关键词，避免重复追加
        if "法律免责声明" in answer or "不构成律师正式法律意见" in answer:
            return answer
        return answer + self.LEGAL_DISCLAIMER
