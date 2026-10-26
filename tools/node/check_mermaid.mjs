// Syntax-check all ```mermaid blocks in a Markdown file.
// Usage: node tools/node/check_mermaid.mjs docs/diagrams.md
import { JSDOM } from "jsdom";
import fs from "fs";

const dom = new JSDOM("<!DOCTYPE html><body></body>");
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const mermaid = (await import("mermaid")).default;
mermaid.initialize({ startOnLoad: false });

const text = fs.readFileSync(process.argv[2], "utf8");
const blocks = process.argv[2].endsWith(".mmd")
  ? [text]
  : [...text.matchAll(/```mermaid\n([\s\S]*?)```/g)].map((m) => m[1]);
let bad = 0;
for (const [i, b] of blocks.entries()) {
  try {
    await mermaid.parse(b);
    console.log(`block ${i + 1}: ok`);
  } catch (e) {
    bad++;
    console.log(`block ${i + 1}: ERROR ${String(e.message || e).slice(0, 300)}`);
  }
}
process.exit(bad || !blocks.length ? 1 : 0);
