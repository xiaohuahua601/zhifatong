"""
智法通 - 用户模型模块

定义用户、角色、权限相关的数据库模型，
采用RBAC（基于角色的访问控制）权限模型。
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Table
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


# ==================== 多对多关联表 ====================

# 用户-角色关联表（多对多）
user_role = Table(
    "user_role",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, comment="主键ID"),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), comment="用户ID"),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), comment="角色ID"),
    Column("created_at", DateTime, default=datetime.utcnow, comment="创建时间"),
    comment="用户-角色关联表",
)

# 角色-权限关联表（多对多）
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, comment="主键ID"),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), comment="角色ID"),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), comment="权限ID"),
    Column("created_at", DateTime, default=datetime.utcnow, comment="创建时间"),
    comment="角色-权限关联表",
)


class User(Base):
    """用户模型

    存储系统用户的基本信息，包括登录凭证和个人资料。
    通过关联表与角色建立多对多关系。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="哈希密码")
    phone = Column(String(20), unique=True, nullable=True, comment="手机号")
    avatar = Column(String(500), nullable=True, comment="头像URL")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_superuser = Column(Boolean, default=False, comment="是否超级管理员")
    last_login = Column(DateTime, nullable=True, comment="最后登录时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系：用户拥有的角色列表
    roles = relationship("Role", secondary=user_role, back_populates="users", lazy="selectin")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Role(Base):
    """角色模型

    定义系统中的角色，如：管理员、律师、普通用户等。
    每个角色可关联多个权限。
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="角色ID")
    name = Column(String(50), unique=True, nullable=False, comment="角色名称")
    code = Column(String(50), unique=True, nullable=False, index=True, comment="角色编码")
    description = Column(Text, nullable=True, comment="角色描述")
    is_default = Column(Boolean, default=False, comment="是否默认角色")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系：角色下的用户列表
    users = relationship("User", secondary=user_role, back_populates="roles", lazy="selectin")
    # 关系：角色拥有的权限列表
    permissions = relationship("Permission", secondary=role_permission, back_populates="roles", lazy="selectin")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class Permission(Base):
    """权限模型

    定义系统中的细粒度权限，采用 resource:action 的编码格式。
    例如：contract:upload、qa:ask、knowledge:manage 等。
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="权限ID")
    name = Column(String(100), nullable=False, comment="权限名称")
    code = Column(String(100), unique=True, nullable=False, index=True, comment="权限编码（如 contract:upload）")
    resource = Column(String(50), nullable=False, comment="资源类型")
    action = Column(String(50), nullable=False, comment="操作类型")
    description = Column(Text, nullable=True, comment="权限描述")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关系：拥有该权限的角色列表
    roles = relationship("Role", secondary=role_permission, back_populates="permissions", lazy="selectin")

    def __repr__(self):
        return f"<Permission(id={self.id}, code='{self.code}')>"
