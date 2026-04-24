import { useState, useCallback, useRef } from "react";
import type { ChatMessage, DimensionProgress, MessageOptions } from "../types";

export function useChat(onSessionError?: (code: string) => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [dimensionProgress, setDimensionProgress] = useState<DimensionProgress | null>(null);
  const [dialogueComplete, setDialogueComplete] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const _processSSE = async (reader: ReadableStreamDefaultReader<Uint8Array>) => {
    const decoder = new TextDecoder();
    let buffer = "";
    let assistantContent = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ") && currentEvent) {
          try {
            const data = JSON.parse(line.slice(6));
            console.log(`[SSE] event: ${currentEvent}`, data);
            switch (currentEvent) {
              case "token":
                assistantContent += data.delta;
                setMessages(prev => {
                  const updated = [...prev];
                  updated[updated.length - 1] = { role: "assistant", content: assistantContent };
                  return updated;
                });
                break;
              case "metadata":
                setDimensionProgress(data.dimension_progress);
                setDialogueComplete(data.dialogue_complete);
                break;
              case "options":
                // Attach options to the last assistant message
                setMessages(prev => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last && last.role === "assistant") {
                    updated[updated.length - 1] = { ...last, options: data as MessageOptions };
                  }
                  return updated;
                });
                break;
              case "done":
                // Replace with clean content + options from done event
                if (data.message?.content) {
                  assistantContent = data.message.content;
                  console.log(`[SSE] done content: ${assistantContent}`);
                  const opts = data.options as MessageOptions | null | undefined;
                  setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      role: "assistant",
                      content: assistantContent,
                      options: opts ?? undefined,
                    };
                    return updated;
                  });
                }
                if (data.dimension_progress) {
                  setDimensionProgress(data.dimension_progress);
                }
                if (typeof data.dialogue_complete === "boolean") {
                  setDialogueComplete(data.dialogue_complete);
                }
                break;
              case "error":
                console.error("SSE Error:", data);
                if (data.code === "not_found") {
                  onSessionError?.(data.code);
                }
                break;
            }
          } catch {
            // Ignore parse errors for incomplete JSON
          }
          currentEvent = "";
        }
      }
    }
  };

  const sendMessage = useCallback(async (apiUrl: string, sessionId: string, content: string) => {
    setIsStreaming(true);

    // Add user message
    setMessages(prev => [...prev, { role: "user", content }]);

    // Create assistant placeholder
    setMessages(prev => [...prev, { role: "assistant", content: "" }]);

    abortRef.current = new AbortController();

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({ session_id: sessionId, content }),
        signal: abortRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      await _processSSE(reader);
    } catch (error: unknown) {
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
      abortRef.current = null;
    }
  }, []);

  const skipToNext = useCallback(async (apiUrl: string, sessionId: string) => {
    setIsStreaming(true);

    // Add system-like user message about skipping
    setMessages(prev => [...prev, { role: "assistant", content: "" }]);

    abortRef.current = new AbortController();

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({ session_id: sessionId, content: "", skip_to_next: true }),
        signal: abortRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      await _processSSE(reader);
    } catch (error: unknown) {
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
      abortRef.current = null;
    }
  }, []);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { messages, setMessages, isStreaming, dimensionProgress, dialogueComplete, sendMessage, skipToNext, stopStreaming };
}
