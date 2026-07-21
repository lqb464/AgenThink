"use client";

import React, { useState } from "react";
import { Wrench, CheckCircle2, XCircle, ChevronDown, ChevronUp, Eye, Search, Database } from "lucide-react";
import { ToolCallData } from "../lib/types";
import { cn } from "../lib/utils";

interface ToolCallCardProps {
  toolName: string;
  isExecuting?: boolean;
  toolData?: ToolCallData;
}

export function ToolCallCard({ toolName, isExecuting, toolData }: ToolCallCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getToolIcon = (name: string) => {
    if (name.includes("docread") || name.includes("ocr") || name.includes("vision")) {
      return <Eye className="w-4 h-4 text-cyan-400 animate-pulse" />;
    }
    if (
      name.includes("search_documents") ||
      name.includes("summarize_documents") ||
      name.includes("generate_document_report") ||
      name.includes("rag")
    ) {
      return <Database className="w-4 h-4 text-emerald-400" />;
    }
    if (name.includes("web_search") || name.includes("wikipedia") || name.includes("arxiv") || name.includes("search")) {
      return <Search className="w-4 h-4 text-amber-400" />;
    }
    if (name.includes("memory")) {
      return <Database className="w-4 h-4 text-emerald-400" />;
    }
    return <Wrench className="w-4 h-4 text-blue-400" />;
  };

  const getToolFriendlyTitle = (name: string) => {
    if (name === "docread_ocr" || name === "ocr_image") return "Trích xuất văn bản từ ảnh (OCR)";
    if (name === "describe_image" || name === "docread_describe") return "Mô tả ảnh";
    if (name === "detect_objects" || name === "docread_detect") return "Nhận diện đối tượng";
    if (name === "search_documents" || name === "rag_query") return "Tìm trong Tri thức (Local RAG)";
    if (name === "summarize_documents") return "Tóm tắt tài liệu đã upload";
    if (name === "generate_document_report") return "Báo cáo từ tài liệu RAG";
    if (name === "rag_list_documents") return "Liệt kê tài liệu trong Tri thức";
    if (name === "web_search") return "Tìm trên web (SearXNG)";
    if (name === "wikipedia_lookup") return "Tra Wikipedia";
    if (name === "arxiv_search") return "Tìm paper arXiv";
    if (name === "calculator") return "Máy tính toán học tử vi AI";
    if (name === "get_weather") return "Cập nhật thời tiết trực tuyến";
    if (name === "memory_add" || name === "memory_list") return "Hệ thống ghi nhớ dài hạn (Memory Store)";
    return `Thực thi công cụ: ${name}`;
  };

  return (
    <div className="my-2 rounded-xl border border-slate-700/70 bg-slate-900/80 backdrop-blur-md overflow-hidden text-xs shadow-md transition-all duration-200">
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-slate-800/60 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1 rounded-lg bg-slate-800/80 border border-slate-700 shrink-0">
            {getToolIcon(toolName)}
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-slate-200">{getToolFriendlyTitle(toolName)}</span>
            <span className="text-[10px] text-slate-400 font-mono">tool: {toolName}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isExecuting ? (
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-medium text-[11px] animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
              Đang thực thi...
            </span>
          ) : toolData?.success !== undefined ? (
            toolData.success ? (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-medium text-[11px]">
                <CheckCircle2 className="w-3 h-3" /> Hoàn tất
              </span>
            ) : (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 font-medium text-[11px]">
                <XCircle className="w-3 h-3" /> Lỗi tool
              </span>
            )
          ) : (
            <span className="text-slate-500 text-[11px]">Đã xử lý</span>
          )}

          {toolData && (
            <button className="text-slate-400 hover:text-slate-200">
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>

      {isExpanded && toolData && (
        <div className="border-t border-slate-800/80 bg-slate-950/70 p-3 space-y-2 font-mono text-[11px]">
          {toolData.arguments && (
            <div>
              <span className="text-slate-500 block mb-1 uppercase tracking-wider text-[10px] font-sans font-bold">
                Tham số đầu vào (Arguments):
              </span>
              <pre className="p-2 rounded bg-slate-900 text-cyan-300 overflow-x-auto border border-slate-800">
                {JSON.stringify(toolData.arguments, null, 2)}
              </pre>
            </div>
          )}
          {toolData.sources && toolData.sources.length > 0 && (
            <div>
              <span className="text-slate-500 block mb-1 uppercase tracking-wider text-[10px] font-sans font-bold">
                Nguồn (Sources):
              </span>
              <ul className="space-y-1 font-sans">
                {toolData.sources.map((s, i) => (
                  <li
                    key={`${s.filename}-${i}`}
                    className="p-2 rounded bg-slate-900 border border-emerald-500/20 text-emerald-200/90"
                  >
                    <span className="font-semibold text-[11px]">{s.filename}</span>
                    {s.snippet && (
                      <p className="text-slate-400 text-[10px] mt-0.5 line-clamp-3">{s.snippet}</p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {toolData.text && (
            <div>
              <span className="text-slate-500 block mb-1 uppercase tracking-wider text-[10px] font-sans font-bold">
                Kết quả trả về (Tool Output):
              </span>
              <div className="p-2 rounded bg-slate-900 text-slate-300 max-h-48 overflow-y-auto border border-slate-800 whitespace-pre-wrap font-sans">
                {toolData.text}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
