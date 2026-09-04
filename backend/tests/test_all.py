"""
智法通 - 企业级智能法律顾问平台 综合测试脚本

测试范围：
1. 配置模块导入和默认值
2. 安全工具（密码哈希、JWT生成/验证）
3. 数据模型定义
4. RAG管线各组件初始化
5. MCP工具数据加载
6. API路由定义
7. Agent工作流构建
"""

import sys
import os
import traceback
from typing import List, Tuple

# 确保backend目录在sys.path中
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ============================================================
# 测试结果记录
# ============================================================

class TestResult:
    """测试结果记录器"""

    def __init__(self):
        self.passed: List[str] = []
        self.failed: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []

    def ok(self, name: str):
        self.passed.append(name)

    def fail(self, name: str, reason: str):
        self.failed.append((name, reason))

    def warn(self, name: str, reason: str):
        self.warnings.append((name, reason))

    def summary(self) -> str:
        total = len(self.passed) + len(self.failed)
        lines = [
            "",
            "=" * 60,
            "  智法通 综合测试报告",
            "=" * 60,
            f"  总计: {total}  通过: {len(self.passed)}  失败: {len(self.failed)}  警告: {len(self.warnings)}",
            "-" * 60,
        ]

        if self.passed:
            lines.append("  [通过]")
            for name in self.passed:
                lines.append(f"    OK  {name}")

        if self.warnings:
            lines.append("  [警告]")
            for name, reason in self.warnings:
                lines.append(f"    WARN  {name}: {reason}")

        if self.failed:
            lines.append("  [失败]")
            for name, reason in self.failed:
                lines.append(f"    FAIL  {name}: {reason}")

        lines.append("=" * 60)

        if self.failed:
            lines.append("  结果: 存在失败项，请检查上方详情")
        else:
            lines.append("  结果: 全部通过!")

        lines.append("")
        return "\n".join(lines)


result = TestResult()


# ============================================================
# 1. 配置模块测试
# ============================================================

def test_config():
    """测试配置模块导入和默认值"""
    print("\n[1/7] 测试配置模块...")

    try:
        from app.config import settings
        result.ok("config: 导入 Settings")

        # 检查默认值
        assert settings.APP_NAME == "智法通", f"APP_NAME 不匹配: {settings.APP_NAME}"
        result.ok("config: APP_NAME == '智法通'")

        assert settings.APP_VERSION == "1.0.0", f"APP_VERSION 不匹配: {settings.APP_VERSION}"
        result.ok("config: APP_VERSION == '1.0.0'")

        assert settings.DEBUG is True, f"DEBUG 不匹配: {settings.DEBUG}"
        result.ok("config: DEBUG == True")

        assert settings.API_PREFIX == "/api/v1", f"API_PREFIX 不匹配: {settings.API_PREFIX}"
        result.ok("config: API_PREFIX == '/api/v1'")

        # 检查数据库URL属性
        db_url = settings.DATABASE_URL
        assert "mysql+aiomysql" in db_url, f"DATABASE_URL 格式不正确: {db_url}"
        result.ok("config: DATABASE_URL 包含 mysql+aiomysql")

        # 检查Redis URL属性
        redis_url = settings.REDIS_URL
        assert "redis://" in redis_url, f"REDIS_URL 格式不正确: {redis_url}"
        result.ok("config: REDIS_URL 包含 redis://")

        # 检查JWT配置
        assert settings.JWT_ALGORITHM == "HS256", f"JWT_ALGORITHM 不匹配: {settings.JWT_ALGORITHM}"
        result.ok("config: JWT_ALGORITHM == 'HS256'")

        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 60
        result.ok("config: JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 60")

        # 检查Ollama配置
        assert settings.OLLAMA_MODEL == "qwen2.5:1.5b"
        result.ok("config: OLLAMA_MODEL == 'qwen2.5:1.5b'")

        # 检查RAG配置
        assert settings.RAG_TOP_K == 5
        result.ok("config: RAG_TOP_K == 5")

        assert settings.RAG_CHUNK_SIZE == 500
        result.ok("config: RAG_CHUNK_SIZE == 500")

        # 检查CORS配置
        assert len(settings.CORS_ORIGINS) > 0
        result.ok("config: CORS_ORIGINS 非空")

    except Exception as e:
        result.fail("config", str(e))
        traceback.print_exc()


