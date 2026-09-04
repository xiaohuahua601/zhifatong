"""
智法通 - 子查询分解器模块

将复杂的法律查询分解为多个简单的子查询，
分别检索后合并结果，提高复杂问题的回答质量。
"""

import httpx
import json
from typing import List
from app.config import settings


class SubQueryDecomposer:
    """子查询分解器类

    使用LLM将复杂查询分解为多个子查询，
    每个子查询可以独立检索，最后合并结果。
    """

    def __init__(self):
        """初始化子查询分解器"""
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    async def decompose(self, query: str) -> list[str]:
        """分解复杂查询

        判断查询是否需要分解，如果需要则生成子查询列表。

        Args:
            query: 原始查询

        Returns:
            子查询列表（简单查询返回原始查询本身）
        """
        # 先判断是否需要分解
        if not await self._needs_decomposition(query):
            return [query]

        # 生成子查询
        sub_queries = await self._generate_sub_queries(query)
        return sub_queries if sub_queries else [query]

    async def _needs_decomposition(self, query: str) -> bool:
        """判断查询是否需要分解

        复杂查询通常包含多个法律问题或多个法律领域。

        Args:
            query: 查询文本

        Returns:
            是否需要分解
        """
        prompt = f"""判断以下法律查询是否包含多个独立的法律问题，需要分解为子查询。
只回答"是"或"否"。

查询：{query}

是否需要分解："""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 10,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                answer = data.get("response", "否").strip()
                return "是" in answer

        except Exception:
            return False

    async def _generate_sub_queries(self, query: str) -> list[str]:
        """生成子查询

        Args:
            query: 原始查询

        Returns:
            子查询列表
        """
        prompt = f"""请将以下复杂的法律查询分解为多个简单的子查询。
每个子查询应该只关注一个法律问题。

原始查询：{query}

请以JSON数组格式返回子查询列表，例如：["子查询1", "子查询2", "子查询3"]
只返回JSON数组，不要其他内容："""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 500,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                result_text = data.get("response", "[]").strip()

                # 尝试解析JSON
                try:
                    sub_queries = json.loads(result_text)
                    if isinstance(sub_queries, list) and len(sub_queries) > 0:
                        return [q for q in sub_queries if isinstance(q, str) and len(q) > 0]
                except json.JSONDecodeError:
                    pass

                return [query]

        except Exception:
            return [query]
