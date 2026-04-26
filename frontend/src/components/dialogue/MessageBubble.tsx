import type { ChatMessage } from "../../types";
import OptionChips from "./OptionChips";

interface MessageBubbleProps {
  message: ChatMessage;
  onOptionSelect?: (selected: string) => void;
  onOptionMultiConfirm?: (selected: string[]) => void;
  optionsDisabled?: boolean;
}

export default function MessageBubble({ message, onOptionSelect, onOptionMultiConfirm, optionsDisabled }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const hasOptions = !isUser && message.options && message.options.length > 0;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-blue-600 text-white rounded-br-md"
            : "bg-white text-gray-800 border border-gray-200 rounded-bl-md shadow-sm"
        }`}
      >
        {message.content || (
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
        )}
        {hasOptions && (
          <OptionChips
            options={message.options!}
            onSelect={onOptionSelect ?? (() => {})}
            onMultiConfirm={onOptionMultiConfirm ?? (() => {})}
            disabled={optionsDisabled}
          />
        )}
      </div>
    </div>
  );
}