# ============================================================
# 2. 安全工具测试
# ============================================================

def test_security():
    """测试安全工具模块"""
    print("[2/7] 测试安全工具...")

    try:
        from app.utils.security import hash_password, verify_password
        from app.utils.security import create_access_token, create_refresh_token, decode_token
        result.ok("security: 导入所有安全函数")

        # 测试密码哈希和验证
        password = "TestPass123!"
        hashed = hash_password(password)
        assert hashed != password, "哈希后密码不应与原文相同"
        result.ok("security: hash_password 返回哈希值")

        assert verify_password(password, hashed) is True, "密码验证应通过"
        result.ok("security: verify_password 正确密码验证通过")

        assert verify_password("WrongPass", hashed) is False, "错误密码验证应失败"
        result.ok("security: verify_password 错误密码验证失败")

        # 测试JWT访问令牌
        token_data = {"sub": "1", "username": "testuser"}
        access_token = create_access_token(token_data)
        assert isinstance(access_token, str) and len(access_token) > 0, "访问令牌应为非空字符串"
        result.ok("security: create_access_token 生成令牌")

        decoded = decode_token(access_token)
        assert decoded is not None, "令牌解码应成功"
        assert decoded.get("sub") == "1", f"sub 不匹配: {decoded.get('sub')}"
        assert decoded.get("type") == "access", f"type 不匹配: {decoded.get('type')}"
        result.ok("security: decode_token 正确解码访问令牌")

        # 测试JWT刷新令牌
        refresh_token = create_refresh_token(token_data)
        assert isinstance(refresh_token, str) and len(refresh_token) > 0
        result.ok("security: create_refresh_token 生成刷新令牌")

        decoded_refresh = decode_token(refresh_token)
        assert decoded_refresh is not None
        assert decoded_refresh.get("type") == "refresh", f"type 不匹配: {decoded_refresh.get('type')}"
        result.ok("security: decode_token 正确解码刷新令牌")

        # 测试无效令牌
        invalid_decoded = decode_token("invalid.token.here")
        assert invalid_decoded is None, "无效令牌解码应返回None"
        result.ok("security: decode_token 无效令牌返回None")

    except Exception as e:
        result.fail("security", str(e))
        traceback.print_exc()


# ============================================================
# 3. 数据模型测试
# ============================================================

