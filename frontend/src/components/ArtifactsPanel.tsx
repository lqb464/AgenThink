"use client";

import React, { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Download, FileText, X } from "lucide-react";
import { cn } from "../lib/utils";

export type Artifact = {
  id: string;
  title: string;
  content: string;
  kind: "report" | "plan" | "code" | "markdown";
  source?: string;
};

interface ArtifactsPanelProps {
  artifact: Artifact | null;
  open: boolean;
  onClose: () => void;
  language?: "vi" | "en";
}

export function detectArtifactFromText(
  text: string,
  source?: string
): Artifact | null {
  const trimmed = (text || "").trim();
  if (trimmed.length < 400) return null;

  const hasHeading = /^#{1,3}\s+/m.test(trimmed);
  const hasCodeFence = /```/.test(trimmed);
  const isReportTool =
    source === "generate_document_report" ||
    source === "summarize_documents" ||
    /báo cáo|report|tóm tắt|summary/i.test(source || "");

  if (!hasHeading && !hasCodeFence && !isReportTool && trimmed.length < 800) {
    return null;
  }

  let kind: Artifact["kind"] = "markdown";
  if (hasCodeFence && trimmed.length - trimmed.replace(/```/g, "").length >= 6) {
    kind = "code";
  } else if (isReportTool || /báo cáo|report/i.test(trimmed.slice(0, 120))) {
    kind = "report";
  } else if (/^#{1,3}\s+(plan|kế hoạch|roadmap)/im.test(trimmed)) {
    kind = "plan";
  }

  const titleMatch = trimmed.match(/^#\s+(.+)$/m);
  const title =
    titleMatch?.[1]?.slice(0, 80) ||
    (kind === "report" ? "Report" : kind === "plan" ? "Plan" : "Artifact");

  return {
    id: `art-${Date.now()}`,
    title,
    content: trimmed,
    kind,
    source,
  };
}

export function ArtifactsPanel({
  artifact,
  open,
  onClose,
  language = "vi",
}: ArtifactsPanelProps) {
  const labels = useMemo(
    () =>
      language === "en"
        ? { title: "Artifact", copy: "Copy", export: "Export", empty: "No artifact pinned" }
        : { title: "Artifact", copy: "Sao chép", export: "Xuất file", empty: "Chưa ghim artifact" },
    [language]
  );

  if (!open) return null;

  const copy = async () => {
    if (!artifact) return;
    try {
      await navigator.clipboard.writeText(artifact.content);
    } catch {
      /* ignore */
    }
  };

  const exportMd = () => {
    if (!artifact) return;
    const blob = new Blob([artifact.content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${artifact.title.replace(/\s+/g, "_").slice(0, 40)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <aside
      className={cn(
        "flex flex-col h-full border-l border-slate-800/80 bg-slate-950/95 backdrop-blur-xl w-full sm:w-[380px] lg:w-[420px] shrink-0 z-20"
      )}
    >
      <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-4 h-4 text-emerald-400 shrink-0" />
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-wider text-slate-500">{labels.title}</p>
            <p className="text-sm font-semibold text-slate-100 truncate">
              {artifact?.title || labels.empty}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={copy}
            disabled={!artifact}
            className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-300 hover:bg-slate-800 disabled:opacity-40"
            title={labels.copy}
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={exportMd}
            disabled={!artifact}
            className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-300 hover:bg-slate-800 disabled:opacity-40"
            title={labels.export}
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 prose prose-invert prose-sm max-w-none scrollbar-thin scrollbar-thumb-slate-800">
        {artifact ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
        ) : (
          <p className="text-sm text-slate-500">{labels.empty}</p>
        )}
      </div>
    </aside>
  );
}
