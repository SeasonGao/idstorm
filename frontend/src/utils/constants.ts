export const DIMENSION_LABELS: Record<string, string> = {
  form_size: "形态与尺寸",
  material_color: "材质与色彩",
  scenario: "使用场景与交互",
  brand: "品牌与市场定位",
};

export const STEPS = [
  { key: "dialogue", label: "设计对话", step: 1 },
  { key: "requirement", label: "设计需求", step: 2 },
  { key: "candidates", label: "候选方案", step: 3 },
] as const;

export const API_BASE = "/api";
