"use client";

import React, { useState } from "react";
import { Check, Copy } from "lucide-react";

interface CodeBlockProps {
  language?: string;
  children: React.ReactNode;
}

export function CodeBlock({ language, children }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const lang = (language || "text").replace(/^language-/, "");

  const getText = (node: React.ReactNode): string => {
    if (node == null || typeof node === "boolean") return "";
    if (typeof node === "string" || typeof node === "number") return String(node);
    if (Array.isArray(node)) return node.map(getText).join("");
    if (React.isValidElement<{ children?: React.ReactNode }>(node)) {
      return getText(node.props.children);
    }
    return "";
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(getText(children).replace(/\n$/, ""));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="code-block-wrapper">
      <div className="code-header">
        <span className="code-lang">{lang}</span>
        <button type="button" className="btn-copy-code" onClick={handleCopy}>
          {copied ? (
            <>
              <Check className="w-3 h-3 inline -mt-px" /> Copied
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 inline -mt-px" /> Copy
            </>
          )}
        </button>
      </div>
      <pre>
        <code className={`language-${lang} hljs`}>{children}</code>
      </pre>
    </div>
  );
}
