import { useState } from "react";
import type { Candidate } from "../../types";
import ImageWithPlaceholder from "../common/ImageWithPlaceholder";
import IterationPanel from "./IterationPanel";

interface CandidateCardProps {
  candidate: Candidate;
  sessionId: string;
  onRegenerateImage: (view: string) => void;
  onIterate: (mode: "text_edit" | "image_feedback", updates: any) => Promise<Candidate>;
  onIterateSuccess: () => void;
}

export default function CandidateCard({
  candidate,
  sessionId,
  onRegenerateImage,
  onIterate,
  onIterateSuccess,
}: CandidateCardProps) {
  const [showIteration, setShowIteration] = useState(false);
  const orthographicFailed = candidate.failed_views.includes("orthographic");
  const renderFailed = candidate.failed_views.includes("render");

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
        </div>
      </div>

      {/* Images */}
      <div className="grid grid-cols-2 gap-4 p-5">
        {/* Orthographic View */}
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            三视图
          </span>
          <div className="h-64 rounded-lg bg-gray-50 border border-gray-200 overflow-hidden">
            <ImageWithPlaceholder
              src={candidate.orthographic_url}
              alt={`${candidate.label} 三视图`}
              className="h-full w-full"
              onRegenerate={
                orthographicFailed
                  ? () => onRegenerateImage("orthographic")
                  : undefined
              }
            />
          </div>
        </div>

        {/* Render View */}
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            展示图
          </span>
          <div className="h-64 rounded-lg bg-gray-50 border border-gray-200 overflow-hidden">
            <ImageWithPlaceholder
              src={candidate.render_url}
              alt={`${candidate.label} 展示图`}
              className="h-full w-full"
              onRegenerate={
                renderFailed
                  ? () => onRegenerateImage("render")
                  : undefined
              }
            />
          </div>
        </div>
      </div>

      {/* Adjust Design Toggle */}
      <div className="border-t border-gray-100 px-5 py-3">
        <button
          onClick={() => setShowIteration((prev) => !prev)}
          className="flex items-center gap-1.5 text-sm font-medium text-blue-600 transition-colors hover:text-blue-800"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`h-4 w-4 transition-transform ${showIteration ? "rotate-180" : ""}`}
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
          调整方案
        </button>
      </div>

      {/* Iteration Panel */}
      {showIteration && (
        <IterationPanel
          sessionId={sessionId}
          candidate={candidate}
          onIterate={async (mode, updates) => {
            const updated = await onIterate(mode, updates);
            return updated;
          }}
          onSuccess={() => {
            onIterateSuccess();
            setShowIteration(false);
          }}
          onClose={() => setShowIteration(false)}
        />
      )}
    </div>
  );
}
