import { useState } from "react";
import { STEPS } from "./utils/constants";
import { useSession } from "./hooks/useSession";
import DialoguePage from "./components/dialogue/DialoguePage";
import RequirementPage from "./components/requirement/RequirementPage";
import CandidatePage from "./components/candidate/CandidatePage";
import "./index.css";

function App() {
  const [currentStep, setCurrentStep] = useState(1);
  const [designKey, setDesignKey] = useState(0);
  const { sessionId, resetSession } = useSession();

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="shrink-0 bg-white shadow-sm border-b">
        <div className="max-w-5xl mx-auto flex items-center justify-between px-4 py-3">
          <h1 className="text-xl font-semibold text-gray-800">
            IDStorm - 工业设计头脑风暴
          </h1>
          <button
            onClick={() => {
              resetSession();
              setCurrentStep(1);
              setDesignKey(prev => prev + 1);
            }}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50"
          >
            新建设计
          </button>
        </div>
      </header>

      {/* Step indicator */}
      <nav className="shrink-0 border-b border-gray-200 bg-white">
        <div className="max-w-5xl mx-auto px-4">
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
            onBack={() => setCurrentStep(2)}
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
  );
}

export default App;
