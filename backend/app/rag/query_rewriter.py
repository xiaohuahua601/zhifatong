"""
智法通 - 查询重写器模块

将用户的口语化查询转换为专业的法律术语查询，
提高检索的准确性和召回率。

V2.0增强：
- 新增指代消解（coreference resolution）能力
- rewrite方法接受chat_history参数，支持多轮对话上下文
"""

import httpx
import json
from typing import Optional
from app.config import settings


class QueryRewriter:
    """查询重写器类

    使用LLM将用户的口语化表达转换为法律专业术语，
    同时补充隐含的法律概念。

    V2.0新增指代消解能力，能够将"那个法条""上面说的法律"
    等代词替换为对话历史中的具体内容，使多轮对话中的检索
    能够准确定位到正确的法律依据。
    """

    def __init__(self):
        """初始化查询重写器"""
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    async def rewrite(
        self,
        query: str,
        chat_history: Optional[list[dict]] = None,
    ) -> str:
        """重写查询

        将口语化的法律问题转换为专业法律术语。
        V2.0增强：接受chat_history参数，若提供则先进行指代消解，
        再进行查询重写，使多轮对话场景下的检索更准确。

        Args:
            query: 原始查询文本
            chat_history: 对话历史（可选），格式为[{"role": "user"/"assistant", "content": "..."}]
                          用于指代消解，将代词替换为具体内容

        Returns:
            重写后的查询文本
        """
        # V2.0：若提供了对话历史，先进行指代消解
        # 这样重写器能基于完整、明确的问题进行术语转换
        if chat_history:
            query = await self.resolve_coreference(query, chat_history)

        prompt = f"""你是一个法律查询重写助手。请将以下口语化的法律问题转换为更专业、更精确的法律术语查询，以便在法律知识库中检索到更相关的结果。

要求：
1. 保留原始查询的核心意图
2. 使用法律专业术语替换口语表达
3. 补充隐含的法律概念
4. 只返回重写后的查询，不要解释

原始查询：{query}

重写后的查询："""

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
                            "num_predict": 100,  # 减少token数提升速度
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                rewritten = data.get("response", query).strip()

                # 如果重写结果为空或过短，返回原始查询
                if len(rewritten) < 2:
                    return query

                return rewritten

        except Exception:
            # 重写失败时返回原始查询
            return query

    async def resolve_coreference(
        self,
        query: str,
        chat_history: list[dict],
    ) -> str:
        """指代消解

        使用LLM将当前问题中的指代词（如"那个法条""上面说的法律"
        "这个条款""他""它"等）替换为对话历史中的具体内容，
        生成一个语义完整、可独立理解的问题。

        V2.0新增方法，用于支持多轮对话场景下的准确检索。

        Args:
            query: 当前用户问题（可能包含指代词）
            chat_history: 对话历史，格式为[{"role": "user"/"assistant", "content": "..."}]

        Returns:
            消解指代后的完整问题。若chat_history为空或消解失败，
            返回原始query。
        """
        # 若对话历史为空，无需消解，直接返回原查询
        if not chat_history:
            return query

        # 将对话历史格式化为文本（取最近6轮，避免上下文过长）
        history_parts = []
        for msg in chat_history[-6:]:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            if content:
                history_parts.append(f"{role}：{content}")
        chat_history_text = "\n".join(history_parts)

        # 若格式化后的历史为空，直接返回原查询
        if not chat_history_text.strip():
            return query

        prompt = f"""请消解以下法律问题中的指代词，将代词替换为对话历史中的具体内容。

要求：
1. 将"那个法条""上面说的法律""这个条款""他""它"等代词替换为对话历史中的具体法律名称、条款或内容
2. 保持问题的核心意图不变
3. 如果当前问题中没有指代词，或对话历史中找不到对应内容，请原样返回问题
4. 只返回消解后的完整问题，不要解释

对话历史：{chat_history_text}
当前问题：{query}

消解后的完整问题："""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,  # 低温度，确保消解结果稳定
                            "num_predict": 300,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                resolved = data.get("response", query).strip()

                # 若消解结果为空或过短，返回原始查询
                if len(resolved) < 2:
                    return query

                return resolved

        except Exception:
            # 消解失败时返回原始查询，保证流程不中断
            return query

    async def expand_with_synonyms(self, query: str) -> list[str]:
        """扩展查询同义词

        生成与原始查询语义相近的多个查询变体，
        用于提高检索召回率。

        Args:
            query: 原始查询

        Returns:
            查询变体列表（包含原始查询）
        """
        prompt = f"""请为以下法律查询生成3个语义相近但表述不同的查询变体。
这些变体将用于扩大检索范围，提高召回率。

原始查询：{query}

请以JSON数组格式返回，例如：["变体1", "变体2", "变体3"]
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
                            "temperature": 0.5,
                            "num_predict": 300,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                result_text = data.get("response", "[]").strip()

                # 尝试解析JSON
                try:
                    variants = json.loads(result_text)
                    if isinstance(variants, list):
                        # 确保原始查询在列表中
                        all_queries = [query] + [v for v in variants if isinstance(v, str) and v != query]
                        return all_queries[:5]  # 最多5个变体
                except json.JSONDecodeError:
                    pass

                return [query]

        except Exception:
            return [query]
