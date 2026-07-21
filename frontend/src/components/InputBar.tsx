"use client";

import React, { useState, useRef, useEffect, useMemo } from "react";
import { Send, Paperclip, X, StopCircle } from "lucide-react";
import { buildComposerPreviewHtml } from "../lib/composerPreview";
import { cn } from "../lib/utils";

interface InputBarProps {
  onSendMessage: (text: string, files: File[]) => void;
  onStopStreaming: () => void;
  isStreaming: boolean;
}

export function InputBar({ onSendMessage, onStopStreaming, isStreaming }: InputBarProps) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [filePreviews, setFilePreviews] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const previewRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const previewHtml = useMemo(() => buildComposerPreviewHtml(text), [text]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(el.scrollHeight, 220);
    el.style.height = `${next}px`;
    el.style.overflowY = el.scrollHeight > 220 ? "auto" : "hidden";
  }, [text]);

  const syncPreviewScroll = () => {
    if (textareaRef.current && previewRef.current) {
      previewRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length === 0) return;

    setFiles((prev) => [...prev, ...selectedFiles]);
    selectedFiles.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        setFilePreviews((prev) => [...prev, reader.result as string]);
      };
      reader.readAsDataURL(file);
    });

    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setFilePreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if ((!text.trim() && files.length === 0) || isStreaming) return;

    onSendMessage(text, files);
    setText("");
    setFiles([]);
    setFilePreviews([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const el = e.currentTarget;

    if (e.key === "Tab") {
      e.preventDefault();
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const val = el.value;
      const indent = "  ";
      const next = val.substring(0, start) + indent + val.substring(end);
      setText(next);
      requestAnimationFrame(() => {
        el.selectionStart = el.selectionEnd = start + indent.length;
      });
      return;
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
      return;
    }

    if (e.key === "Enter" && e.shiftKey) {
      const val = el.value;
      const start = el.selectionStart;
      const lineStart = val.lastIndexOf("\n", start - 1) + 1;
      const currentLine = val.substring(lineStart, start);

      const fenceMatch = currentLine.match(/^(\s*)```([a-zA-Z0-9_-]*)\s*$/);
      if (fenceMatch) {
        const lang = fenceMatch[2];
        let isOpening = lang.length > 0;
        if (!isOpening) {
          const textBefore = val.substring(0, lineStart);
          const previousFences = (textBefore.match(/```/g) || []).length;
          if (previousFences % 2 === 0) isOpening = true;
        }
        if (isOpening) {
          e.preventDefault();
          const indent = fenceMatch[1];
          const insertion = "\n" + indent + "\n" + indent + "```";
          const next = val.substring(0, start) + insertion + val.substring(el.selectionEnd);
          setText(next);
          requestAnimationFrame(() => {
            el.selectionStart = el.selectionEnd = start + 1 + indent.length;
          });
          return;
        }
      }

      const bulletMatch = currentLine.match(/^(\s*)[-*]\s+(.*)$/);
      if (bulletMatch) {
        e.preventDefault();
        let next: string;
        let caret: number;
        if (!bulletMatch[2].trim()) {
          next = val.substring(0, lineStart) + val.substring(start);
          caret = lineStart;
        } else {
          const insertion = "\n" + bulletMatch[1] + "- ";
          next = val.substring(0, start) + insertion + val.substring(el.selectionEnd);
          caret = start + insertion.length;
        }
        setText(next);
        requestAnimationFrame(() => {
          el.selectionStart = el.selectionEnd = caret;
        });
        return;
      }

      const numberMatch = currentLine.match(/^(\s*)(\d+)\.\s+(.*)$/);
      if (numberMatch) {
        e.preventDefault();
        let next: string;
        let caret: number;
        if (!numberMatch[3].trim()) {
          next = val.substring(0, lineStart) + val.substring(start);
          caret = lineStart;
        } else {
          const nextNum = parseInt(numberMatch[2], 10) + 1;
          const insertion = "\n" + numberMatch[1] + nextNum + ". ";
          next = val.substring(0, start) + insertion + val.substring(el.selectionEnd);
          caret = start + insertion.length;
        }
        setText(next);
        requestAnimationFrame(() => {
          el.selectionStart = el.selectionEnd = caret;
        });
      }
    }
  };

  return (
    <div className="p-3 sm:p-4 bg-gradient-to-t from-slate-950 via-slate-950/95 to-transparent">
      <div
        className={cn(
          "chat-composer max-w-4xl mx-auto",
          isStreaming && "opacity-95"
        )}
      >
        {filePreviews.length > 0 && (
          <div className="flex flex-wrap gap-2 px-3 pt-3 pb-1 border-b border-slate-800/60">
            {filePreviews.map((preview, idx) => (
              <div
                key={idx}
                className="relative group rounded-xl overflow-hidden border border-slate-700 bg-slate-950 w-16 h-16"
              >
                <img src={preview} alt="Attached file preview" className="w-full h-full object-cover" />
                <button
                  type="button"
                  onClick={() => removeFile(idx)}
                  className="absolute top-1 right-1 p-1 rounded-full bg-red-500/80 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Xóa đính kèm"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="chat-input-wrapper">
            <div
              ref={previewRef}
              className="chat-input-preview"
              aria-hidden="true"
              dangerouslySetInnerHTML={{ __html: previewHtml }}
            />
            <textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              onScroll={syncPreviewScroll}
              disabled={isStreaming}
              placeholder="Hỏi AgenThink điều gì đó — Markdown, ảnh OCR, thời trang, thử đồ..."
              rows={1}
              spellCheck={false}
            />
          </div>

          <div className="chat-composer-bar">
            <div className="flex items-center gap-1">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="image/*"
                multiple
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isStreaming}
                className="p-2 rounded-lg text-slate-400 hover:text-[#5bcefa] hover:bg-slate-800/80 transition-all disabled:opacity-50 disabled:pointer-events-none"
                title="Đính kèm hình ảnh"
              >
                <Paperclip className="w-4 h-4" />
              </button>
              <span className="chat-sel-count hidden sm:inline">
                Enter gửi · Shift+Enter dòng mới
              </span>
            </div>

            {isStreaming ? (
              <button
                type="button"
                onClick={onStopStreaming}
                className="btn-send-stop flex items-center gap-1.5 px-3 py-2 rounded-[10px] text-xs font-semibold bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500 hover:text-white transition-all"
                title="Dừng phản hồi"
              >
                <StopCircle className="w-4 h-4 animate-pulse" />
                <span>Dừng</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!text.trim() && files.length === 0}
                className="btn-send flex items-center gap-1.5 px-3.5 py-2 rounded-[10px] text-xs font-semibold text-white bg-[#0095ff] hover:bg-[#0071c5] shadow-[0_0_0_3px_rgba(0,149,255,0.12)] disabled:opacity-40 disabled:pointer-events-none disabled:shadow-none transition-all"
                title="Gửi tin nhắn"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Gửi</span>
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
