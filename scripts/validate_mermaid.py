# -*- coding: utf-8 -*-
"""校验需求文档 mermaid 图表的结构完整性

检查项：
1. 代码围栏 ``` 配对完整性
2. mermaid 块数量与语法类型
3. 残留 ASCII 字符画（目录树除外）
4. 提取全部 mermaid 块供后续语法解析验证
"""
import io
import re
import json

DOC = r"e:\临时项目\3_大模型项目_实施\项目1_智法通_企业级智能法律顾问平台\项目1_智法通_企业级智能法律顾问平台_项目需求文档.md"

content = io.open(DOC, encoding="utf-8").read()
lines = content.splitlines()

# 1. 围栏配对检查
fence_lines = [i for i, l in enumerate(lines) if l.strip().startswith("```")]
print(f"围栏线总数: {len(fence_lines)}，配对: {'OK' if len(fence_lines) % 2 == 0 else 'ERROR'}")

# 2. mermaid 块统计
mermaid_blocks = re.findall(r"(?ms)^```mermaid\n(.*?)^```$", content)
print(f"mermaid 块数: {len(mermaid_blocks)}")
types = {}
for b in mermaid_blocks:
    first = b.strip().splitlines()[0].strip()
    types[first] = types.get(first, 0) + 1
for t, c in types.items():
    print(f"  - {t}: {c} 块")

# 3. 残留 ASCII 图（排除目录树行：含 ├── 或 └── 的行）
box_chars = "┌┐┘┤┼"
residual = [
    (i + 1, l)
    for i, l in enumerate(lines)
    if any(c in l for c in box_chars) and ("├──" not in l and "└──" not in l)
]
print(f"残留 ASCII 图行: {len(residual)}")
for ln, l in residual[:10]:
    print(f"  L{ln}: {l[:60]}")

# 4. 导出 mermaid 块供 node 解析验证
export = [
    {"index": i + 1, "code": b}
    for i, b in enumerate(mermaid_blocks)
]
with io.open(
    r"e:\临时项目\3_大模型项目_实施\项目1_智法通_企业级智能法律顾问平台\scripts\mermaid_blocks.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(export, f, ensure_ascii=False, indent=1)
print("已导出 mermaid_blocks.json 供语法解析验证")
