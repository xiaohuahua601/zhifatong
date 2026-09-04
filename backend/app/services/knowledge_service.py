"""
智法通 - 知识库服务模块

提供法律文档管理、分块索引构建和语义搜索的业务逻辑。
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import UploadFile
from typing import Optional
import os
import time
import json

from app.models.knowledge import LegalDocument, DocumentChunk, DocumentStatus, DocumentSource
from app.utils.file_parser import FileParser
from app.rag.vector_store import ChromaVectorStore
from app.rag.embedding import EmbeddingService
from app.config import settings


class KnowledgeService:
    """知识库服务类

    封装文档上传、解析、分块、向量化和搜索的业务逻辑。
    """

    def __init__(self, db: AsyncSession):
        """初始化知识库服务

        Args:
            db: 异步数据库会话
        """
        self.db = db
        self.vector_store = ChromaVectorStore()
        self.embedding_service = EmbeddingService()

    async def get_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        doc_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> dict:
        """获取文档列表

        Args:
            page: 页码
            page_size: 每页数量
            doc_type: 文档类型筛选
            keyword: 关键词搜索

        Returns:
            包含文档列表和分页信息的字典
        """
        # 构建查询条件
        conditions = []
        if doc_type:
            conditions.append(LegalDocument.doc_type == doc_type)
        if keyword:
            conditions.append(LegalDocument.title.contains(keyword))

        # 查询总数
        count_query = select(func.count(LegalDocument.id))
        if conditions:
            count_query = count_query.where(*conditions)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 查询文档列表
        query = select(LegalDocument).order_by(LegalDocument.created_at.desc())
        if conditions:
            query = query.where(*conditions)
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        documents = result.scalars().all()

        return {
            "items": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "doc_type": doc.doc_type,
                    "source": doc.source,
                    "file_name": doc.file_name,
                    "status": doc.status,
                    "chunk_count": doc.chunk_count,
                    "indexing_progress": doc.indexing_progress,
                    "summary": doc.summary,
                    "tags": doc.tags,
                    "is_effective": doc.is_effective,
                    "created_at": doc.created_at.isoformat() if doc.created_at else "",
                }
                for doc in documents
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def upload_document(
        self,
        user_id: int,
        file: UploadFile,
        doc_type: str = "法律",
        tags: Optional[str] = None,
    ) -> dict:
        """上传法律文档

        保存文件、解析内容、分块并向量化索引。

        Args:
            user_id: 用户ID
            file: 上传的文件
            doc_type: 文档类型
            tags: 标签（逗号分隔）

        Returns:
            包含文档ID、标题、状态和提示信息的字典
        """
        # 确保上传目录存在
        upload_dir = os.path.abspath(settings.UPLOAD_DIR)
        os.makedirs(upload_dir, exist_ok=True)

        # 保存文件
        file_ext = os.path.splitext(file.filename)[1] if "." in file.filename else ""
        timestamp = int(time.time() * 1000)
        saved_filename = f"doc_{user_id}_{timestamp}{file_ext}"
        file_path = os.path.join(upload_dir, saved_filename)

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # 创建文档记录
        tags_json = json.dumps(tags.split(","), ensure_ascii=False) if tags else None
        document = LegalDocument(
            title=os.path.splitext(file.filename)[0],
            doc_type=doc_type,
            source=DocumentSource.UPLOAD,
            file_path=file_path,
            file_name=file.filename,
            file_size=len(content),
            status=DocumentStatus.PENDING,
            tags=tags_json,
            uploaded_by=user_id,
        )
        self.db.add(document)
        await self.db.flush()

        # 异步处理文档：解析、分块、向量化
        try:
            document.status = DocumentStatus.PROCESSING
            await self.db.flush()

            # 1. 解析文件内容
            parsed_content = await FileParser.parse(file_path, file_ext.lstrip("."))
            document.content = parsed_content

            # 2. 文档分块
            chunks = self._split_text(parsed_content, settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP)

            # 3. 生成embedding并存储到向量数据库
            for idx, chunk_text in enumerate(chunks):
                # 生成向量
                embedding = await self.embedding_service.embed_text(chunk_text)

                # 存入向量数据库
                vector_id = f"doc_{document.id}_chunk_{idx}"
                self.vector_store.add(
                    ids=[vector_id],
                    documents=[chunk_text],
                    embeddings=[embedding],
                    metadatas=[{
                        "document_id": document.id,
                        "chunk_index": idx,
                        "doc_type": doc_type,
                    }],
                )

                # 保存分块记录
                chunk_record = DocumentChunk(
                    document_id=document.id,
                    chunk_index=idx,
                    content=chunk_text,
                    vector_id=vector_id,
                    start_char=0,
                    end_char=len(chunk_text),
                )
                self.db.add(chunk_record)

            # 更新文档状态
            document.chunk_count = len(chunks)
            document.indexing_progress = 100
            document.status = DocumentStatus.COMPLETED
            await self.db.flush()

            return {
                "id": document.id,
                "title": document.title,
                "status": document.status,
                "message": "文档上传并索引成功",
            }

        except Exception as e:
            document.status = DocumentStatus.FAILED
            await self.db.flush()
            raise ValueError(f"文档处理失败：{str(e)}")

    async def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
    ) -> list[dict]:
        """语义搜索知识库

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            doc_type: 文档类型筛选

        Returns:
            搜索结果列表
        """
        # 生成查询向量
        query_embedding = await self.embedding_service.embed_text(query)

        # 构建过滤条件
        where_filter = None
        if doc_type:
            where_filter = {"doc_type": doc_type}

        # 向量检索
        results = self.vector_store.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
        )

        # 组装结果
        search_results = []
        if results and results.get("ids") and results["ids"][0]:
            for i, vector_id in enumerate(results["ids"][0]):
                # 从向量ID中提取文档ID和分块信息
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                document_id = metadata.get("document_id")

                # 查询文档标题
                doc = await self.db.get(LegalDocument, document_id)
                doc_title = doc.title if doc else "未知文档"

                # 查询分块记录
                chunk_result = await self.db.execute(
                    select(DocumentChunk).where(DocumentChunk.vector_id == vector_id)
                )
                chunk = chunk_result.scalar_one_or_none()

                search_results.append({
                    "chunk_id": chunk.id if chunk else 0,
                    "document_id": document_id,
                    "document_title": doc_title,
                    "content": results["documents"][0][i] if results.get("documents") else "",
                    "score": results["distances"][0][i] if results.get("distances") else 0.0,
                    "metadata": metadata,
                })

        return search_results

    async def get_stats(self) -> dict:
        """获取知识库统计信息

        Returns:
            包含各项统计指标的字典
        """
        # 文档总数
        total_docs_result = await self.db.execute(
            select(func.count(LegalDocument.id))
        )
        total_documents = total_docs_result.scalar() or 0

        # 分块总数
        total_chunks_result = await self.db.execute(
            select(func.count(DocumentChunk.id))
        )
        total_chunks = total_chunks_result.scalar() or 0

        # 文档类型分布
        type_dist_result = await self.db.execute(
            select(LegalDocument.doc_type, func.count(LegalDocument.id))
            .group_by(LegalDocument.doc_type)
        )
        doc_type_distribution = {row[0]: row[1] for row in type_dist_result.all() if row[0]}

        # 最近7天上传数量
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_result = await self.db.execute(
            select(func.count(LegalDocument.id)).where(LegalDocument.created_at >= week_ago)
        )
        recent_uploads = recent_result.scalar() or 0

        # 处理中的数量
        processing_result = await self.db.execute(
            select(func.count(LegalDocument.id)).where(
                LegalDocument.status == DocumentStatus.PROCESSING
            )
        )
        processing_count = processing_result.scalar() or 0

        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "doc_type_distribution": doc_type_distribution,
            "recent_uploads": recent_uploads,
            "processing_count": processing_count,
        }

    async def get_document_detail(self, document_id: int) -> dict:
        """获取文档详细信息

        Args:
            document_id: 文档ID

        Returns:
            文档详情字典
        """
        document = await self.db.get(LegalDocument, document_id)
        if not document:
            raise ValueError("文档不存在")

        # 查询分块列表
        chunks_result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        chunks = chunks_result.scalars().all()

        return {
            "id": document.id,
            "title": document.title,
            "doc_type": document.doc_type,
            "source": document.source,
            "file_name": document.file_name,
            "content": document.content,
            "summary": document.summary,
            "status": document.status,
            "chunk_count": document.chunk_count,
            "tags": document.tags,
            "is_effective": document.is_effective,
            "created_at": document.created_at.isoformat() if document.created_at else "",
            "chunks": [
                {
                    "id": c.id,
                    "chunk_index": c.chunk_index,
                    "content": c.content[:200] + "..." if len(c.content) > 200 else c.content,
                    "token_count": c.token_count,
                }
                for c in chunks
            ],
        }

    async def get_document_content(self, document_id: int) -> dict:
        """获取文档完整内容

        返回文档全文内容及所有分块的完整文本，用于前端文档阅读器展示。
        优先使用 LegalDocument.content 字段（解析后的全文），
        若为空则按分块顺序拼接 DocumentChunk.content 作为兜底。

        Args:
            document_id: 文档ID

        Returns:
            包含文档元数据、全文内容和分块列表的字典

        Raises:
            ValueError: 文档不存在时抛出
        """
        document = await self.db.get(LegalDocument, document_id)
        if not document:
            raise ValueError("文档不存在")

        # 查询所有分块的完整内容（按分块序号排序）
        chunks_result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        chunks = chunks_result.scalars().all()

        # 优先使用文档全文字段；若为空则拼接分块内容
        full_content = document.content or ""
        if not full_content and chunks:
            full_content = "\n".join([c.content for c in chunks])

        return {
            "id": document.id,
            "title": document.title,
            "file_name": document.file_name,
            "doc_type": document.doc_type,
            "content": full_content,
            "file_size": document.file_size,
            "chunk_count": len(chunks),
            "chunks": [
                {
                    "id": c.id,
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                    "token_count": c.token_count,
                }
                for c in chunks
            ],
        }

    async def delete_document(self, document_id: int) -> None:
        """删除文档

        同时删除向量数据库索引和文件存储。

        Args:
            document_id: 文档ID
        """
        document = await self.db.get(LegalDocument, document_id)
        if not document:
            raise ValueError("文档不存在")

        # 删除向量数据库中的索引
        chunks_result = await self.db.execute(
            select(DocumentChunk.vector_id).where(DocumentChunk.document_id == document_id)
        )
        vector_ids = [row[0] for row in chunks_result.all() if row[0]]
        if vector_ids:
            self.vector_store.delete(ids=vector_ids)

        # 删除文件
        if document.file_path and os.path.exists(document.file_path):
            os.remove(document.file_path)

        # 删除数据库记录（级联删除分块）
        await self.db.delete(document)
        await self.db.flush()

    def _split_text(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> list[str]:
        """文本分块

        将长文本按指定大小切分为多个分块，支持重叠。

        Args:
            text: 待分块的文本
            chunk_size: 分块大小（字符数）
            chunk_overlap: 重叠大小（字符数）

        Returns:
            分块文本列表
        """
        if not text:
            return []

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            # 尝试在句号、问号、感叹号处切分
            if end < len(text):
                for sep in ["。", "？", "！", ".", "?", "!", "\n"]:
                    last_sep = chunk.rfind(sep)
                    if last_sep > chunk_size // 2:
                        chunk = chunk[: last_sep + 1]
                        end = start + last_sep + 1
                        break
            chunks.append(chunk)
            start = end - chunk_overlap

        return chunks
