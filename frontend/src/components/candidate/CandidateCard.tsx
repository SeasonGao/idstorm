import { useState, useEffect } from "react";
import type { Candidate, CandidateImageEntry } from "../../types";
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
  sessionId: _sessionId,
  onRegenerateImage,
  onIterate: _onIterate,
  onImageIterate,
  onIterateSuccess,
}: CandidateCardProps) {
  const isFailed = candidate.status === "failed";
  const images = candidate.images || [];
  const hasImage = !!candidate.image_url;

  // Build a flat display list: if images is empty but image_url exists, create a synthetic entry
  const displayList: CandidateImageEntry[] = images.length > 0
    ? images
    : hasImage
      ? [{ id: "__current__", url: candidate.image_url, feedback: null, parent_image_id: null, created_at: "" }]
      : [];

  // Currently selected version index (defaults to latest = last)
  const [selectedIdx, setSelectedIdx] = useState(displayList.length - 1);

  // Reset selection when images change (new iteration)
  useEffect(() => {
    setSelectedIdx(displayList.length - 1);
  }, [images.length, candidate.image_url]);

  const selectedImage = displayList[selectedIdx] || displayList[displayList.length - 1];

  // Per-image feedback text inputs
  const [feedbackTexts, setFeedbackTexts] = useState<Record<string, string>>({});
  const [iteratingImageId, setIteratingImageId] = useState<string | null>(null);
  const [isQuickIterating, setIsQuickIterating] = useState(false);

  const handleSubmit = async (baseImageId: string | null, feedback: string) => {
    if (!feedback.trim()) return;

    // Determine which state setter to use
    const isQuick = baseImageId === "__quick__";
    if (isQuick) {
      setIsQuickIterating(true);
    } else {
      setIteratingImageId(baseImageId);
    }

    try {
      // Use null for synthetic entries so backend falls back to latest real image
      const realId = baseImageId === "__quick__" || baseImageId === "__current__" ? null : baseImageId;
      await onImageIterate(realId, feedback.trim());
      if (baseImageId != null) setFeedbackTexts((prev) => ({ ...prev, [baseImageId]: "" }));
      onIterateSuccess();
    } catch {
      // Error handled by hook
    } finally {
      if (isQuick) {
        setIsQuickIterating(false);
      } else {
        setIteratingImageId(null);
      }
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
      {selectedImage && (
        <div className="p-5 pb-3">
          <div className="rounded-lg bg-gray-50 border border-gray-200 overflow-hidden">
            <ImageWithPlaceholder
              src={selectedImage.url}
              alt={`${candidate.label} - 版本 ${selectedIdx + 1}`}
              className="h-auto w-full"
              onRegenerate={isFailed ? onRegenerateImage : undefined}
            />
          </div>
          {/* Show feedback for selected version */}
          {selectedImage.feedback && (
            <div className="mt-2 text-xs text-gray-500">
              修改意见：{selectedImage.feedback}
            </div>
          )}
        </div>
      )}

      {/* Version tabs */}
      {displayList.length > 1 && (
        <div className="px-5 pb-2">
          <div className="flex gap-2 overflow-x-auto pb-2">
            {displayList.map((img, idx) => (
              <button
                key={img.id}
                onClick={() => setSelectedIdx(idx)}
                className={`group relative flex-shrink-0 rounded-lg border-2 overflow-hidden transition-all ${
                  idx === selectedIdx
                    ? "border-blue-500 ring-1 ring-blue-500"
                    : "border-gray-200 hover:border-gray-400"
                }`}
                title={img.feedback || `版本 ${idx + 1}`}
              >
                <img
                  src={img.url}
                  alt={`V${idx + 1}`}
                  className="w-16 h-16 object-cover"
                />
                <div className={`absolute bottom-0 left-0 right-0 text-center text-[10px] font-bold py-0.5 ${
                  idx === selectedIdx
                    ? "bg-blue-500 text-white"
                    : "bg-black/50 text-white group-hover:bg-black/70"
                }`}>
                  V{idx + 1}
                </div>
                {/* Latest badge */}
                {idx === displayList.length - 1 && (
                  <div className="absolute top-0 right-0 text-[8px] bg-green-500 text-white px-1 rounded-bl">
                    最新
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Modification input for selected version */}
      {hasImage && selectedImage && (
        <div className="px-5 pb-4">
          <div className="text-xs text-gray-400 mb-1.5">
            {displayList.length > 1
              ? `基于 V${selectedIdx + 1} 修改`
              : "输入修改意见，基于当前图片微调"}
          </div>
          <div className="flex gap-2">
            <input
              value={feedbackTexts[selectedImage.id] || ""}
              onChange={(e) =>
                setFeedbackTexts((prev) => ({
                  ...prev,
                  [selectedImage.id]: e.target.value,
                }))
              }
              placeholder="描述修改意见..."
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 outline-none placeholder:text-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
              disabled={iteratingImageId === selectedImage.id || isQuickIterating}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSubmit(selectedImage.id, feedbackTexts[selectedImage.id] || "");
              }}
            />
            <button
              onClick={() => handleSubmit(selectedImage.id, feedbackTexts[selectedImage.id] || "")}
              disabled={iteratingImageId === selectedImage.id || isQuickIterating || !feedbackTexts[selectedImage.id]?.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
            >
              {iteratingImageId === selectedImage.id || isQuickIterating ? "生成中..." : "生成新版本"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
