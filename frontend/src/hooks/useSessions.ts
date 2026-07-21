"use client";

import { useState, useCallback, useEffect } from "react";
import { SessionSummary } from "../lib/types";
import { fetchSessions, deleteSession as apiDeleteSession } from "../lib/api";

export function useSessions() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshSessions = useCallback(async () => {
    setLoading(true);
    const list = await fetchSessions();
    setSessions(list);
    setLoading(false);
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  const removeSession = useCallback(
    async (id: string) => {
      const success = await apiDeleteSession(id);
      if (success) {
        setSessions((prev) => prev.filter((s) => s.id !== id));
      }
      return success;
    },
    []
  );

  return {
    sessions,
    loading,
    refreshSessions,
    removeSession,
  };
}
