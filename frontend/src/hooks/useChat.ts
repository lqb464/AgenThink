"use client";

import { useState, useCallback, useRef } from "react";
import { Message, ToolCallData } from "../lib/types";
import { fetchSessionMessages } from "../lib/api";
import { getAccessToken, getUiPrefs } from "../lib/auth";

function clearAssistantStreaming(messages: Message[], assistantMsgId: string): Message[] {
  return messages.map((m) =>
    m.id === assistantMsgId ? { ...m, isStreaming: false } : m
  );
}

function extractToolName(toolCalls: unknown): string | null {
  if (!Array.isArray(toolCalls) || toolCalls.length === 0) return null;
  const first = toolCalls[0] as { function?: { name?: string }; name?: string };
  return first?.function?.name || first?.name || null;
}

/** Collapse DB transcript (assistant tool_calls + tool roles) into UI bubbles. */
export function hydrateMessagesForUi(raw: Message[]): Message[] {
  const out: Message[] = [];
  let pendingTools: ToolCallData[] = [];

  for (let i = 0; i < raw.length; i++) {
    const msg = raw[i];
    const id = msg.id || `${msg.role}-${i}`;

    if (msg.role === "user") {
      if (pendingTools.length) {
        out.push({
          id: `tools-${id}`,
          role: "assistant",
          content: "",
          toolResults: pendingTools,
        });
        pendingTools = [];
      }
      out.push({ ...msg, id });
      continue;
    }

    if (msg.role === "assistant" && msg.tool_calls?.length) {
      const name = extractToolName(msg.tool_calls) || "tool";
      let args: Record<string, unknown> | undefined;
      try {
        const rawArgs = (msg.tool_calls[0] as { function?: { arguments?: string } })
          ?.function?.arguments;
        args = typeof rawArgs === "string" ? JSON.parse(rawArgs) : (rawArgs as object);
      } catch {
        args = undefined;
      }
      // Peek next tool result
      const next = raw[i + 1];
      if (next && next.role === "tool") {
        const text =
          typeof next.content === "string"
            ? next.content
            : JSON.stringify(next.content ?? "");
        pendingTools.push({
          tool: name,
          arguments: args,
          success: !text.startsWith("[Tool Error"),
          text: text.slice(0, 500),
        });
        i += 1; // skip tool message
      } else {
        pendingTools.push({ tool: name, arguments: args, success: true });
      }
      continue;
    }

    if (msg.role === "tool") {
      // Orphan tool row
      pendingTools.push({
        tool: "tool",
        success: true,
        text: typeof msg.content === "string" ? msg.content.slice(0, 500) : "",
      });
      continue;
    }

    if (msg.role === "assistant") {
      const content =
        typeof msg.content === "string"
          ? msg.content
          : Array.isArray(msg.content)
            ? msg.content
            : msg.content ?? "";
      // Skip empty assistant placeholders
      if (
        (content === "" || content === null) &&
        !pendingTools.length &&
        !msg.tool_calls?.length
      ) {
        continue;
      }
      out.push({
        ...msg,
        id,
        content: content as Message["content"],
        toolResults: pendingTools.length ? pendingTools : msg.toolResults,
      });
      pendingTools = [];
      continue;
    }

    out.push({ ...msg, id });
  }

  if (pendingTools.length) {
    out.push({
      id: `tools-trailing`,
      role: "assistant",
      content: "",
      toolResults: pendingTools,
    });
  }

  return out;
}

function parseToolStart(parsed: unknown): { tool: string; arguments?: Record<string, unknown> } {
  if (typeof parsed === "string") {
    try {
      const obj = JSON.parse(parsed);
      if (obj && typeof obj === "object" && "tool" in obj) {
        return {
          tool: String((obj as { tool: string }).tool),
          arguments: (obj as { arguments?: Record<string, unknown> }).arguments,
        };
      }
    } catch {
      return { tool: parsed };
    }
    return { tool: parsed };
  }
  if (parsed && typeof parsed === "object" && "tool" in parsed) {
    return {
      tool: String((parsed as { tool: string }).tool),
      arguments: (parsed as { arguments?: Record<string, unknown> }).arguments,
    };
  }
  return { tool: "unknown_tool" };
}

