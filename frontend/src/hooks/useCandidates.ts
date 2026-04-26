import { useState, useCallback } from "react";
import apiClient from "../api/client";
import type { Candidate } from "../types";

export type ImageModel = "doubao" | "openai";

export function useCandidates() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageModel, setImageModel] = useState<ImageModel>("doubao");

  const loadExisting = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
      const res = await apiClient.get(`/candidate/${sessionId}`);
      const existing = res.data.candidates as Candidate[];
      if (existing.length > 0) {
        setCandidates(existing);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

  const generate = useCallback(async (sessionId: string, model?: ImageModel) => {
    setIsGenerating(true);
    setError(null);
    try {
      const res = await apiClient.post("/candidate/generate", {
        session_id: sessionId,
        image_model: model || imageModel,
      });
      setCandidates(res.data.candidates);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "生成失败，请重试";
      setError(message);
    } finally {
      setIsGenerating(false);
    }
  }, [imageModel]);

  const regenerateImage = useCallback(
    async (sessionId: string, candidateId: string, view: string) => {
      try {
        const res = await apiClient.post("/candidate/image/regenerate", {
          session_id: sessionId,
          candidate_id: candidateId,
          view,
          image_model: imageModel,
        });
        const updated = res.data.candidate;
        setCandidates((prev) =>
          prev.map((c) => (c.id === updated.id ? updated : c))
        );
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "重新生成失败";
        setError(message);
      }
    },
    [imageModel]
  );

  const iterate = useCallback(
    async (
      sessionId: string,
      candidateId: string,
      mode: "text_edit" | "image_feedback",
      updates: Record<string, string> | { annotation_text: string }
    ) => {
      try {
        const res = await apiClient.post("/candidate/iterate", {
          session_id: sessionId,
          candidate_id: candidateId,
          mode,
          updates,
          image_model: imageModel,
        });
        const updated = res.data.candidate;
        setCandidates((prev) =>
          prev.map((c) => (c.id === updated.id ? updated : c))
        );
        return updated;
      } catch (err: unknown) {
        throw new Error(err instanceof Error ? err.message : "迭代失败");
      }
    },
    [imageModel]
  );

  return {
    candidates, isGenerating, error, loadExisting, generate, regenerateImage, iterate,
    imageModel, setImageModel,
  };
}
