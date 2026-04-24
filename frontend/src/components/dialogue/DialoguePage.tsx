import { useState } from "react";
import { useSession } from "../../hooks/useSession";
import { useChat } from "../../hooks/useChat";
import { API_BASE, DIMENSION_LABELS } from "../../utils/constants";
import ChatWindow from "./ChatWindow";
import ChatInput from "./ChatInput";
import Button from "../common/Button";

interface DialoguePageProps {
  onComplete: () => void;
}

export default function DialoguePage({ onComplete }: DialoguePageProps) {
  const { sessionId, status, setStatus, createSession, resetSession } = useSession();
  const { messages, isStreaming, dimensionProgress, dialogueComplete, sendMessage, skipToNext } = useChat((code) => {
    if (code === "not_found") {
      resetSession();
      setError("会话已过期，请重新开始对话。");
    }
  });
  const [error, setError] = useState<string | null>(null);

  const _ensureSession = async (content: string): Promise<string> => {
    if (sessionId) return sessionId;
    const session = await createSession(content);
    return session.session_id;
  };

  const handleSend = async (content: string) => {
    setError(null);
    try {
      const sid = await _ensureSession(content);
      await sendMessage(`${API_BASE}/dialogue/message`, sid, content);
    } catch {
      setError("创建会话失败，请重试。");
    }
  };

  const handleOptionSelect = async (selected: string) => {
    setError(null);
    try {
      const sid = await _ensureSession(selected);
      await sendMessage(`${API_BASE}/dialogue/message`, sid, selected);
    } catch {
      setError("发送失败，请重试。");
    }
  };

  const handleOptionMultiConfirm = async (selected: string[]) => {
    const text = selected.join("、");
    setError(null);
    try {
      const sid = await _ensureSession(text);
      await sendMessage(`${API_BASE}/dialogue/message`, sid, text);
    } catch {
      setError("发送失败，请重试。");
    }
  };

  const handleSkipToNext = async () => {
    setError(null);
    try {
      if (!sessionId) {
        setError("请先发送一条消息开始对话。");
        return;
      }
      await skipToNext(`${API_BASE}/dialogue/message`, sessionId);
    } catch {
      setError("操作失败，请重试。");
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Dimension progress badges */}
      {dimensionProgress && (
        <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 bg-gray-50 px-4 py-2">
          <span className="text-xs text-gray-500 mr-1">探索维度：</span>
          {dimensionProgress.completed.map(dim => (
            <span
              key={dim}
              className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700"
            >
              {DIMENSION_LABELS[dim] || dim} ✓
            </span>
          ))}
          {dimensionProgress.current && (
            <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 animate-pulse">
              {DIMENSION_LABELS[dimensionProgress.current] || dimensionProgress.current} ...
            </span>
          )}
          {dimensionProgress.remaining.map(dim => (
            <span
              key={dim}
              className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-400"
            >
              {DIMENSION_LABELS[dim] || dim}
            </span>
          ))}
        </div>
      )}

      {/* Chat area */}
      <ChatWindow
        messages={messages}
        isStreaming={isStreaming}
        onOptionSelect={handleOptionSelect}
        onOptionMultiConfirm={handleOptionMultiConfirm}
      />

      {/* Error */}
      {error && (
        <div className="px-4 py-1 text-xs text-red-500">{error}</div>
      )}

      {/* Dialogue complete action */}
      {dialogueComplete && !isStreaming ? (
        <div className="flex justify-center border-t border-gray-200 bg-white px-4 py-3">
          <Button onClick={onComplete}>
            查看设计需求
          </Button>
        </div>
      ) : (
        /* Input area with skip button */
        <>
          <ChatInput onSend={handleSend} disabled={isStreaming} />
          {!isStreaming && sessionId && (
            <div className="flex justify-center border-t border-gray-100 bg-white px-4 py-2">
              <button
                onClick={handleSkipToNext}
                className="text-xs text-gray-400 hover:text-blue-500 transition-colors underline underline-offset-2"
              >
                进入下一步骤 →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
