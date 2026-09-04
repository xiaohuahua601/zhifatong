"""
智法通 - 向量存储模块

使用ChromaDB实现向量存储，支持文档的增删改查和相似度检索。
开发环境使用本地持久化存储。

维度管理：
    当切换Embedding模型时（如从nomic-embed-text 768维切换到bge-large-zh-v1.5 1024维），
    需要重建索引。本模块在初始化时自动检测维度不匹配并删除旧集合。
"""

import chromadb
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """ChromaDB向量存储类

    封装ChromaDB的增删改查操作，提供统一的向量存储接口。

    维度自动检测：
        初始化时检查已有向量的维度，如果与配置维度（CHROMA_EMBEDDING_DIM）不匹配，
        自动删除旧集合并重新创建，避免维度不一致导致的查询错误。
    """

    def __init__(self, collection_name: Optional[str] = None):
        """初始化向量存储

        Args:
            collection_name: 集合名称，默认使用配置中的名称
        """
        self.persist_dir = settings.CHROMA_PERSIST_DIR
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self.expected_dim = settings.CHROMA_EMBEDDING_DIM

        # 创建持久化客户端
        self.client = chromadb.PersistentClient(path=self.persist_dir)

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},  # 使用余弦相似度
        )

        # 维度自动检测：如果已有向量维度与配置不匹配，删除旧集合并重建
        self._check_and_rebuild_if_dim_mismatch()

    def _check_and_rebuild_if_dim_mismatch(self):
        """检查已有向量维度，不匹配时删除旧集合并重建

        场景：从768维nomic-embed-text切换到1024维bge-large-zh-v1.5时，
        旧索引的768维向量与新模型的1024维向量不兼容，查询会报维度错误。
        本方法检测这种情况并自动删除旧集合。
        """
        try:
            count = self.collection.count()
            if count == 0:
                return  # 空集合，无需检查

            # 获取一条已有数据检查维度
            sample = self.collection.get(limit=1, include=["embeddings"])
            embeddings = sample.get("embeddings", [])
            # 注意：embeddings可能是numpy数组，不能直接用 if embeddings 判断真值
            # 需要先转换为列表或显式检查长度
            embeddings_list = list(embeddings) if embeddings is not None else []
            if len(embeddings_list) > 0:
                actual_dim = len(embeddings_list[0])
                if actual_dim != self.expected_dim:
                    logger.warning(
                        f"⚠️ 检测到向量维度不匹配（旧={actual_dim}维, 新={self.expected_dim}维），"
                        f"删除旧集合并重建..."
                    )
                    self.client.delete_collection(self.collection_name)
                    self.collection = self.client.get_or_create_collection(
                        name=self.collection_name,
                        metadata={"hnsw:space": "cosine"},
                    )
                    logger.info(f"✅ 集合已重建（维度={self.expected_dim}），需重新构建索引")
                else:
                    logger.debug(f"向量维度检查通过（{actual_dim}维）")
        except Exception as e:
            logger.warning(f"维度检查异常（忽略，继续使用）: {e}")


    def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        """添加文档到向量存储

        Args:
            ids: 文档ID列表
            documents: 文档内容列表
            embeddings: 向量列表
            metadatas: 元数据列表
        """
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embeddings: list[list[float]],
        n_results: int = 5,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
    ) -> dict:
        """向量相似度查询

        Args:
            query_embeddings: 查询向量列表
            n_results: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件

        Returns:
            查询结果字典，包含ids、documents、distances、metadatas
        """
        kwargs = {
            "query_embeddings": query_embeddings,
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        if where_document:
            kwargs["where_document"] = where_document

        return self.collection.query(**kwargs)

    def delete(self, ids: list[str]) -> None:
        """根据ID删除文档

        Args:
            ids: 待删除的文档ID列表
        """
        self.collection.delete(ids=ids)

    def update(
        self,
        ids: list[str],
        documents: Optional[list[str]] = None,
        embeddings: Optional[list[list[float]]] = None,
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        """更新文档

        Args:
            ids: 文档ID列表
            documents: 新文档内容列表
            embeddings: 新向量列表
            metadatas: 新元数据列表
        """
        kwargs = {"ids": ids}
        if documents:
            kwargs["documents"] = documents
        if embeddings:
            kwargs["embeddings"] = embeddings
        if metadatas:
            kwargs["metadatas"] = metadatas

        self.collection.update(**kwargs)

    def count(self) -> int:
        """获取集合中的文档数量

        Returns:
            文档数量
        """
        return self.collection.count()

    def get(
        self,
        ids: Optional[list[str]] = None,
        where: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """获取文档

        Args:
            ids: 文档ID列表
            where: 元数据过滤条件
            limit: 返回数量限制

        Returns:
            文档数据字典
        """
        kwargs = {}
        if ids:
            kwargs["ids"] = ids
        if where:
            kwargs["where"] = where
        if limit:
            kwargs["limit"] = limit

        return self.collection.get(**kwargs)

    def reset(self) -> None:
        """重置集合（删除所有数据）

        谨慎使用，会删除集合中的所有数据。
        """
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
