import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from "react";
import apiClient from "../api/client";

interface SessionState {
  sessionId: string | null;
  status: string;
  initialIdea: string | null;
  createSession: (initialIdea: string) => Promise<{ session_id: string; status: string }>;
  resetSession: () => void;
  switchSession: (sessionId: string) => Promise<string>;
}

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(() => {
    return localStorage.getItem("idstorm_session_id");
  });
  const [status, setStatus] = useState<string>("dialogue");
  const [initialIdea, setInitialIdea] = useState<string | null>(null);
  const mounted = useRef(false);

  useEffect(() => {
    if (mounted.current) return;
    mounted.current = true;

    const sid = localStorage.getItem("idstorm_session_id");
    if (!sid) return;

    apiClient.get(`/session/${sid}/state`).then((res) => {
      setSessionId(res.data.session_id);
      setStatus(res.data.status);
      setInitialIdea(res.data.initial_idea || null);
    }).catch(() => {
      setSessionId(null);
      localStorage.removeItem("idstorm_session_id");
    });
  }, []);

  const createSession = useCallback(async (idea: string) => {
    const res = await apiClient.post("/session", { initial_idea: idea });
    const data = res.data;
    setSessionId(data.session_id);
    setStatus(data.status);
    setInitialIdea(idea);
    localStorage.setItem("idstorm_session_id", data.session_id);
    return data;
  }, []);

  const resetSession = useCallback(() => {
    setSessionId(null);
    setStatus("dialogue");
    setInitialIdea(null);
    localStorage.removeItem("idstorm_session_id");
  }, []);

  const switchSession = useCallback(async (sid: string): Promise<string> => {
    const res = await apiClient.get(`/session/${sid}/state`);
    const newStatus = res.data.status;
    setSessionId(res.data.session_id);
    setStatus(newStatus);
    setInitialIdea(res.data.initial_idea || null);
    localStorage.setItem("idstorm_session_id", sid);
    return newStatus;
  }, []);

  return (
    <SessionContext.Provider value={{ sessionId, status, initialIdea, createSession, resetSession, switchSession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionState {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
