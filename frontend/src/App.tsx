import { useState, useEffect, useCallback } from "react";
import { STEPS } from "./utils/constants";
import { useSession } from "./hooks/useSession";
import DialoguePage from "./components/dialogue/DialoguePage";
import RequirementPage from "./components/requirement/RequirementPage";
import CandidatePage from "./components/candidate/CandidatePage";
import apiClient from "./api/client";
import "./index.css";

interface SessionInfo {
  session_id: string;
  initial_idea: string;
  status: string;
  created_at: string;
}

function statusToStep(status: string): number {
  switch (status) {
    case "dialogue": return 1;
    case "requirement": return 2;
    case "generating":
    case "review": return 3;
    default: return 1;
  }
}

function App() {
  const { sessionId, status, resetSession, switchSession } = useSession();
  const [currentStep, setCurrentStep] = useState(() => statusToStep(status));
  const [designKey, setDesignKey] = useState(0);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);

  useEffect(() => {
    setCurrentStep(statusToStep(status));
  }, [status]);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await apiClient.get("/sessions");
      setSessions(res.data.sessions);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions, sessionId]);

  const handleNewDesign = () => {
    resetSession();
    setCurrentStep(1);
    setDesignKey(prev => prev + 1);
  };

  const handleSwitchSession = async (sid: string) => {
    await switchSession(sid);
    setDesignKey(prev => prev + 1);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-gray-200 bg-white">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h1 className="text-sm font-bold text-gray-800">IDStorm</h1>
          <button
            onClick={handleNewDesign}
            className="rounded-md bg-blue-600 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-blue-700"
          >
            + 新建
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {sessions.length === 0 ? (
            <div className="px-4 py-8 text-center text-xs text-gray-400">
              暂无会话，点击上方新建
            </div>
          ) : (
            <ul>
              {sessions.map((s) => (
                <li key={s.session_id}>
                  <button
                    onClick={() => handleSwitchSession(s.session_id)}
                    className={`w-full text-left px-4 py-3 transition-colors hover:bg-gray-50 border-b border-gray-100 ${
                      s.session_id === sessionId ? "bg-blue-50 border-l-2 border-l-blue-600" : ""
                    }`}
                  >
                    <div className="text-sm font-medium text-gray-700 truncate">
                      {s.initial_idea || "未命名会话"}
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-gray-400">
                      <span className={`inline-block rounded-full px-1.5 py-0.5 ${
                        s.status === "dialogue" ? "bg-blue-100 text-blue-600" :
                        s.status === "requirement" ? "bg-yellow-100 text-yellow-600" :
                        s.status === "review" ? "bg-green-100 text-green-600" :
                        "bg-gray-100 text-gray-500"
                      }`}>
                        {s.status === "dialogue" ? "对话中" :
                         s.status === "requirement" ? "需求确认" :
                         s.status === "review" ? "方案评审" :
                         s.status === "generating" ? "生成中" : s.status}
                      </span>
                      <span>{new Date(s.created_at).toLocaleString("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <header className="shrink-0 bg-white shadow-sm border-b">
          <div className="flex items-center justify-between px-4 py-3">
            <h2 className="text-lg font-semibold text-gray-800">
              工业设计头脑风暴
            </h2>
          </div>
        </header>

        {/* Step indicator */}
        <nav className="shrink-0 border-b border-gray-200 bg-white">
          <div className="px-4">
            <ol className="flex items-center gap-2 py-2">
              {STEPS.map((step, idx) => {
                const stepNum = step.step;
                const isActive = stepNum === currentStep;
                const isCompleted = stepNum < currentStep;
                return (
                  <li key={step.key} className="flex items-center gap-2">
                    {idx > 0 && (
                      <div className={`h-px w-8 ${stepNum <= currentStep ? "bg-blue-600" : "bg-gray-300"}`} />
                    )}
                    <div
                      className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                        isActive
                          ? "bg-blue-600 text-white"
                          : isCompleted
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-400"
                      }`}
                    >
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/20 text-[10px]">
                        {isCompleted ? "✓" : stepNum}
                      </span>
                      {step.label}
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        </nav>

        {/* Main content */}
        <main className="flex min-h-0 flex-1 flex-col">
          {currentStep === 1 && (
            <DialoguePage key={designKey} onComplete={() => setCurrentStep(2)} />
          )}
          {currentStep === 2 && sessionId && (
            <RequirementPage
              key={designKey}
              sessionId={sessionId}
              onProceed={() => setCurrentStep(3)}
              onBack={() => setCurrentStep(1)}
            />
          )}
          {currentStep === 3 && sessionId && (
            <CandidatePage
              key={designKey}
              sessionId={sessionId}
              onBack={() => setCurrentStep(2)}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
