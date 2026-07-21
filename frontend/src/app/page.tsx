"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Sidebar } from "../components/Sidebar";
import { ChatArea } from "../components/ChatArea";
import { InputBar } from "../components/InputBar";
import { AuthScreen } from "../components/AuthScreen";
import { ChatToolbar } from "../components/ChatToolbar";
import { ArtifactsPanel, Artifact, detectArtifactFromText } from "../components/ArtifactsPanel";
import { useChat } from "../hooks/useChat";
import { useSessions } from "../hooks/useSessions";
import { useServiceStatus } from "../hooks/useServiceStatus";
import { fetchMe } from "../lib/api";
import {
  AuthUser,
  clearAuthSession,
  getAccessToken,
  getStoredUser,
  getUiPrefs,
  ModelProfile,
  setLanguage,
  setModelProfile,
  UiPrefs,
} from "../lib/auth";

export default function HomePage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [prefs, setPrefs] = useState<UiPrefs>({ language: "vi", modelProfile: "gemini" });
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [artifactOpen, setArtifactOpen] = useState(false);

  const { sessions, refreshSessions, removeSession } = useSessions();
  const { health } = useServiceStatus(15000);
  const sourceFilterRef = useRef<string[]>([]);
  const {
    sessionId,
    messages,
    isStreaming,
    sendMessage,
    stopStreaming,
    loadSession,
  } = useChat("");

  useEffect(() => {
    setPrefs(getUiPrefs());
    const token = getAccessToken();
    const stored = getStoredUser();
    if (!token) {
      setAuthReady(true);
      return;
    }
    fetchMe()
      .then((me) => {
        if (me && me.id && me.id !== "anonymous") {
          setUser({
            id: me.id,
            email: me.email,
            rag_project_id: me.rag_project_id,
          });
        } else if (stored) {
          setUser(stored);
        }
      })
      .finally(() => setAuthReady(true));
  }, []);

  useEffect(() => {
    if (!isStreaming && messages.length > 0) {
      refreshSessions();
    }
  }, [isStreaming, messages.length, refreshSessions]);

  // Auto-open artifact for long report tool outputs
  useEffect(() => {
    if (isStreaming) return;
    const last = [...messages].reverse().find((m) => m.role === "assistant");
    if (!last?.toolResults?.length) return;
    const report = last.toolResults.find(
      (t) =>
        (t.tool === "generate_document_report" || t.tool === "summarize_documents") &&
        (t.text?.length || 0) > 400
    );
    if (report?.text) {
      const art = detectArtifactFromText(report.text, report.tool);
      if (art) {
        setArtifact(art);
        setArtifactOpen(true);
      }
    }
  }, [isStreaming, messages]);

  const handleSelectSession = (id: string) => {
    if (id === sessionId) return;
    loadSession(id);
  };

  const handleNewChat = () => {
    loadSession("");
  };

  const handleDeleteSession = async (id: string) => {
    const success = await removeSession(id);
    if (success && id === sessionId) {
      loadSession("");
    }
  };

  const withSourceHint = useCallback((promptText: string) => {
    const filter = sourceFilterRef.current;
    if (!filter.length) return promptText;
    return (
      `${promptText}\n\n` +
      `(Gợi ý RAG: khi gọi search_documents hãy dùng allowed_sources = ` +
      `${JSON.stringify(filter)}.)`
    );
  }, []);

  const handleSuggestionClick = (promptText: string) => {
    sendMessage(withSourceHint(promptText), []);
  };

  const handleSend = useCallback(
    (text: string, files: File[] = []) => {
      sendMessage(withSourceHint(text), files);
    },
    [sendMessage, withSourceHint]
  );

  const handleLogout = () => {
    clearAuthSession();
    setUser(null);
    loadSession("");
  };

  if (!authReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#060a12] text-slate-400 text-sm">
        Loading…
      </div>
    );
  }

  const needsAuth = health?.auth_required !== false;
  if (!user && needsAuth) {
    return (
      <AuthScreen
        language={prefs.language}
        onAuthenticated={(u) => {
          setUser(u);
          refreshSessions();
        }}
      />
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#060a12] font-sans text-slate-100">
      <Sidebar
        sessions={sessions}
        activeSessionId={sessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        health={health}
        onSourceFilterChange={(files) => {
          sourceFilterRef.current = files;
        }}
      />

      <main className="flex-1 flex flex-col h-full overflow-hidden relative min-w-0">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/8 rounded-full blur-3xl pointer-events-none -z-10" />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-teal-500/8 rounded-full blur-3xl pointer-events-none -z-10" />

        <ChatToolbar
          prefs={prefs}
          userEmail={user?.email}
          artifactOpen={artifactOpen}
          onToggleArtifact={() => setArtifactOpen((v) => !v)}
          onLogout={handleLogout}
          onLanguageChange={(lang) => {
            setLanguage(lang);
            setPrefs((p) => ({ ...p, language: lang }));
          }}
          onModelChange={(profile: ModelProfile, localPreset) => {
            setModelProfile({ modelProfile: profile, localPreset });
            setPrefs((p) => ({
              ...p,
              modelProfile: profile,
              localPreset: localPreset || p.localPreset,
            }));
          }}
        />

        <div className="flex-1 flex min-h-0 overflow-hidden">
          <div className="flex-1 flex flex-col min-w-0">
            <ChatArea
              messages={messages}
              onSuggestionClick={handleSuggestionClick}
              isStreaming={isStreaming}
              language={prefs.language}
              onPinArtifact={(art) => {
                setArtifact(art);
                setArtifactOpen(true);
              }}
            />

            <InputBar
              onSendMessage={handleSend}
              onStopStreaming={stopStreaming}
              isStreaming={isStreaming}
            />
          </div>

          <ArtifactsPanel
            open={artifactOpen}
            artifact={artifact}
            onClose={() => setArtifactOpen(false)}
            language={prefs.language}
          />
        </div>
      </main>
    </div>
  );
}
