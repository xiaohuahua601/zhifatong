-- ============================================================
-- 智法通 - 企业级智能法律顾问平台 数据库初始化脚本
-- 数据库: MySQL 8.0+
-- 字符集: utf8mb4
-- 排序规则: utf8mb4_unicode_ci
-- 说明: 仅创建数据库，表结构由后端SQLAlchemy ORM自动创建
--       （Base.metadata.create_all），避免与模型定义冲突
-- ============================================================

-- 设置字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET character_set_connection=utf8mb4;

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS zhifatong
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE zhifatong;
