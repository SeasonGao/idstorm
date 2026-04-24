import { useState, useEffect, useCallback, useRef } from "react";
import type { Candidate, Dimension, DimensionField } from "../../types";
import apiClient from "../../api/client";
import Button from "../common/Button";
import LoadingSpinner from "../common/LoadingSpinner";

interface IterationPanelProps {
  sessionId: string;
  candidate: Candidate;
  onIterate: (mode: "text_edit" | "image_feedback", updates: any) => Promise<Candidate>;
  onSuccess: () => void;
  onClose: () => void;
}

type IterationMode = "text_edit" | "image_feedback";

export default function IterationPanel({
  sessionId,
  candidate,
  onIterate,
  onSuccess,
  onClose,
}: IterationPanelProps) {
  const [mode, setMode] = useState<IterationMode>("text_edit");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Text edit state
  const [fields, setFields] = useState<DimensionField[]>([]);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [requirementLoading, setRequirementLoading] = useState(false);
  const initialValuesRef = useRef<Record<string, string>>({});

  // Image feedback state
  const [feedbackText, setFeedbackText] = useState("");

  // Fetch requirement fields for text edit mode
  useEffect(() => {
    if (mode !== "text_edit") return;

    let cancelled = false;
    setRequirementLoading(true);
    apiClient
      .get(`/requirement/${sessionId}`)
      .then((res) => {
        if (cancelled) return;
        const dimensions: Record<string, Dimension> = res.data.dimensions;
        const allFields: DimensionField[] = [];
        const initialValues: Record<string, string> = {};
        for (const dim of Object.values(dimensions)) {
          for (const field of dim.fields) {
            if (field.editable) {
              allFields.push(field);
              initialValues[field.key] = field.value;
            }
          }
        }
        setFields(allFields);
        setFieldValues(initialValues);
        initialValuesRef.current = initialValues;
      })
      .catch(() => {
        if (cancelled) return;
        setError("加载需求数据失败");
      })
      .finally(() => {
        if (!cancelled) setRequirementLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, mode]);

  const handleTextEdit = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Only send fields that actually changed compared to initial values
      const changedFields: Record<string, string> = {};
      for (const [key, value] of Object.entries(fieldValues)) {
        if (value !== initialValuesRef.current[key]) {
          changedFields[key] = value;
        }
      }
      if (Object.keys(changedFields).length === 0) {
        setLoading(false);
        return;
      }
      await onIterate("text_edit", changedFields);
      onSuccess();
    } catch (err: any) {
      setError(err.message || "迭代失败，请重试");
    } finally {
      setLoading(false);
    }
  }, [fieldValues, onIterate, onSuccess]);

  const handleImageFeedback = useCallback(async () => {
    if (!feedbackText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await onIterate("image_feedback", { annotation_text: feedbackText.trim() });
      onSuccess();
    } catch (err: any) {
      setError(err.message || "迭代失败，请重试");
    } finally {
      setLoading(false);
    }
  }, [feedbackText, onIterate, onSuccess]);

  return (
    <div className="border-t border-gray-200 bg-white px-5 py-4">
      {/* Mode Tabs */}
      <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1">
        <button
          onClick={() => setMode("text_edit")}
          className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            mode === "text_edit"
              ? "bg-white text-blue-700 shadow-sm"
              : "text-gray-600 hover:text-gray-800"
          }`}
        >
          修改参数
        </button>
        <button
          onClick={() => setMode("image_feedback")}
          className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            mode === "image_feedback"
              ? "bg-white text-blue-700 shadow-sm"
              : "text-gray-600 hover:text-gray-800"
          }`}
        >
          图像反馈
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-3 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="mb-3 flex items-center gap-2 text-sm text-gray-600">
          <LoadingSpinner className="" />
          <span>正在重新生成...</span>
        </div>
      )}

      {/* Text Edit Mode */}
      {mode === "text_edit" && !loading && (
        <>
          {requirementLoading ? (
            <div className="flex items-center justify-center py-6">
              <LoadingSpinner className="mr-2" />
              <span className="text-sm text-gray-500">加载中...</span>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              {fields.map((field) => (
                <div key={field.key}>
                  <label className="mb-1 block text-xs font-medium text-gray-500">
                    {field.label}
                  </label>
                  <input
                    value={fieldValues[field.key] ?? ""}
                    onChange={(e) =>
                      setFieldValues((prev) => ({
                        ...prev,
                        [field.key]: e.target.value,
                      }))
                    }
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm text-gray-800 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
                  />
                </div>
              ))}
            </div>
          )}
          <div className="mt-4 flex items-center justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>
              取消
            </Button>
            <Button onClick={handleTextEdit} disabled={loading || fields.length === 0}>
              应用修改
            </Button>
          </div>
        </>
      )}

      {/* Image Feedback Mode */}
      {mode === "image_feedback" && !loading && (
        <>
          <textarea
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            placeholder="描述你希望对这个设计方案做什么调整..."
            rows={3}
            className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 outline-none placeholder:text-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
          />
          <div className="mt-3 flex items-center justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>
              取消
            </Button>
            <Button
              onClick={handleImageFeedback}
              disabled={loading || !feedbackText.trim()}
            >
              提交反馈
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
