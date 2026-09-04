// Mermaid 9.4.3 语法解析验证（与 Typora 1.2.3 内置版本一致）
// 用 jsdom 提供 DOM 环境后调用 mermaid.parse 逐一校验文档中的图表
const fs = require("fs");
const { JSDOM } = require("jsdom");

// 构造最小 DOM 环境（mermaid 初始化需要 window/document）
const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { pretendToBeVisual: true });
global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;
global.DOMParser = dom.window.DOMParser;
global.XMLSerializer = dom.window.XMLSerializer;

const mermaid = require("mermaid");
mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });

const blocks = JSON.parse(
  fs.readFileSync(
    "e:/临时项目/3_大模型项目_实施/项目1_智法通_企业级智能法律顾问平台/scripts/mermaid_blocks.json",
    "utf-8"
  )
);

(async () => {
  let pass = 0;
  let fail = 0;
  for (const b of blocks) {
    try {
      // mermaid.parse 成功（返回 true 或图定义）即语法有效
      await mermaid.parse(b.code);
      pass++;
      console.log(`[PASS] 图 ${b.index} (${b.code.trim().split("\n")[0].trim()})`);
    } catch (e) {
      fail++;
      const msg = String(e.message || e).split("\n").slice(0, 3).join(" | ");
      console.log(`[FAIL] 图 ${b.index}: ${msg}`);
    }
  }
  console.log(`\n结果: ${pass}/${blocks.length} 通过，${fail} 失败`);
  process.exit(fail > 0 ? 1 : 0);
})();
