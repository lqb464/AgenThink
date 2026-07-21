import hljs from "highlight.js/lib/core";
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import python from "highlight.js/lib/languages/python";
import json from "highlight.js/lib/languages/json";
import bash from "highlight.js/lib/languages/bash";
import css from "highlight.js/lib/languages/css";
import xml from "highlight.js/lib/languages/xml";
import markdown from "highlight.js/lib/languages/markdown";
import sql from "highlight.js/lib/languages/sql";

hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("js", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("ts", typescript);
hljs.registerLanguage("python", python);
hljs.registerLanguage("py", python);
hljs.registerLanguage("json", json);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("shell", bash);
hljs.registerLanguage("sh", bash);
hljs.registerLanguage("css", css);
hljs.registerLanguage("html", xml);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("markdown", markdown);
hljs.registerLanguage("md", markdown);
hljs.registerLanguage("sql", sql);

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function highlightLine(code: string, lang: string): string {
  if (!lang || !code.trim()) return esc(code);
  try {
    if (hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
  } catch {
    /* fall through */
  }
  return esc(code);
}

function styleInline(s: string): string {
  let h = esc(s);
  h = h.replace(
    /`([^`]+)`/g,
    (_m, code: string) =>
      `<span class="cip-inline"><span class="cip-hidden">\`</span><span class="cip-inline-code">${code}</span><span class="cip-hidden">\`</span></span>`
  );
  h = h.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  h = h.replace(/\*(.+?)\*/g, "<em>$1</em>");
  return h;
}

/** Live Markdown preview HTML (char widths stay synced with textarea). */
export function buildComposerPreviewHtml(text: string): string {
  if (!text) return "";

  const lines = text.split("\n");
  const parts: { html: string; block?: boolean }[] = [];
  let inFence = false;
  let fenceLang = "";
  let fenceRows: string[] = [];

  const flushFence = () => {
    if (!fenceRows.length) return;
    parts.push({
      block: true,
      html: `<div class="cip-code-card">${fenceRows.join("")}</div>`,
    });
    fenceRows = [];
  };

  for (const line of lines) {
    const fence = line.match(/^(\s*)```([a-zA-Z0-9_+-]*)\s*$/);
    if (fence) {
      const indent = esc(fence[1]);
      const lang = (fence[2] || "").toLowerCase();
      if (!inFence) {
        inFence = true;
        fenceLang = lang;
        fenceRows.push(
          `<div class="cip-block cip-block-head">${indent}` +
            `<span class="cip-tick">\`\`\`</span>` +
            (lang ? `<span class="cip-lang">${esc(lang)}</span>` : "") +
            `</div>`
        );
      } else {
        fenceRows.push(
          `<div class="cip-block cip-block-foot">${indent}` +
            `<span class="cip-tick">${esc(line.slice(fence[1].length))}</span>` +
            `</div>`
        );
        inFence = false;
        fenceLang = "";
        flushFence();
      }
      continue;
    }
    if (inFence) {
      const hl = highlightLine(line, fenceLang);
      fenceRows.push(`<div class="cip-block cip-code-line hljs">${hl || "&nbsp;"}</div>`);
      continue;
    }
    const quote = line.match(/^(\s*)>(.*)$/);
    if (quote) {
      parts.push({
        html: `${esc(quote[1])}<span class="cip-quote"><span class="cip-qmark">&gt;</span>${styleInline(quote[2])}</span>`,
      });
      continue;
    }
    const ul = line.match(/^(\s*)([-*])(\s+)(.*)$/);
    if (ul) {
      parts.push({
        html:
          `${esc(ul[1])}<span class="cip-ul-mark">${esc(ul[2])}</span>${esc(ul[3])}` +
          `<span class="cip-li-body">${styleInline(ul[4])}</span>`,
      });
      continue;
    }
    const ol = line.match(/^(\s*)(\d+\.)(\s+)(.*)$/);
    if (ol) {
      parts.push({
        html:
          `${esc(ol[1])}<span class="cip-ol-mark">${esc(ol[2])}</span>${esc(ol[3])}` +
          `<span class="cip-li-body">${styleInline(ol[4])}</span>`,
      });
      continue;
    }
    parts.push({ html: styleInline(line) });
  }
  flushFence();

  let html = "";
  for (let i = 0; i < parts.length; i++) {
    if (i > 0) html += "<br/>";
    html += parts[i].html;
  }
  return html;
}
