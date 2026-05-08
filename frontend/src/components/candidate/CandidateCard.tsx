import { useState } from "react";
import type { Candidate } from "../../types";
import ImageWithPlaceholder from "../common/ImageWithPlaceholder";

interface CandidateCardProps {
  candidate: Candidate;
  sessionId: string;
  onRegenerateImage: () => void;
  onIterate: (mode: "text_edit" | "image_feedback", updates: any) => Promise<Candidate>;
  onImageIterate: (baseImageId: string | null, feedbackText: string) => Promise<Candidate>;
  onIterateSuccess: () => void;
}

export default function CandidateCard({
  candidate,
  sessionId,
  onRegenerateImage,
  onIterate: _onIterate,
  onImageIterate,
  onIterateSuccess,
}: CandidateCardProps) {
  const isFailed = candidate.status === "failed";
  const images = candidate.images || [];
  const hasImage = !!candidate.image_url;

  // Quick modify input (always visible below main image)
  const [quickFeedback, setQuickFeedback] = useState("");
  const [isQuickIterating, setIsQuickIterating] = useState(false);

  // Per-history-image feedback inputs
  const [feedbackTexts, setFeedbackTexts] = useState<Record<string, string>>({});
  const [iteratingImageId, setIteratingImageId] = useState<string | null>(null);

  // Use latest image as base for quick modify
  const latestImageId = images.length > 0 ? images[images.length - 1].id : null;

  const handleQuickSubmit = async () => {
    const text = quickFeedback.trim();
    if (!text) return;
    setIsQuickIterating(true);
    try {
      await onImageIterate(latestImageId, text);
      setQuickFeedback("");
      onIterateSuccess();
    } catch {
      // Error handled by hook
    } finally {
      setIsQuickIterating(false);
    }
  };

  const handleHistorySubmit = async (baseImageId: string) => {
    const text = feedbackTexts[baseImageId]?.trim();
    if (!text) return;
    setIteratingImageId(baseImageId);
    try {
      await onImageIterate(baseImageId, text);
      setFeedbackTexts((prev) => ({ ...prev, [baseImageId]: "" }));
      onIterateSuccess();
    } catch {
      // Error handled by hook
    } finally {
      setIteratingImageId(null);
    }
  };

  return (
    <div className="rounded-xl bg-white shadow-md border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-100 bg-gray-50 px-5 py-3">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-0.5 text-sm font-semibold text-blue-700">
            {candidate.label}
          </span>
          <span className="text-sm text-gray-600">
            {candidate.variant_description}
          </span>
          {images.length > 1 && (
            <span className="text-xs text-gray-400">
              共 {images.length} 个版本
            </span>
          )}
        </div>
      </div>

      {/* Main image display */}
      {hasImage && (
        <div className="p-5 pb-3">
          <div className="rounded-lg bg-gray-50 border border-gray-200 overflow-hidden">
            <ImageWithPlaceholder
              src={candidate.image_url}
              alt={`${candidate.label} 设计方案`}
              className="h-auto w-full"
              onRegenerate={isFailed ? onRegenerateImage : undefined}
            />
          </div>
        </div>
      )}

      {/* Quick modify input - always visible when image exists */}
      {hasImage && (
        <div className="px-5 pb-4">
          <div className="flex gap-2">
            <input
              value={quickFeedback}
              onChange={(e) => setQuickFeedback(e.target.value)}
              placeholder="输入修改意见，基于当前图片微调..."
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 outline-none placeholder:text-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
              disabled={isQuickIterating}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleQuickSubmit();
              }}
            />
            <button
              onClick={handleQuickSubmit}
              disabled={isQuickIterating || !quickFeedback.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
            >
              {isQuickIterating ? "生成中..." : "生成新版本"}
            </button>
          </div>
        </div>
      )}

      {/* Image History Timeline (only when multiple versions exist) */}
      {images.length > 1 && (
        <div className="border-t border-gray-100 px-5 py-4">
          <div className="mb-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
            历史版本
          </div>
          <div className="space-y-3">
            {images.slice(0, -1).reverse().map((img) => {
              const isIterating = iteratingImageId === img.id;

              return (
                <div key={img.id} className="flex gap-3">
                  <img
                    src={img.url}
                    alt={`历史版本`}
                    className="flex-shrink-0 w-16 h-16 rounded-lg border border-gray-200 object-cover"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {img.feedback ? (
                        <span className="text-xs text-gray-500 truncate max-w-[200px]">
                          {img.feedback}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">初始版本</span>
                      )}
                    </div>
                    <div className="flex gap-1.5">
                      <input
                        value={feedbackTexts[img.id] || ""}
                        onChange={(e) =>
                          setFeedbackTexts((prev) => ({
                            ...prev,
                            [img.id]: e.target.value,
                          }))
                        }
                        placeholder="基于此图修改..."
                        className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 outline-none placeholder:text-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
                        disabled={isIterating}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleHistorySubmit(img.id);
                        }}
                      />
                      <button
                        onClick={() => handleHistorySubmit(img.id)}
                        disabled={isIterating || !feedbackTexts[img.id]?.trim()}
                        className="rounded bg-blue-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {isIterating ? "..." : "生成"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
