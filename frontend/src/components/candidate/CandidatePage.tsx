import { useEffect, useState } from "react";
import { useCandidates, type ImageModel } from "../../hooks/useCandidates";
import CandidateCard from "./CandidateCard";
import LoadingSpinner from "../common/LoadingSpinner";
import Button from "../common/Button";

interface CandidatePageProps {
  sessionId: string;
  onBack: () => void;
}

const IMAGE_MODELS: { value: ImageModel; label: string }[] = [
  { value: "doubao", label: "豆包 Seedream" },
  { value: "openai", label: "OpenAI GPT-Image" },
];

export default function CandidatePage({
  sessionId,
  onBack,
}: CandidatePageProps) {
  const {
    candidates, isGenerating, error, loadExisting, generate, regenerateImage, iterate,
    imageModel, setImageModel,
  } = useCandidates();

  useEffect(() => {
    loadExisting(sessionId);
  }, [sessionId, loadExisting]);

  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [candidateCount, setCandidateCount] = useState(3);

  const handleIterateSuccess = () => {
    setSuccessMessage("方案已更新");
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  const handleModelChange = (model: ImageModel) => {
    setImageModel(model);
  };

  const handleGenerate = () => {
    generate(sessionId, imageModel, candidateCount);
  };

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {isGenerating && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm">
          <LoadingSpinner className="mb-4" />
          <p className="text-sm font-medium text-gray-600">
            正在生成设计方案...
          </p>
          <p className="mt-1 text-xs text-gray-400">
            这可能需要几分钟，请稍候
          </p>
        </div>
      )}

      {successMessage && (
        <div className="absolute top-4 left-1/2 z-20 -translate-x-1/2 rounded-lg bg-green-50 border border-green-200 px-4 py-2 text-sm font-medium text-green-700 shadow-sm">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="mx-auto mt-4 max-w-lg rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-4xl px-4 py-6">
          <div className="mb-6 flex items-center gap-6">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-600">图像模型：</span>
              <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
                {IMAGE_MODELS.map((m) => (
                  <button
                    key={m.value}
                    onClick={() => handleModelChange(m.value)}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      imageModel === m.value
                        ? "bg-white text-blue-600 shadow-sm"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-600">方案数量：</span>
              <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    onClick={() => setCandidateCount(n)}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      candidateCount === n
                        ? "bg-white text-blue-600 shadow-sm"
                        : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {candidates.length === 0 && !isGenerating ? (
            <div className="flex flex-col items-center justify-center py-20">
              <p className="mb-4 text-sm text-gray-500">尚未生成设计方案，点击下方按钮开始生成</p>
              <Button onClick={handleGenerate}>
                生成设计方案
              </Button>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-6">
                {candidates.map((candidate) => (
                  <CandidateCard
                    key={candidate.id}
                    candidate={candidate}
                    sessionId={sessionId}
                    onRegenerateImage={(view) =>
                      regenerateImage(sessionId, candidate.id, view)
                    }
                    onIterate={(mode, updates) =>
                      iterate(sessionId, candidate.id, mode, updates)
                    }
                    onIterateSuccess={handleIterateSuccess}
                  />
                ))}
              </div>

              <div className="mt-8 flex items-center justify-center gap-4 pb-6">
                <Button variant="secondary" onClick={onBack}>
                  返回修改需求
                </Button>
                <Button onClick={handleGenerate}>
                  重新生成全部
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
