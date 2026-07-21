"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { ListChecks, RefreshCw, Pin } from "lucide-react";
import { Message } from "../lib/types";
import { ToolCallCard } from "./ToolCallCard";
import { CodeBlock } from "./CodeBlock";
import { TypingIndicator } from "./TypingIndicator";
import { CitationPanel, collectCitations } from "./CitationPanel";
import { cn } from "../lib/utils";
import { detectArtifactFromText, Artifact } from "./ArtifactsPanel";

interface MessageBubbleProps {
  message: Message;
  onPinArtifact?: (artifact: Artifact) => void;
}

function extractText(content: Message["content"]): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((part) => (typeof part === "string" ? part : part.text || ""))
      .join("\n");
  }
  return "";
}

export function MessageBubble({ message, onPinArtifact }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const textContent = extractText(message.content);
  const hasActiveTools = !isUser && !!message.activeTools?.length;
  const hasToolResults = !isUser && !!message.toolResults?.length;
  const hasPlan = !isUser && !!message.planSteps?.length;
  const citations = message.citations || collectCitations(message.toolResults) || [];
  const showTyping =
    !isUser &&
    !!message.isStreaming &&
    !textContent.trim() &&
    !hasActiveTools &&
    !hasToolResults &&
    !hasPlan;

  const canPin = (() => {
    if (isUser || message.isStreaming || !onPinArtifact) return false;
    const reportTool = message.toolResults?.find(
      (t) =>
        t.tool === "generate_document_report" ||
        t.tool === "summarize_documents"
    );
    if (reportTool?.text && reportTool.text.length > 200) return true;
    return !!detectArtifactFromText(textContent);
  })();

  const handlePin = () => {
    if (!onPinArtifact) return;
    const reportTool = message.toolResults?.find(
      (t) =>
        t.tool === "generate_document_report" ||
        t.tool === "summarize_documents"
    );
    const fromTool =
      reportTool?.text &&
      detectArtifactFromText(reportTool.text, reportTool.tool);
    const art =
      fromTool ||
      detectArtifactFromText(textContent, "assistant") ||
      ({
        id: `art-${message.id}`,
        title: "Deliverable",
        content: textContent,
        kind: "markdown" as const,
      });
    onPinArtifact(art);
  };

  if (showTyping) {
    return <TypingIndicator />;
  }

  return (
    <div
      className={cn(
        "msg-row msg-in flex w-full px-4 py-1.5",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "flex flex-col gap-2",
          isUser ? "max-w-[92%] sm:max-w-[75%] items-end" : "w-full max-w-full items-start"
        )}
      >
        {message.images && message.images.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {message.images.map((img, idx) => (
              <div
                key={idx}
                className="relative rounded-xl overflow-hidden border border-slate-700/70 shadow-md max-w-xs"
              >
                <img
                  src={img}
                  alt="Uploaded attachment"
                  className="max-h-48 w-auto object-cover"
                />
              </div>
            ))}
          </div>
        )}

        {hasPlan && (
          <div className="w-full my-1 rounded-xl border border-slate-700/70 bg-slate-900/70 px-3 py-2 text-xs">
            <div className="flex items-center gap-2 text-slate-200 font-semibold mb-1.5">
              <ListChecks className="w-4 h-4 text-[#5bcefa]" />
              Kế hoạch
            </div>
            <ol className="list-decimal list-inside space-y-1 text-slate-300">
              {message.planSteps!.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          </div>
        )}

        {message.reflectStatus && message.isStreaming && (
          <div className="flex items-center gap-1.5 text-[11px] text-amber-300/90 px-1">
            <RefreshCw className="w-3 h-3 animate-spin" />
            {message.reflectStatus === "critiquing" && "Đang phản chiếu / kiểm tra câu trả lời…"}
            {message.reflectStatus === "retry" && "Cải thiện câu trả lời theo feedback…"}
            {message.reflectStatus === "pass" && "Phản chiếu: đạt"}
            {!["critiquing", "retry", "pass"].includes(message.reflectStatus) &&
              `Reflect: ${message.reflectStatus}`}
          </div>
        )}

        {hasToolResults && (
          <div className="w-full space-y-1">
            {message.toolResults!.map((td, idx) => (
              <ToolCallCard
                key={`${td.tool}-done-${idx}`}
                toolName={td.tool}
                isExecuting={false}
                toolData={td}
              />
            ))}
          </div>
        )}

        {hasActiveTools && message.isStreaming && (
          <div className="w-full space-y-1">
            {message.activeTools!
              .filter((tname) => !message.toolResults?.some((t) => t.tool === tname))
              .map((tname, idx) => (
                <ToolCallCard
                  key={`${tname}-active-${idx}`}
                  toolName={tname}
                  isExecuting
                />
              ))}
          </div>
        )}

        {!isUser && citations.length > 0 && <CitationPanel sources={citations} />}

        {(textContent || (!isUser && message.isStreaming)) && (
          <div className={cn(isUser ? "msg user" : "msg bot")}>
            {isUser ? (
              <div className="md-content whitespace-pre-wrap">{textContent}</div>
            ) : (
              <div className="md-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    pre({ children }) {
                      return <>{children}</>;
                    },
                    code({ className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || "");
                      const isBlock =
                        !!match || String(children).includes("\n");
                      if (isBlock) {
                        return (
                          <CodeBlock language={match?.[1]}>
                            {children}
                          </CodeBlock>
                        );
                      }
                      return (
                        <code className={cn("inline-code", className)} {...props}>
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {textContent}
                </ReactMarkdown>
                {message.isStreaming && textContent && (
                  <span className="stream-cursor" aria-hidden />
                )}
              </div>
            )}
          </div>
        )}

        {canPin && (
          <button
            type="button"
            onClick={handlePin}
            className="inline-flex items-center gap-1.5 text-[11px] text-emerald-400/90 hover:text-emerald-300 px-2 py-1 rounded-md border border-emerald-500/20 hover:border-emerald-500/40 bg-emerald-500/5 transition-colors"
          >
            <Pin className="w-3 h-3" />
            Pin Artifact
          </button>
        )}
      </div>
    </div>
  );
}
