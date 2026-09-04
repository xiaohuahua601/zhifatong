"""
智法通 - 文件解析模块

支持解析PDF、Word和TXT格式的文件，
提取文本内容用于后续处理。
"""

import os
from typing import Optional


class FileParser:
    """文件解析器类

    根据文件类型选择对应的解析方法，提取文本内容。
    """

    @staticmethod
    async def parse(file_path: str, file_type: str) -> str:
        """解析文件，提取文本内容

        Args:
            file_path: 文件路径
            file_type: 文件类型（pdf/docx/doc/txt）

        Returns:
            提取的文本内容

        Raises:
            ValueError: 不支持的文件类型
            FileNotFoundError: 文件不存在
        """
        # 验证文件存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在：{file_path}")

        # 根据文件类型选择解析方法
        if file_type == "pdf":
            return await FileParser._parse_pdf(file_path)
        elif file_type in ("docx", "doc"):
            return await FileParser._parse_docx(file_path)
        elif file_type == "txt":
            return await FileParser._parse_txt(file_path)
        else:
            raise ValueError(f"不支持的文件类型：{file_type}")

    @staticmethod
    async def _parse_pdf(file_path: str) -> str:
        """解析PDF文件

        使用PyMuPDF（fitz）库提取PDF文本内容。

        Args:
            file_path: PDF文件路径

        Returns:
            提取的文本内容
        """
        try:
            import fitz  # PyMuPDF

            text_parts = []
            doc = fitz.open(file_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(text.strip())

            doc.close()
            return "\n\n".join(text_parts)

        except ImportError:
            # 如果PyMuPDF未安装，尝试使用pdfplumber
            try:
                import pdfplumber

                text_parts = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)

                return "\n\n".join(text_parts)

            except ImportError:
                raise ImportError(
                    "PDF解析需要安装PyMuPDF或pdfplumber库。"
                    "请运行：pip install PyMuPDF 或 pip install pdfplumber"
                )

    @staticmethod
    async def _parse_docx(file_path: str) -> str:
        """解析Word文件

        使用python-docx库提取Word文档文本内容。

        Args:
            file_path: Word文件路径

        Returns:
            提取的文本内容
        """
        try:
            from docx import Document

            doc = Document(file_path)
            text_parts = []

            # 提取段落文本
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text.strip())

            # 提取表格文本
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        text_parts.append(row_text)

            return "\n\n".join(text_parts)

        except ImportError:
            raise ImportError(
                "Word文档解析需要安装python-docx库。"
                "请运行：pip install python-docx"
            )

    @staticmethod
    async def _parse_txt(file_path: str) -> str:
        """解析TXT文件

        直接读取文本文件内容，支持多种编码。

        Args:
            file_path: TXT文件路径

        Returns:
            文件文本内容
        """
        # 尝试多种编码读取
        encodings = ["utf-8", "gbk", "gb2312", "gb18030", "latin-1"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue

        # 所有编码都失败，使用二进制模式读取并替换错误字符
        with open(file_path, "rb") as f:
            return f.read().decode("utf-8", errors="replace")
