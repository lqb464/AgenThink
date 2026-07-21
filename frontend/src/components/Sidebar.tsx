"use client";

import React, { useState } from "react";
import {
  MessageSquare,
  Plus,
  Trash2,
  BrainCircuit,
  ChevronLeft,
  ChevronRight,
  Server,
} from "lucide-react";
import { SessionSummary, HealthResponse } from "../lib/types";
import { cn } from "../lib/utils";
import { KnowledgePanel } from "./KnowledgePanel";

interface SidebarProps {
  sessions: SessionSummary[];
  activeSessionId: string;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  health: HealthResponse | null;
  onSourceFilterChange?: (files: string[]) => void;
}

export function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  health,
  onSourceFilterChange,
}: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const servicesList = [
    { key: "core", name: "AgenThink Core", status: health?.status === "ok" },
    { key: "rag", name: "Tri thức (Local RAG)", status: health?.services?.rag ?? true },
    { key: "docread", name: "OCR (Gemini vision)", status: health?.services?.docread ?? true },
  ];

  return (
    <aside
      className={cn(
        "flex flex-col h-screen border-r border-slate-800/80 bg-slate-950/90 backdrop-blur-xl transition-all duration-300 z-30 select-none relative",
        isCollapsed ? "w-16" : "w-72 sm:w-80"
      )}
    >
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-6 w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-slate-300 flex items-center justify-center hover:bg-cyan-500 hover:text-white transition-colors z-40 shadow-lg"
        title={isCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
      >
        {isCollapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
      </button>

      <div className="p-4 border-b border-slate-800/80 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 shrink-0">
          <BrainCircuit className="w-5 h-5 text-white animate-pulse" />
        </div>
        {!isCollapsed && (
          <div className="flex flex-col overflow-hidden">
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-emerald-300 via-teal-200 to-cyan-300 bg-clip-text text-transparent truncate">
              AgenThink
            </span>
          </div>
        )}
      </div>

      <div className="p-3">
        <button
          onClick={onNewChat}
          className={cn(
            "w-full flex items-center justify-center gap-2.5 py-2.5 px-3 rounded-xl font-medium text-sm transition-all shadow-md group border border-emerald-500/30 bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-cyan-500/10 hover:from-emerald-500 hover:via-teal-600 hover:to-cyan-600 hover:text-white hover:border-transparent text-emerald-300",
            isCollapsed && "px-0 py-2.5"
          )}
          title="Cuộc trò chuyện mới"
        >
          <Plus className="w-4 h-4 transition-transform group-hover:rotate-90" />
          {!isCollapsed && <span>Cuộc trò chuyện mới</span>}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent min-h-0">
        {!isCollapsed && sessions.length === 0 && (
          <div className="text-center py-10 px-4 text-xs text-slate-500">
            Chưa có lịch sử trò chuyện. Hãy bắt đầu một cuộc hội thoại mới!
          </div>
        )}

        {sessions.map((session) => {
          const isActive = session.id === activeSessionId;
          return (
            <div
              key={session.id}
              onClick={() => onSelectSession(session.id)}
              className={cn(
                "group flex items-center justify-between p-2.5 rounded-xl cursor-pointer text-sm transition-all duration-200 border",
                isActive
                  ? "bg-slate-800/90 text-cyan-300 border-slate-700/80 shadow-md shadow-black/30 font-medium"
                  : "text-slate-400 hover:bg-slate-900/80 hover:text-slate-200 border-transparent"
              )}
              title={session.title || "Cuộc trò chuyện"}
            >
              <div className="flex items-center gap-2.5 overflow-hidden flex-1">
                <MessageSquare
                  className={cn(
                    "w-4 h-4 shrink-0 transition-colors",
                    isActive ? "text-cyan-400" : "text-slate-500 group-hover:text-slate-400"
                  )}
                />
                {!isCollapsed && (
                  <span className="truncate flex-1 text-xs sm:text-sm tracking-tight">
                    {session.title || "Cuộc trò chuyện không tên"}
                  </span>
                )}
              </div>

              {!isCollapsed && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm("Bạn có chắc chắn muốn xóa cuộc trò chuyện này?")) {
                      onDeleteSession(session.id);
                    }
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-red-500/20 hover:text-red-400 text-slate-500 transition-all shrink-0 ml-1"
                  title="Xóa cuộc trò chuyện"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      <KnowledgePanel
        collapsed={isCollapsed}
        onFilterChange={onSourceFilterChange}
      />

      <div className="p-3 border-t border-slate-800/80 bg-slate-950/60">
        {!isCollapsed ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <Server className="w-3 h-3 text-blue-400" /> Hệ sinh thái AI
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                {health?.llm_provider || "gemini"}
              </span>
            </div>
            <div className="space-y-1 pt-1">
              {servicesList.map((srv) => (
                <div
                  key={srv.key}
                  className="flex items-center justify-between text-xs py-1 px-2 rounded-lg bg-slate-900/50 border border-slate-800/50"
                >
                  <span className="text-slate-300 truncate font-medium text-[11px]">{srv.name}</span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="relative flex h-2 w-2">
                      {srv.status && (
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      )}
                      <span
                        className={cn(
                          "relative inline-flex rounded-full h-2 w-2",
                          srv.status ? "bg-emerald-500" : "bg-red-500"
                        )}
                      ></span>
                    </span>
                    <span className={cn("text-[10px] font-semibold", srv.status ? "text-emerald-400" : "text-red-400")}>
                      {srv.status ? "Online" : "Offline"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 py-1">
            <span title="Trạng thái hệ sinh thái">
              <Server className="w-4 h-4 text-blue-400" />
            </span>
            <div className="flex flex-col gap-1.5 items-center">
              {servicesList.map((srv) => (
                <div
                  key={srv.key}
                  className={cn("w-2 h-2 rounded-full", srv.status ? "bg-emerald-500" : "bg-red-500")}
                  title={`${srv.name}: ${srv.status ? "Online" : "Offline"}`}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
