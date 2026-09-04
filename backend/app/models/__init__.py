"""
智法通 - 数据模型包

导出所有数据库模型，方便统一导入和数据库迁移。
"""

from app.models.user import User, Role, Permission, user_role, role_permission
from app.models.qa import Conversation, Message, QAFeedback, MessageRole, ConversationStatus
from app.models.contract import Contract, ReviewReport, RiskClause, ContractStatus, RiskLevel
from app.models.knowledge import LegalDocument, DocumentChunk, DocumentStatus, DocumentSource
from app.models.analysis import QueryLog, CitationStat

__all__ = [
    # 用户相关
    "User", "Role", "Permission", "user_role", "role_permission",
    # 问答相关
    "Conversation", "Message", "QAFeedback", "MessageRole", "ConversationStatus",
    # 合同相关
    "Contract", "ReviewReport", "RiskClause", "ContractStatus", "RiskLevel",
    # 知识库相关
    "LegalDocument", "DocumentChunk", "DocumentStatus", "DocumentSource",
    # 分析相关
    "QueryLog", "CitationStat",
]
