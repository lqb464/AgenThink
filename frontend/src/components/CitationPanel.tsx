"use client";

import React, { useState } from "react";
import { FileText, Quote } from "lucide-react";
import { CitationSource } from "../lib/types";
import { cn } from "../lib/utils";

interface CitationPanelProps {
  sources: CitationSource[];
}

export function CitationPanel({ sources }: CitationPanelProps) {
  const [openIdx, setOpenIdx] = useState<number | null>(0);

  if (!sources?.length) return null;

  // Deduplicate by filename, keep first snippet
  const seen = new Set<string>();
  const unique: CitationSource[] = [];
  for (const s of sources) {
    const key = s.filename || "";
    if (!key || seen.has(key)) {
      if (key && !seen.has(`${key}::${s.snippet?.slice(0, 40)}`)) {
        // allow multiple snippets same file with different text
        unique.push(s);
        seen.add(`${key}::${s.snippet?.slice(0, 40)}`);
      }
      continue;
    }
    seen.add(key);
    unique.push(s);
  }

  return (
    <div className="w-full my-1 rounded-xl border border-emerald-500/25 bg-emerald-500/[0.06] px-3 py-2 text-xs">
      <div className="flex items-center gap-2 text-emerald-300/95 font-semibold mb-1.5">
        <Quote className="w-3.5 h-3.5" />
        Nguồn trích dẫn ({unique.length})
      </div>
      <div className="flex flex-wrap gap-1.5 mb-1.5">
        {unique.map((s, idx) => (
          <button
            key={`${s.filename}-${idx}`}
            type="button"
            onClick={() => setOpenIdx(openIdx === idx ? null : idx)}
            className={cn(
              "inline-flex items-center gap-1 px-2 py-1 rounded-lg border text-[11px] transition-colors",
              openIdx === idx
                ? "border-emerald-400/50 bg-emerald-500/15 text-emerald-200"
                : "border-slate-700/80 bg-slate-900/60 text-slate-300 hover:border-emerald-500/40"
            )}
            title={s.filename}
          >
            <FileText className="w-3 h-3 shrink-0" />
            <span className="truncate max-w-[160px]">{s.filename}</span>
          </button>
        ))}
      </div>
      {openIdx !== null && unique[openIdx]?.snippet && (
        <div className="p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-slate-400 text-[11px] leading-relaxed whitespace-pre-wrap max-h-28 overflow-y-auto">
          {unique[openIdx].snippet}
        </div>
      )}
    </div>
  );
}

/** Collect citations from tool results for a message. */
export function collectCitations(
  toolResults?: { sources?: CitationSource[]; tool?: string }[]
): CitationSource[] {
  if (!toolResults?.length) return [];
  const out: CitationSource[] = [];
  for (const t of toolResults) {
    if (t.sources?.length) {
      out.push(...t.sources);
      continue;
    }
    // Fallback: parse [filename] blocks from RAG tool text
    if (
      t.tool &&
      (t.tool.includes("search_documents") ||
        t.tool.includes("summarize") ||
        t.tool.includes("report") ||
        t.tool.includes("rag"))
    ) {
      // no structured sources — skip
    }
  }
  return out;
}