def test_models():
    """测试数据模型定义"""
    print("[3/7] 测试数据模型...")

    try:
        # 测试数据库模块
        from app.database import Base, engine
        result.ok("models: 导入 Base 和 engine")

        # 测试用户模型
        from app.models.user import User, Role, Permission, user_role, role_permission
        result.ok("models: 导入 User, Role, Permission")

        assert hasattr(User, "__tablename__") and User.__tablename__ == "users"
        result.ok("models: User.__tablename__ == 'users'")

        assert hasattr(Role, "__tablename__") and Role.__tablename__ == "roles"
        result.ok("models: Role.__tablename__ == 'roles'")

        assert hasattr(Permission, "__tablename__") and Permission.__tablename__ == "permissions"
        result.ok("models: Permission.__tablename__ == 'permissions'")

        # 测试问答模型
        from app.models.qa import Conversation, Message, QAFeedback, MessageRole, ConversationStatus
        result.ok("models: 导入 Conversation, Message, QAFeedback")

        # 测试合同模型
        from app.models.contract import Contract, ReviewReport, RiskClause, ContractStatus, RiskLevel
        result.ok("models: 导入 Contract, ReviewReport, RiskClause")

        # 测试知识库模型
        from app.models.knowledge import LegalDocument, DocumentChunk, DocumentStatus, DocumentSource
        result.ok("models: 导入 LegalDocument, DocumentChunk")

        # 验证 DocumentChunk 的 chunk_metadata 属性（修复后的保留字冲突）
        assert hasattr(DocumentChunk, "chunk_metadata"), "DocumentChunk 应有 chunk_metadata 属性"
        result.ok("models: DocumentChunk.chunk_metadata 属性存在（metadata保留字修复）")

        # 测试分析模型
        from app.models.analysis import QueryLog, CitationStat
        result.ok("models: 导入 QueryLog, CitationStat")

        # 测试模型包统一导入
        from app.models import (
            User, Role, Permission, user_role, role_permission,
            Conversation, Message, QAFeedback, MessageRole, ConversationStatus,
            Contract, ReviewReport, RiskClause, ContractStatus, RiskLevel,
            LegalDocument, DocumentChunk, DocumentStatus, DocumentSource,
            QueryLog, CitationStat,
        )
        result.ok("models: 从 app.models 统一导入所有模型")

    except Exception as e:
        result.fail("models", str(e))
        traceback.print_exc()


# ============================================================
# 4. RAG管线组件测试
# ============================================================

def test_rag():
    """测试RAG管线各组件"""
    print("[4/7] 测试RAG管线组件...")

    try:
        # 测试Embedding服务
        from app.rag.embedding import EmbeddingService
        result.ok("rag: 导入 EmbeddingService")

        embedding_svc = EmbeddingService()
        assert embedding_svc.model == "nomic-embed-text"
        result.ok("rag: EmbeddingService 默认模型为 nomic-embed-text")

        # 测试向量存储
        from app.rag.vector_store import ChromaVectorStore
        result.ok("rag: 导入 ChromaVectorStore")

        # 测试检索器
        from app.rag.retriever import HybridRetriever
        result.ok("rag: 导入 HybridRetriever")

        # 测试查询重写器
        from app.rag.query_rewriter import QueryRewriter
        result.ok("rag: 导入 QueryRewriter")

        # 测试子查询分解器
        from app.rag.sub_query import SubQueryDecomposer
        result.ok("rag: 导入 SubQueryDecomposer")

        # 测试重排序器
        from app.rag.reranker import Reranker
        result.ok("rag: 导入 Reranker")

        # 测试自评估器
        from app.rag.self_eval import SelfEvaluator
        result.ok("rag: 导入 SelfEvaluator")

        # 测试RAG管线
        from app.rag.pipeline import RAGPipeline
        result.ok("rag: 导入 RAGPipeline")

        pipeline = RAGPipeline()
        assert hasattr(pipeline, "query_rewriter")
        assert hasattr(pipeline, "sub_query_decomposer")
        assert hasattr(pipeline, "retriever")
        assert hasattr(pipeline, "reranker")
        assert hasattr(pipeline, "self_evaluator")
        result.ok("rag: RAGPipeline 初始化包含所有子组件")

    except Exception as e:
        result.fail("rag", str(e))
        traceback.print_exc()


# ============================================================
# 5. MCP工具测试
# ============================================================

