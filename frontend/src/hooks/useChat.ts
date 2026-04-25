import { useState, useCallback } from "react";
import type { ChatMessage, DimensionProgress, MessageOptions } from "../types";

export function useChat(onSessionError?: (code: string) => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [dimensionProgress, setDimensionProgress] = useState<DimensionProgress | null>(null);
  const [dialogueComplete, setDialogueComplete] = useState(false);

  const sendMessage = useCallback(async (apiUrl: string, sessionId: string, content: string) => {
    setIsStreaming(true);
    console.log(`[CHAT] 发送消息: ${content}`);
    console.log(`[CHAT] 发送消息到 URL: ${apiUrl}`);

    setMessages(prev => [...prev, { role: "user", content }]);
    setMessages(prev => [...prev, { role: "assistant", content: "" }]);

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, content }),
      });

      if (!response.ok) {
        if (response.status === 404) {
          console.log("[CHAT] 会话不存在，将触发重置");
          onSessionError?.("not_found");
          setMessages(prev => prev.slice(0, -2));
          return;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log(`[CHAT] 收到响应:`, data);

      const assistantContent = data.content || "";
      const options = data.options as MessageOptions | null | undefined;
      const dp = data.dimension_progress as DimensionProgress | null;
      const dc = data.dialogue_complete as boolean;

      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: assistantContent,
          options: options ?? undefined,
        };
        return updated;
      });

      if (dp) setDimensionProgress(dp);
      if (typeof dc === "boolean") setDialogueComplete(dc);

    } catch (error: unknown) {
      console.error("[CHAT] 请求失败:", error);
      if (error instanceof Error && error.name !== "AbortError") {
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: "抱歉，发生了错误，请重试。",
          };
          return updated;
        });
      }
    } finally {
      setIsStreaming(false);
    }
  }, []);

  const skipToNext = useCallback(async (apiUrl: string, sessionId: string) => {
    setIsStreaming(true);
    console.log(`[CHAT] skipToNext`);

    setMessages(prev => [...prev, { role: "assistant", content: "" }]);

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, content: "", skip_to_next: true }),
      });

      if (!response.ok) {
        if (response.status === 404) {
          console.log("[CHAT] 会话不存在，将触发重置");
          onSessionError?.("not_found");
          setMessages(prev => prev.slice(0, -1));
          return;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log(`[CHAT] skipToNext 响应:`, data);

      const assistantContent = data.content || "";
      const options = data.options as MessageOptions | null | undefined;
      const dp = data.dimension_progress as DimensionProgress | null;
      const dc = data.dialogue_complete as boolean;

      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: assistantContent,
          options: options ?? undefined,
        };
        return updated;
      });

      if (dp) setDimensionProgress(dp);
      if (typeof dc === "boolean") setDialogueComplete(dc);

    } catch (error: unknown) {
      console.error("[CHAT] skipToNext 失败:", error);
      if (error instanceof Error && error.name !== "AbortError") {
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: "抱歉，操作失败，请重试。",
          };
          return updated;
        });
      }
    } finally {
      setIsStreaming(false);
    }
  }, []);

  return { messages, setMessages, isStreaming, dimensionProgress, dialogueComplete, sendMessage, skipToNext };
}
