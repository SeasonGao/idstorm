import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../types";
import MessageBubble from "./MessageBubble";
import LoadingSpinner from "../common/LoadingSpinner";

interface ChatWindowProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onOptionSelect?: (selected: string) => void;
  onOptionMultiConfirm?: (selected: string[]) => void;
}

export default function ChatWindow({ messages, isStreaming, onOptionSelect, onOptionMultiConfirm }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.length === 0 && (
        <div className="flex h-full items-center justify-center text-gray-400 text-sm">
          开始描述你的工业设计想法吧
        </div>
      )}
      {messages.map((msg, idx) => (
        <MessageBubble
          key={idx}
          message={msg}
          onOptionSelect={onOptionSelect}
          onOptionMultiConfirm={onOptionMultiConfirm}
          optionsDisabled={isStreaming || idx < messages.length - 1}
        />
      ))}
      {isStreaming && messages[messages.length - 1]?.content && (
        <LoadingSpinner className="py-2" />
      )}
      <div ref={bottomRef} />
    </div>
  );
}
