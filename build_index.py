"""
智法通 - ChromaDB索引构建脚本

将MySQL中的法律文档分块索引到ChromaDB向量数据库，
使RAG检索和知识库搜索功能正常工作。
"""
import asyncio
import sys
import os

# 添加backend目录到路径
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.database import async_session_factory
from app.models.knowledge import LegalDocument, DocumentChunk
from app.rag.vector_store import ChromaVectorStore
from app.rag.embedding import EmbeddingService
from sqlalchemy import select


async def build_index():
    """构建ChromaDB索引"""
    async with async_session_factory() as db:
        print("=" * 60)
        print("  智法通 - ChromaDB索引构建")
        print("=" * 60)

        # 查询所有已完成的文档
        result = await db.execute(
            select(LegalDocument).where(LegalDocument.content.isnot(None))
        )
        documents = result.scalars().all()
        print(f"\n📄 找到 {len(documents)} 个文档需要索引")

        # 初始化服务
        vector_store = ChromaVectorStore()
        embedding_service = EmbeddingService()

        # 先清空现有索引
        try:
            vector_store.reset()
            print("🗑️ 已清空旧索引")
        except Exception as e:
            print(f"⚠️ 清空索引跳过: {e}")

        total_chunks = 0
        for doc in documents:
            print(f"\n📝 索引文档: {doc.title} (ID: {doc.id})")

            # 查询该文档的分块
            chunk_result = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == doc.id)
                .order_by(DocumentChunk.chunk_index)
            )
            chunks = chunk_result.scalars().all()

            if not chunks:
                # 如果没有分块，按固定大小切分
                content = doc.content or ""
                chunk_size = 500
                chunk_texts = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            else:
                chunk_texts = [c.content for c in chunks]

            # 生成embedding并存储到ChromaDB
            ids = []
            embeddings = []
            documents_text = []
            metadatas = []

            for idx, chunk_text in enumerate(chunk_texts):
                if not chunk_text.strip():
                    continue

                # 生成embedding
                embedding = await embedding_service.embed_text(chunk_text)

                vector_id = f"doc_{doc.id}_chunk_{idx}"
                ids.append(vector_id)
                embeddings.append(embedding)
                documents_text.append(chunk_text)
                metadatas.append({
                    "document_id": doc.id,
                    "chunk_index": idx,
                    "doc_type": doc.doc_type or "法律",
                    "title": doc.title,
                    "law_name": doc.title,
                    "effectiveness": "有效",
                })

            if ids:
                vector_store.add(
                    ids=ids,
                    documents=documents_text,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
                total_chunks += len(ids)
                print(f"  ✅ 索引 {len(ids)} 个分块")

        print(f"\n{'=' * 60}")
        print(f"  ✅ 索引构建完成! 共索引 {total_chunks} 个分块")
        print(f"  ChromaDB集合: {vector_store.collection_name}")
        print(f"  文档总数: {vector_store.count()}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(build_index())
