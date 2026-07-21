"use client";

import React from "react";
import { Languages, Cpu, LogOut } from "lucide-react";
import { ModelProfile, UiPrefs } from "../lib/auth";
import { cn } from "../lib/utils";

interface ChatToolbarProps {
  prefs: UiPrefs;
  onLanguageChange: (lang: "vi" | "en") => void;
  onModelChange: (profile: ModelProfile, localPreset?: "ollama" | "vllm") => void;
  userEmail?: string;
  onLogout: () => void;
  onToggleArtifact?: () => void;
  artifactOpen?: boolean;
}

export function ChatToolbar({
  prefs,
  onLanguageChange,
  onModelChange,
  userEmail,
  onLogout,
  onToggleArtifact,
  artifactOpen,
}: ChatToolbarProps) {
  const en = prefs.language === "en";

  return (
    <header className="flex items-center justify-between gap-3 px-4 py-2 border-b border-slate-800/60 bg-slate-950/40 backdrop-blur-md shrink-0 z-10">
      <div className="flex items-center gap-2 flex-wrap min-w-0">
        <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-900/60 p-0.5">
          <button
            type="button"
            onClick={() => onLanguageChange("vi")}
            className={cn(
              "px-2 py-1 text-[11px] font-semibold rounded-md transition-colors",
              prefs.language === "vi"
                ? "bg-emerald-600/30 text-emerald-200"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            VN
          </button>
          <button
            type="button"
            onClick={() => onLanguageChange("en")}
            className={cn(
              "px-2 py-1 text-[11px] font-semibold rounded-md transition-colors",
              prefs.language === "en"
                ? "bg-emerald-600/30 text-emerald-200"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            EN
          </button>
        </div>

        <div className="flex items-center gap-1.5 text-slate-500">
          <Cpu className="w-3.5 h-3.5" />
          <select
            value={prefs.modelProfile}
            onChange={(e) => onModelChange(e.target.value as ModelProfile)}
            className="text-[11px] bg-slate-900 border border-slate-800 rounded-md px-2 py-1 text-slate-200 focus:outline-none focus:border-emerald-500/50"
            title={en ? "Model profile" : "Hồ sơ model"}
          >
            <option value="gemini">Gemini</option>
            <option value="openai">OpenAI-compat</option>
            <option value="local">Local (Ollama/vLLM)</option>
          </select>
          {prefs.modelProfile === "local" && (
            <select
              value={prefs.localPreset || "ollama"}
              onChange={(e) =>
                onModelChange("local", e.target.value as "ollama" | "vllm")
              }
              className="text-[11px] bg-slate-900 border border-slate-800 rounded-md px-2 py-1 text-slate-200 focus:outline-none"
            >
              <option value="ollama">Ollama :11434</option>
              <option value="vllm">vLLM :8000</option>
            </select>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {onToggleArtifact && (
          <button
            type="button"
            onClick={onToggleArtifact}
            className={cn(
              "text-[11px] px-2 py-1 rounded-md border transition-colors",
              artifactOpen
                ? "border-emerald-500/40 text-emerald-300 bg-emerald-500/10"
                : "border-slate-800 text-slate-400 hover:text-slate-200"
            )}
          >
            {en ? "Artifacts" : "Artifacts"}
          </button>
        )}
        {userEmail && (
          <span className="hidden sm:inline text-[11px] text-slate-500 truncate max-w-[140px]">
            {userEmail}
          </span>
        )}
        <button
          type="button"
          onClick={onLogout}
          className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-rose-300 px-2 py-1 rounded-md hover:bg-slate-800/80"
          title={en ? "Logout" : "Đăng xuất"}
        >
          <LogOut className="w-3.5 h-3.5" />
          <Languages className="w-3 h-3 opacity-0 absolute" />
          {en ? "Logout" : "Thoát"}
        </button>
      </div>
    </header>
  );
}