def test_mcp():
    """测试MCP工具数据加载"""
    print("[5/7] 测试MCP工具...")

    try:
        # 测试MCP管理器
        from app.mcp_servers.manager import (
            app as manager_app,
            MCP_SERVERS,
            TOOL_SERVER_MAP,
            ALL_TOOLS,
            register_tools,
            ToolCallRequest,
            ToolCallResult,
            ServerStatus,
            RegisterRequest,
        )
        result.ok("mcp: 导入 MCP管理器模块")

        assert len(MCP_SERVERS) == 5, f"MCP_SERVERS 应有5个服务器配置，实际: {len(MCP_SERVERS)}"
        result.ok("mcp: MCP_SERVERS 包含5个服务器配置")

        expected_servers = {"law_search", "case_search", "contract_tools", "calc_tools", "compliance"}
        assert set(MCP_SERVERS.keys()) == expected_servers, f"服务器列表不匹配: {set(MCP_SERVERS.keys())}"
        result.ok("mcp: MCP_SERVERS 包含所有预期服务器")

        # 测试法律法规检索MCP
        from app.mcp_servers.law_search import (
            app as law_search_app,
            TOOLS as law_search_tools,
            LAW_ARTICLES,
            load_law_articles,
            keyword_match_score,
            SearchArticlesRequest,
            SearchResult,
        )
        result.ok("mcp: 导入法律法规检索MCP")

        assert len(law_search_tools) == 2, f"法律法规检索应有2个工具，实际: {len(law_search_tools)}"
        result.ok("mcp: 法律法规检索MCP 提供2个工具")

        tool_names = [t.get("function", {}).get("name") for t in law_search_tools]
        assert "search_articles" in tool_names, f"缺少 search_articles 工具: {tool_names}"
        assert "search_interpretations" in tool_names, f"缺少 search_interpretations 工具: {tool_names}"
        result.ok("mcp: 法律法规检索MCP 工具名称正确")

        # 测试法条数据加载
        articles = load_law_articles()
        if len(articles) > 0:
            result.ok(f"mcp: 法条数据加载成功，共 {len(articles)} 条")
        else:
            result.warn("mcp: 法条数据为空（数据文件可能不存在或为空）")

        # 测试案例检索MCP
        from app.mcp_servers.case_search import (
            app as case_search_app,
            TOOLS as case_search_tools,
        )
        result.ok("mcp: 导入案例检索MCP")

        # 测试合同工具MCP
        from app.mcp_servers.contract_tools import (
            app as contract_tools_app,
            TOOLS as contract_tools_list,
        )
        result.ok("mcp: 导入合同工具MCP")

        # 测试法律计算工具MCP
        from app.mcp_servers.calc_tools import (
            app as calc_tools_app,
            TOOLS as calc_tools_list,
            LPR_ONE_YEAR,
            LPR_FIVE_YEAR,
        )
        result.ok("mcp: 导入法律计算工具MCP")

        assert LPR_ONE_YEAR > 0 and LPR_FIVE_YEAR > 0
        result.ok(f"mcp: LPR利率配置正确 (一年期: {LPR_ONE_YEAR}%, 五年期: {LPR_FIVE_YEAR}%)")

        # 测试合规检查MCP
        from app.mcp_servers.compliance import (
            app as compliance_app,
            TOOLS as compliance_tools,
        )
        result.ok("mcp: 导入合规检查MCP")

        # 测试工具注册逻辑
        test_tools = [
            {"type": "function", "function": {"name": "test_tool_1", "description": "测试工具1", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "test_tool_2", "description": "测试工具2", "parameters": {"type": "object", "properties": {}}}},
        ]
        old_count = len(ALL_TOOLS)
        register_tools("law_search", test_tools)
        assert len(ALL_TOOLS) >= old_count, "注册工具后 ALL_TOOLS 应增加"
        result.ok("mcp: register_tools 注册工具逻辑正常")

        # 验证工具名到服务器映射
        assert "test_tool_1" in TOOL_SERVER_MAP, "test_tool_1 应在 TOOL_SERVER_MAP 中"
        assert TOOL_SERVER_MAP["test_tool_1"] == "law_search"
        result.ok("mcp: TOOL_SERVER_MAP 映射正确")

    except Exception as e:
        result.fail("mcp", str(e))
        traceback.print_exc()


# ============================================================
# 6. API路由测试
# ============================================================

