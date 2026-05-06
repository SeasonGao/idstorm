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
  const [regenerating, setRegenerating] = useState(false);
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

  const handleDescChange = useCallback(
    async (field: "product_name" | "three_view_desc" | "scene_desc", value: string) => {
      if (!requirement) return;
      setRequirement((prev) => prev ? { ...prev, [field]: value } : prev);
      try {
        const res = await apiClient.put(`/requirement/${sessionId}`, {
          [field]: value,
        });
        setRequirement(res.data);
      } catch {
        // Optimistic update stays
      }
    },
    [requirement, sessionId]
  );

  const handleRegenerate = async () => {
    setRegenerating(true);
    setError(null);
    try {
      const res = await apiClient.post(`/requirement/${sessionId}/regenerate`);
      setRequirement(res.data);
    } catch {
      setError("重新生成失败，请重试");
    } finally {
      setRegenerating(false);
    }
  };

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

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="mx-auto max-w-5xl">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">设计需求确认</h2>
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 disabled:opacity-50"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className={`h-4 w-4 ${regenerating ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {regenerating ? "生成中..." : "重新生成"}
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {dimensions.map((dim) => (
              <DimensionCard
                key={dim.key}
                dimension={dim}
                onFieldChange={handleFieldChange}
              />
            ))}
          </div>

          {/* Product descriptions for image generation */}
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
            <h3 className="mb-4 text-sm font-semibold text-gray-700">图片生成描述</h3>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">产品名称</label>
                <input
                  type="text"
                  value={requirement.product_name || ""}
                  onChange={(e) => handleDescChange("product_name", e.target.value)}
                  placeholder="如：电热水壶、智能台灯"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">三视图描述</label>
                <textarea
                  value={requirement.three_view_desc || ""}
                  onChange={(e) => handleDescChange("three_view_desc", e.target.value)}
                  placeholder="用于三视图的产品视觉描述，包含造型、材质、色彩等"
                  rows={3}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">场景展示描述</label>
                <textarea
                  value={requirement.scene_desc || ""}
                  onChange={(e) => handleDescChange("scene_desc", e.target.value)}
                  placeholder="用于场景展示图的描述，包含使用环境、氛围等"
                  rows={3}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
      <RequirementSummary
        dimensionCount={dimensions.length}
        version={requirement.version}
        onProceed={onProceed}
        onBack={onBack}
      />
    </div>
  );
}
