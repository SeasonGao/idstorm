import { useState, useEffect, useCallback } from "react";
import apiClient from "../../api/client";
import type { DesignRequirement, Dimension } from "../../types";
import DimensionCard from "./DimensionCard";
import RequirementSummary from "./RequirementSummary";

interface RequirementPageProps {
  sessionId: string;
  onProceed: () => void;
  onBack: () => void;
}

export default function RequirementPage({ sessionId, onProceed, onBack }: RequirementPageProps) {
  const [requirement, setRequirement] = useState<DesignRequirement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchRequirement = async () => {
      try {
        const res = await apiClient.get(`/requirement/${sessionId}`);
        if (!cancelled) {
          setRequirement(res.data);
        }
      } catch {
        if (!cancelled) {
          setError("加载设计需求失败，请重试。");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    fetchRequirement();
    return () => { cancelled = true; };
  }, [sessionId]);

  const handleFieldChange = useCallback(
    async (dimKey: string, fieldKey: string, value: string) => {
      if (!requirement) return;

      const updatedDimensions: Record<string, Dimension> = {
        ...requirement.dimensions,
        [dimKey]: {
          ...requirement.dimensions[dimKey],
          fields: requirement.dimensions[dimKey].fields.map((f) =>
            f.key === fieldKey ? { ...f, value } : f
          ),
        },
      };

      setRequirement((prev) =>
        prev ? { ...prev, dimensions: updatedDimensions } : prev
      );

      try {
        const res = await apiClient.put(`/requirement/${sessionId}`, {
          dimensions: updatedDimensions,
        });
        setRequirement(res.data);
      } catch {
        // Optimistic update stays; user can retry
      }
    },
    [requirement, sessionId]
  );

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <span className="text-sm text-gray-500">加载设计需求...</span>
        </div>
      </div>
    );
  }

  if (error || !requirement) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <p className="text-sm text-red-500">{error || "未找到需求数据"}</p>
          <button
            onClick={onBack}
            className="mt-3 text-sm text-blue-600 hover:underline"
          >
            返回对话
          </button>
        </div>
      </div>
    );
  }

  const dimensions = Object.values(requirement.dimensions);
  const totalFields = dimensions.reduce((sum, d) => sum + d.fields.length, 0);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">设计需求确认</h2>
          <div className="grid grid-cols-2 gap-4">
            {dimensions.map((dim) => (
              <DimensionCard
                key={dim.key}
                dimension={dim}
                onFieldChange={handleFieldChange}
              />
            ))}
          </div>
        </div>
      </div>
      <RequirementSummary
        dimensionCount={dimensions.length}
        fieldCount={totalFields}
        version={requirement.version}
        onProceed={onProceed}
        onBack={onBack}
      />
    </div>
  );
}
