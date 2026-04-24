import { useState, useCallback } from "react";
import apiClient from "../api/client";

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(() => {
    return localStorage.getItem("idstorm_session_id");
  });
  const [status, setStatus] = useState<string>("dialogue");

  const createSession = useCallback(async (initialIdea: string) => {
    const res = await apiClient.post("/session", { initial_idea: initialIdea });
    const data = res.data;
    setSessionId(data.session_id);
    setStatus(data.status);
    localStorage.setItem("idstorm_session_id", data.session_id);
    return data;
  }, []);

  const resetSession = useCallback(() => {
    setSessionId(null);
    setStatus("dialogue");
    localStorage.removeItem("idstorm_session_id");
  }, []);

  return { sessionId, status, setStatus, createSession, resetSession };
}
