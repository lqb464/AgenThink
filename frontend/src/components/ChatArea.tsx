"use client";

import React, { useRef, useEffect } from "react";
import { Message } from "../lib/types";
import { MessageBubble } from "./MessageBubble";
import { Artifact } from "./ArtifactsPanel";
import { BrainCircuit, Sparkles, Wand2, Eye, Calculator, BookOpen } from "lucide-react";

interface ChatAreaProps {
  messages: Message[];
  onSuggestionClick: (text: string) => void;
  isStreaming: boolean;
  language?: "vi" | "en";
  onPinArtifact?: (artifact: Artifact) => void;
}

export function ChatArea({
  messages,
  onSuggestionClick,
  isStreaming,
  language = "vi",
  onPinArtifact,
}: ChatAreaProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const en = language === "en";

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  const suggestions = en
    ? [
        {
          icon: <BookOpen className="w-4 h-4 text-emerald-400" />,
          title: "Ask your docs (RAG)",
          prompt:
            "Based on documents uploaded in Knowledge, answer a related question and cite source filenames.",
        },
        {
          icon: <Calculator className="w-4 h-4 text-teal-400" />,
          title: "Autonomy: calc + memory",
          prompt:
            "My name is An. Compute 10% VAT on 7 million, remember my name, then briefly explain your steps.",
        },
        {
          icon: <Wand2 className="w-4 h-4 text-sky-400" />,
          title: "Weather",
          prompt: "What is the weather today in Ho Chi Minh City?",
        },
        {
          icon: <Eye className="w-4 h-4 text-cyan-400" />,
          title: "OCR from image",
          prompt: "Please read and extract text (OCR) from the attached image.",
        },
      ]
    : [
        {
          icon: <BookOpen className="w-4 h-4 text-emerald-400" />,
          title: "Hỏi tài liệu (RAG)",
          prompt:
            "Dựa trên các tài liệu đã upload trong Tri thức, hãy trả lời câu hỏi liên quan và trích dẫn tên file nguồn.",
        },
        {
          icon: <Calculator className="w-4 h-4 text-teal-400" />,
          title: "Autonomy: tính + nhớ",
          prompt:
            "Tên tôi là An. Hãy tính thuế VAT 10% của 7 triệu, nhớ tên tôi, rồi giải thích ngắn gọn các bước bạn đã làm.",
        },
        {
          icon: <Wand2 className="w-4 h-4 text-sky-400" />,
          title: "Thời tiết",
          prompt: "Thời tiết hôm nay ở Thành phố Hồ Chí Minh ra sao?",
        },
        {
          icon: <Eye className="w-4 h-4 text-cyan-400" />,
          title: "OCR từ ảnh",
          prompt: "Hãy giúp tôi đọc và trích xuất chữ (OCR) từ hình ảnh đính kèm.",
        },
      ];

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent flex flex-col"
    >
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-2xl mx-auto text-center space-y-6 my-auto">
          <div className="relative msg-in">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-emerald-500 via-teal-500 to-cyan-600 flex items-center justify-center shadow-2xl shadow-emerald-500/25">
              <BrainCircuit className="w-10 h-10 text-white" />
            </div>
            <div className="absolute -bottom-1 -right-1 bg-slate-900 border border-slate-700 rounded-full p-1.5 shadow-md">
              <Sparkles className="w-4 h-4 text-emerald-300" />
            </div>
          </div>

          <div className="space-y-2 msg-in" style={{ animationDelay: "0.06s" }}>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-100">
              <span className="bg-gradient-to-r from-emerald-300 via-teal-200 to-cyan-300 bg-clip-text text-transparent">
                AgenThink
              </span>
            </h1>
            <p className="text-sm text-slate-400 max-w-md leading-relaxed">
              {en
                ? "Upload docs in Knowledge, ask cross-doc questions, pin long reports as Artifacts — hybrid RAG + vision."
                : "Upload tài liệu ở Tri thức, hỏi cross-doc, ghim báo cáo dài thành Artifact — hybrid RAG + vision."}
            </p>
            <p className="text-[11px] text-slate-600">
              {en
                ? "Tip: switch VN/EN and Gemini / Local in the toolbar above."
                : "Gợi ý: đổi VN/EN và Gemini / Local trên thanh công cụ phía trên."}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full pt-4">
            {suggestions.map((item, idx) => (
              <button
                key={idx}
                onClick={() => onSuggestionClick(item.prompt)}
                className="group flex flex-col items-start gap-1.5 p-3.5 rounded-2xl border border-slate-800/80 bg-slate-900/50 hover:bg-slate-800/70 hover:border-emerald-500/40 transition-all text-left"
              >
                <div className="flex items-center gap-2 font-semibold text-xs text-slate-200">
                  {item.icon}
                  <span>{item.title}</span>
                </div>
                <span className="text-xs text-slate-400 group-hover:text-slate-300 line-clamp-2 leading-relaxed">
                  &ldquo;{item.prompt}&rdquo;
                </span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex flex-col w-full max-w-4xl mx-auto py-5 pb-2">
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onPinArtifact={onPinArtifact}
            />
          ))}
        </div>
      )}
    </div>
  );
}
