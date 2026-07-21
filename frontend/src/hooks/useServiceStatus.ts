"use client";

import { useState, useEffect } from "react";
import { fetchHealth } from "../lib/api";
import { HealthResponse } from "../lib/types";

export function useServiceStatus(pollIntervalMs: number = 15000) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;

    async function checkHealth() {
      const data = await fetchHealth();
      if (isMounted) {
        setHealth(data);
        setLoading(false);
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, pollIntervalMs);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [pollIntervalMs]);

  return { health, loading };
}
