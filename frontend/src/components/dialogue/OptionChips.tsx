import { useState } from "react";
import type { MessageOptions } from "../../types";

interface OptionChipsProps {
  options: MessageOptions;
  disabled?: boolean;
  onSelect: (selected: string) => void;
  onMultiConfirm: (selected: string[]) => void;
}

export default function OptionChips({ options, disabled = false, onSelect, onMultiConfirm }: OptionChipsProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmed, setConfirmed] = useState(false);
  const [showCustom, setShowCustom] = useState(false);
  const [customText, setCustomText] = useState("");

  const isMulti = options.type === "multi";

  const handleSingleClick = (item: string) => {
    if (disabled || confirmed) return;
    setConfirmed(true);
    onSelect(item);
  };

  const handleToggle = (item: string) => {
    if (disabled || confirmed) return;
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(item)) {
        next.delete(item);
      } else {
        next.add(item);
      }
      return next;
    });
  };

  const handleMultiConfirm = () => {
    if (disabled || confirmed || selected.size === 0) return;
    setConfirmed(true);
    onMultiConfirm(Array.from(selected));
  };

  const handleCustomSubmit = () => {
    const text = customText.trim();
    if (!text || disabled || confirmed) return;
    setConfirmed(true);
    onSelect(text);
  };

  const handleCustomKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleCustomSubmit();
    }
  };

  // Show custom input when "其他..." is clicked (for single-select)
  const handleOtherClick = () => {
    if (isMulti) {
      // For multi-select, just toggle "其他" and show input
      setShowCustom(true);
    } else {
      setShowCustom(true);
    }
  };

  const allItems = [...options.items];

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {allItems.map((item) => {
        const isSelected = selected.has(item);
        const isDisabled = disabled || confirmed;
        return (
          <button
            key={item}
            onClick={() => isMulti ? handleToggle(item) : handleSingleClick(item)}
            disabled={isDisabled}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
              isSelected
                ? "border-blue-500 bg-blue-50 text-blue-700"
                : isDisabled
                  ? "border-gray-200 bg-gray-50 text-gray-300 cursor-not-allowed"
                  : "border-gray-200 bg-white text-gray-600 hover:border-blue-300 hover:text-blue-600"
            }`}
          >
            {item}
          </button>
        );
      })}

      {/* "其他..." option */}
      {!showCustom && (
        <button
          onClick={handleOtherClick}
          disabled={disabled || confirmed}
          className={`rounded-full border border-dashed px-3 py-1.5 text-xs transition-colors ${
            disabled || confirmed
              ? "border-gray-200 text-gray-300 cursor-not-allowed"
              : "border-gray-300 text-gray-400 hover:border-blue-300 hover:text-blue-500"
          }`}
        >
          其他...
        </button>
      )}

      {/* Custom text input */}
      {showCustom && (
        <div className="flex items-center gap-1.5">
          <input
            type="text"
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            onKeyDown={handleCustomKeyDown}
            placeholder="输入你的想法"
            disabled={disabled || confirmed}
            className="w-32 rounded-full border border-gray-300 px-3 py-1.5 text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-300"
            autoFocus
          />
          <button
            onClick={handleCustomSubmit}
            disabled={disabled || confirmed || !customText.trim()}
            className="rounded-full bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            确定
          </button>
        </div>
      )}

      {/* Multi-select confirm button */}
      {isMulti && !confirmed && selected.size > 0 && (
        <button
          onClick={handleMultiConfirm}
          className="rounded-full bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
        >
          确认选择 ({selected.size})
        </button>
      )}
    </div>
  );
}