export function useChat(initialSessionId: string = "") {
  const [sessionId, setSessionId] = useState<string>(initialSessionId);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [toolHistory, setToolHistory] = useState<ToolCallData[]>([]);

  const abortControllerRef = useRef<AbortController | null>(null);
  const assistantIdRef = useRef<string | null>(null);

  const loadSession = useCallback(async (sid: string) => {
    setSessionId(sid);
    if (!sid) {
      setMessages([]);
      return;
    }
    const msgs = await fetchSessionMessages(sid);
    setMessages(hydrateMessagesForUi(msgs));
  }, []);

  const sendMessage = useCallback(
    async (text: string, files: File[] = []) => {
      if (!text.trim() && files.length === 0) return;
      if (isStreaming) return;

      setIsStreaming(true);
      setActiveTool(null);
      setToolHistory([]);

      const fileUrls: string[] = [];
      for (const file of files) {
        const reader = new FileReader();
        const url = await new Promise<string>((resolve) => {
          reader.onload = () => resolve(reader.result as string);
          reader.readAsDataURL(file);
        });
        fileUrls.push(url);
      }

      const userMsgId = `user-${Date.now()}`;
      const assistantMsgId = `assistant-${Date.now()}`;
      assistantIdRef.current = assistantMsgId;

      setMessages((prev) => [
        ...prev,
        {
          id: userMsgId,
          role: "user",
          content: text,
          images: fileUrls.length > 0 ? fileUrls : undefined,
        },
        {
          id: assistantMsgId,
          role: "assistant",
          content: "",
          isStreaming: true,
          activeTools: [],
          toolResults: [],
          planSteps: [],
        },
      ]);

      const formData = new FormData();
      formData.append("message", text);
      if (sessionId) {
        formData.append("session_id", sessionId);
      }
      const prefs = getUiPrefs();
      formData.append("language", prefs.language);
      formData.append(
        "llm_provider",
        prefs.modelProfile === "local" ? "local" : prefs.modelProfile
      );
      if (prefs.modelProfile === "local") {
        const base =
          prefs.localPreset === "vllm"
            ? "http://127.0.0.1:8000/v1"
            : "http://127.0.0.1:11434/v1";
        formData.append("openai_base_url", base);
        if (prefs.localModel) formData.append("llm_model", prefs.localModel);
      }
      files.forEach((file) => {
        formData.append("files", file);
      });

      abortControllerRef.current = new AbortController();

      try {
        const headers: HeadersInit = {};
        const token = getAccessToken();
        if (token) headers.Authorization = `Bearer ${token}`;

        const res = await fetch("/api/chat/stream", {
          method: "POST",
          body: formData,
          headers,
          signal: abortControllerRef.current.signal,
        });

        if (res.status === 401) {
          throw new Error("Unauthorized — please sign in again");
        }

        if (!res.ok || !res.body) {
          throw new Error(`Server returned error: ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let currentAssistantText = "";
        const runningTools: string[] = [];
        const completedTools: ToolCallData[] = [];
        let planSteps: string[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            const lines = part.split("\n").map((l) => l.trim());
            let eventType = "message";
            let dataStr = "";

            for (const line of lines) {
              if (line.startsWith("event: ")) {
                eventType = line.replace("event: ", "").trim();
              } else if (line.startsWith("data: ")) {
                dataStr = line.replace("data: ", "").trim();
              }
            }

            if (!dataStr) continue;

            let parsedContent: unknown = "";
            try {
              const json = JSON.parse(dataStr);
              parsedContent =
                json && typeof json === "object" && "content" in json
                  ? (json as { content: unknown }).content
                  : json;
            } catch {
              parsedContent = dataStr;
            }

            if (eventType === "session") {
              const sid =
                parsedContent &&
                typeof parsedContent === "object" &&
                "session_id" in parsedContent
                  ? String((parsedContent as { session_id: string }).session_id)
                  : "";
              if (sid) setSessionId(sid);
            } else if (eventType === "plan") {
              try {
                const planData =
                  typeof parsedContent === "string"
                    ? JSON.parse(parsedContent)
                    : parsedContent;
                planSteps = Array.isArray((planData as { steps?: string[] })?.steps)
                  ? (planData as { steps: string[] }).steps
                  : [];
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId ? { ...m, planSteps: [...planSteps] } : m
                  )
                );
              } catch {
                // ignore
              }
            } else if (eventType === "reflect") {
              try {
                const reflectData =
                  typeof parsedContent === "string"
                    ? JSON.parse(parsedContent)
                    : parsedContent;
                const status = String(
                  (reflectData as { status?: string })?.status || "reflect"
                );
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId ? { ...m, reflectStatus: status } : m
                  )
                );
              } catch {
                // ignore
              }
            } else if (eventType === "tool_start") {
              const { tool: toolName } = parseToolStart(parsedContent);
              setActiveTool(toolName);
              if (!runningTools.includes(toolName)) {
                runningTools.push(toolName);
              }
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, activeTools: [...runningTools] }
                    : m
                )
              );
            } else if (eventType === "tool_result") {
              setActiveTool(null);
              try {
                const toolData: ToolCallData =
                  typeof parsedContent === "string"
                    ? JSON.parse(parsedContent)
                    : (parsedContent as ToolCallData);
                completedTools.push(toolData);
                const citations = completedTools.flatMap((t) => t.sources || []);
                setToolHistory((prev) => [...prev, toolData]);
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId
                      ? {
                          ...m,
                          toolResults: [...completedTools],
                          activeTools: [...runningTools],
                          citations: citations.length ? [...citations] : undefined,
                        }
                      : m
                  )
                );
              } catch {
                // ignore parse errors
              }
            } else if (eventType === "text") {
              const chunk = typeof parsedContent === "string" ? parsedContent : "";
              currentAssistantText += chunk;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        content: currentAssistantText,
                        activeTools: [...runningTools],
                        toolResults: [...completedTools],
                        planSteps: [...planSteps],
                        isStreaming: true,
                      }
                    : m
                )
              );
            } else if (eventType === "error") {
              currentAssistantText += `\n⚠️ [Lỗi]: ${
                typeof parsedContent === "string" ? parsedContent : "Lỗi không xác định"
              }`;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        content: currentAssistantText,
                        isStreaming: false,
                      }
                    : m
                )
              );
            } else if (eventType === "done") {
              setMessages((prev) => clearAssistantStreaming(prev, assistantMsgId));
              setIsStreaming(false);
              setActiveTool(null);
            }
          }
        }
      } catch (err: unknown) {
        const error = err as { name?: string; message?: string };
        if (error.name !== "AbortError") {
          console.error("Stream fetch failed:", err);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    content: `⚠️ Không thể kết nối đến máy chủ: ${error.message || "Unknown error"}`,
                    isStreaming: false,
                  }
                : m
            )
          );
        }
      } finally {
        setMessages((prev) => clearAssistantStreaming(prev, assistantMsgId));
        setIsStreaming(false);
        setActiveTool(null);
        assistantIdRef.current = null;
      }
    },
    [isStreaming, sessionId]
  );

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      const aid = assistantIdRef.current;
      if (aid) {
        setMessages((prev) => clearAssistantStreaming(prev, aid));
      }
      setIsStreaming(false);
      setActiveTool(null);
    }
  }, []);

  return {
    sessionId,
    setSessionId,
    messages,
    isStreaming,
    activeTool,
    toolHistory,
    sendMessage,
    stopStreaming,
    loadSession,
  };
}