def test_api_routes():
    """测试API路由定义"""
    print("[6/7] 测试API路由...")

    try:
        # 测试主应用
        from app.main import app
        result.ok("api: 导入 FastAPI 主应用")

        # 检查路由注册 - 通过OpenAPI获取所有路径
        openapi_schema = app.openapi()
        paths = list(openapi_schema.get("paths", {}).keys())
        result.ok(f"api: 主应用注册了 {len(paths)} 条路由路径")

        # 检查关键路由前缀
        expected_prefixes = [
            "/api/v1/auth",
            "/api/v1/qa",
            "/api/v1/contract",
            "/api/v1/knowledge",
            "/api/v1/analysis",
            "/api/v1/dashboard",
        ]
        for prefix in expected_prefixes:
            matching = [p for p in paths if p.startswith(prefix)]
            assert len(matching) > 0, f"缺少路由前缀: {prefix}，已有路径: {paths}"
        result.ok("api: 所有API路由前缀已注册")

        # 检查健康检查端点
        assert "/health" in paths, "缺少 /health 健康检查端点"
        result.ok("api: /health 健康检查端点存在")

        assert "/" in paths, "缺少 / 根路径端点"
        result.ok("api: / 根路径端点存在")

        # 测试各API路由模块可导入
        from app.api import auth, qa, contract, knowledge, analysis, dashboard
        result.ok("api: 导入所有API路由模块")

        # 验证各路由模块有router属性
        for module_name, module in [
            ("auth", auth),
            ("qa", qa),
            ("contract", contract),
            ("knowledge", knowledge),
            ("analysis", analysis),
            ("dashboard", dashboard),
        ]:
            assert hasattr(module, "router"), f"{module_name} 模块缺少 router 属性"
        result.ok("api: 所有API模块均有 router 属性")

    except Exception as e:
        result.fail("api", str(e))
        traceback.print_exc()


# ============================================================
# 7. Agent工作流测试
# ============================================================

def test_agent():
    """测试Agent工作流构建"""
    print("[7/7] 测试Agent工作流...")

    try:
        # 测试状态定义
        from app.agent.state import ContractReviewState
        result.ok("agent: 导入 ContractReviewState")

        # 验证状态字段
        annotations = ContractReviewState.__annotations__
        expected_fields = [
            "contract_content", "contract_type",
            "parsed_text", "clauses",
            "completeness", "risk_clauses",
            "compliance", "consistency",
            "overall_score", "report",
        ]
        for field in expected_fields:
            assert field in annotations, f"ContractReviewState 缺少字段: {field}"
        result.ok("agent: ContractReviewState 包含所有预期字段")

        # 测试节点函数
        from app.agent.nodes import (
            parse_doc, split_clauses, check_completeness,
            classify_clauses, risk_detect, compliance_check,
            consistency_check, risk_score, suggestions, report_generate,
        )
        result.ok("agent: 导入所有工作流节点函数")

        # 测试工具定义
        from app.agent.tools import TOOLS as agent_tools
        result.ok("agent: 导入 Agent 工具定义")

        if len(agent_tools) > 0:
            result.ok(f"agent: Agent 定义了 {len(agent_tools)} 个工具")
        else:
            result.warn("agent: Agent 工具列表为空")

        # 测试工作流构建
        from app.agent.workflow import ContractReviewWorkflow
        result.ok("agent: 导入 ContractReviewWorkflow")

        workflow = ContractReviewWorkflow()
        assert hasattr(workflow, "graph"), "ContractReviewWorkflow 应有 graph 属性"
        assert hasattr(workflow, "app"), "ContractReviewWorkflow 应有 app 属性（编译后的图）"
        result.ok("agent: ContractReviewWorkflow 初始化成功，图已编译")

    except Exception as e:
        result.fail("agent", str(e))
        traceback.print_exc()


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 60)
    print("  智法通 - 企业级智能法律顾问平台 综合测试")
    print("=" * 60)

    test_config()
    test_security()
    test_models()
    test_rag()
    test_mcp()
    test_api_routes()
    test_agent()

    # 输出报告
    report = result.summary()
    print(report)

    # 返回退出码
    if result.failed:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
