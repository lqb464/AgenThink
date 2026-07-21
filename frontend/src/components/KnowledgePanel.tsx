import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  BookOpen,
  FileText,
  Loader2,
  Plus,
  Trash2,
  Upload,
} from "lucide-react";
import {
  deleteDocSource,
  ensureDocsProject,
  fetchDocsStatus,
  getStoredProjectId,
  getStoredSourceFilter,
  setStoredSourceFilter,
  uploadDocs,
} from "../lib/api";
import { cn } from "../lib/utils";

interface KnowledgePanelProps {
  collapsed?: boolean;
  /** Called when source filter changes (for chat hint) */
  onFilterChange?: (files: string[]) => void;
  onProjectChange?: (projectId: string) => void;
}

export function KnowledgePanel({
  collapsed = false,
  onFilterChange,
  onProjectChange,
}: KnowledgePanelProps) {
  const [online, setOnline] = useState(false);
  const [projectId, setProjectId] = useState("");
  const [defaultId, setDefaultId] = useState("agentthink_default");
  const [sources, setSources] = useState<string[]>([]);
  const [filter, setFilter] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async (pid?: string) => {
    const status = await fetchDocsStatus(pid || projectId || undefined);
    if (!status) {
      setOnline(false);
      setStatusMsg("API offline");
      return;
    }
    setOnline(status.online);
    setDefaultId(status.default_project_id || "agentthink_default");
    const active = status.project_id || status.default_project_id;
    setProjectId(active);
    const src = status.project?.sources || [];
    setSources(src);
    if (!status.online) {
      setStatusMsg(status.error || "Tri thức tạm khóa");
    } else if (status.project?.exists === false) {
      setStatusMsg("Chưa có tài liệu — upload để tạo index");
    } else {
      setStatusMsg(
        src.length
          ? `${src.length} nguồn · ${status.project?.stats?.chunks ?? 0} chunks`
          : "Chưa có tài liệu"
      );
    }
  }, [projectId]);

  useEffect(() => {
    const stored = getStoredProjectId();
    const storedFilter = getStoredSourceFilter();
    setFilter(storedFilter);
    onFilterChange?.(storedFilter);
    (async () => {
      await refresh(stored || undefined);
      if (stored) onProjectChange?.(stored);
    })();
    const t = setInterval(() => refresh(), 20000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onUpload = async (files: FileList | null) => {
    if (!files?.length) return;
    const allowed = Array.from(files).filter((f) => {
      const n = f.name.toLowerCase();
      return n.endsWith(".pdf") || n.endsWith(".docx") || n.endsWith(".md") || n.endsWith(".txt");
    });
    if (!allowed.length) {
      setStatusMsg("Chỉ hỗ trợ PDF / DOCX / MD / TXT");
      return;
    }
    setBusy(true);
    setStatusMsg("Đang upload & index…");
    const res = await uploadDocs(allowed, projectId || defaultId);
    setBusy(false);
    if (res?.error) {
      setStatusMsg(res.error);
      return;
    }
    setStatusMsg(`Đã thêm: ${(res?.added || []).join(", ") || "không đổi"}`);
    await refresh(projectId || defaultId);
  };

  const onDelete = async (filename: string) => {
    if (!confirm(`Xóa nguồn "${filename}"?`)) return;
    setBusy(true);
    const res = await deleteDocSource(filename, projectId);
    setBusy(false);
    if (res?.error) {
      setStatusMsg(res.error);
      return;
    }
    const nextFilter = filter.filter((f) => f !== filename);
    setFilter(nextFilter);
    setStoredSourceFilter(nextFilter);
    onFilterChange?.(nextFilter);
    await refresh(projectId);
  };

  const toggleFilter = (filename: string) => {
    const next = filter.includes(filename)
      ? filter.filter((f) => f !== filename)
      : [...filter, filename];
    setFilter(next);
    setStoredSourceFilter(next);
    onFilterChange?.(next);
  };

  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2 py-2" title="Tri thức / Tài liệu">
        <BookOpen className={cn("w-4 h-4", online ? "text-emerald-400" : "text-slate-500")} />
        <span
          className={cn(
            "w-2 h-2 rounded-full",
            online ? "bg-emerald-500" : "bg-red-500"
          )}
        />
      </div>
    );
  }

  return (
    <div className="px-3 pb-2 border-t border-slate-800/80 pt-3 space-y-2">
      <div className="flex items-center justify-between text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
        <span className="flex items-center gap-1.5">
          <BookOpen className="w-3 h-3 text-emerald-400" /> Tri thức
        </span>
        <span
          className={cn(
            "text-[10px] px-1.5 py-0.5 rounded",
            online ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"
          )}
        >
          {online ? "Local RAG" : "Offline"}
        </span>
      </div>

      <div className="flex gap-1.5 items-center">
        <div
          className="flex-1 min-w-0 text-[11px] px-2 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 truncate font-mono"
          title="Per-user RAG project (JWT-locked)"
        >
          {projectId || defaultId || "…"}
        </div>
        <button
          type="button"
          onClick={async () => {
            setBusy(true);
            await ensureDocsProject(projectId || defaultId);
            setBusy(false);
            await refresh(projectId || defaultId);
          }}
          disabled={busy || !online}
          className="shrink-0 px-2 py-1.5 rounded-lg border border-slate-700 text-[11px] text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50"
          title="Đảm bảo project tồn tại trên đĩa"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.docx,.md,.txt,application/pdf"
        multiple
        className="hidden"
        onChange={(e) => {
          onUpload(e.target.files);
          e.target.value = "";
        }}
      />

      <button
        type="button"
        disabled={busy || !online}
        onClick={() => fileRef.current?.click()}
        className="w-full flex items-center justify-center gap-2 py-2 px-2 rounded-xl text-xs font-medium border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-40 transition-colors"
      >
        {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
        Upload PDF / DOCX / MD
      </button>

      <p className="text-[10px] text-slate-500 leading-snug px-0.5">{statusMsg}</p>

      {sources.length > 0 && (
        <div className="max-h-36 overflow-y-auto space-y-1 pr-0.5">
          {sources.map((src) => {
            const active = filter.length === 0 || filter.includes(src);
            return (
              <div
                key={src}
                className={cn(
                  "flex items-start gap-1.5 px-2 py-1.5 rounded-lg border text-[11px]",
                  active
                    ? "bg-slate-900/80 border-slate-800 text-slate-200"
                    : "bg-slate-950/40 border-transparent text-slate-500"
                )}
              >
                <button
                  type="button"
                  onClick={() => toggleFilter(src)}
                  className="mt-0.5 shrink-0"
                  title={
                    filter.length === 0
                      ? "Bật lọc theo nguồn (click để chọn)"
                      : filter.includes(src)
                        ? "Bỏ khỏi bộ lọc"
                        : "Thêm vào bộ lọc"
                  }
                >
                  <FileText
                    className={cn(
                      "w-3 h-3",
                      filter.includes(src) ? "text-emerald-400" : "text-slate-500"
                    )}
                  />
                </button>
                <span className="flex-1 truncate" title={src}>
                  {src}
                </span>
                <button
                  type="button"
                  onClick={() => onDelete(src)}
                  className="shrink-0 p-0.5 text-slate-600 hover:text-red-400"
                  title="Xóa nguồn"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {filter.length > 0 && (
        <button
          type="button"
          onClick={() => {
            setFilter([]);
            setStoredSourceFilter([]);
            onFilterChange?.([]);
          }}
          className="text-[10px] text-amber-400/90 hover:text-amber-300"
        >
          Xóa bộ lọc ({filter.length} file)
        </button>
      )}
    </div>
  );
}
