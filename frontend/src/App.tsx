import { useState, useEffect, useCallback } from "react";
import { STEPS } from "./utils/constants";
import { useSession } from "./hooks/useSession";
import DialoguePage from "./components/dialogue/DialoguePage";
import RequirementPage from "./components/requirement/RequirementPage";
import CandidatePage from "./components/candidate/CandidatePage";
import SettingsPanel from "./components/common/SettingsPanel";
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
  const [showSettings, setShowSettings] = useState(false);

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
    const newStatus = await switchSession(sid);
    setCurrentStep(statusToStep(newStatus));
    setDesignKey(prev => prev + 1);
  };

  const handleDeleteSession = async (e: React.MouseEvent, sid: string) => {
    e.stopPropagation();
    if (!confirm("确定删除该会话？")) return;
    try {
      await apiClient.delete(`/session/${sid}`);
      if (sid === sessionId) {
        resetSession();
        setCurrentStep(1);
        setDesignKey(prev => prev + 1);
      }
      fetchSessions();
    } catch {
      // ignore
    }
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
                <li key={s.session_id} className="group relative">
                  <button
                    onClick={() => handleSwitchSession(s.session_id)}
                    className={`w-full text-left px-4 py-3 pr-9 transition-colors hover:bg-gray-50 border-b border-gray-100 ${
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
                  <button
                    onClick={(e) => handleDeleteSession(e, s.session_id)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-gray-300 opacity-0 group-hover:opacity-100 hover:bg-gray-100 hover:text-red-500 transition-all"
                    title="删除会话"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
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
            <button
              onClick={() => setShowSettings(true)}
              className="rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
              title="API Key 设置"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
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
                const clickable = isCompleted || isActive;
                return (
                  <li key={step.key} className="flex items-center gap-2">
                    {idx > 0 && (
                      <div className={`h-px w-8 ${stepNum <= currentStep ? "bg-blue-600" : "bg-gray-300"}`} />
                    )}
                    <button
                      disabled={!clickable}
                      onClick={() => setCurrentStep(stepNum)}
                      className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                        isActive
                          ? "bg-blue-600 text-white"
                          : isCompleted
                            ? "bg-green-100 text-green-700 hover:bg-green-200 cursor-pointer"
                            : "bg-gray-100 text-gray-400 cursor-not-allowed"
                      }`}
                    >
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/20 text-[10px]">
                        {isCompleted ? "✓" : stepNum}
                      </span>
                      {step.label}
                    </button>
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

      {showSettings && (
        <SettingsPanel onClose={() => setShowSettings(false)} />
      )}
    </div>
  );
}

export default App;
