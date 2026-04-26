import React, { useState } from "react";
import type { Dimension } from "../../types";

const DIMENSION_COLORS: Record<string, string> = {
  form_size: "border-blue-500",
  material_color: "border-green-500",
  scenario: "border-orange-500",
  brand: "border-purple-500",
};

const DIMENSION_ICONS: Record<string, React.ReactNode> = {
  form_size: (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
      <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zm0 8a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zm6-6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zm2 6a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2h-2z" />
    </svg>
  ),
  material_color: (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-500" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M4 2a2 2 0 00-2 2v11a3 3 0 106 0V4a2 2 0 00-2-2H4zm1 14a1 1 0 100-2 1 1 0 000 2zm5-1.757l4.9-4.9a2 2 0 000-2.828L13.485 5.1a2 2 0 00-2.828 0L10 5.757v8.486zM16 18H9.071l6-6H16a2 2 0 012 2v2a2 2 0 01-2 2z" clipRule="evenodd" />
    </svg>
  ),
  scenario: (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-orange-500" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-6-3a2 2 0 11-4 0 2 2 0 014 0zm-2 4a5 5 0 00-4.546 2.916A5.986 5.986 0 0010 16a5.986 5.986 0 004.546-2.084A5 5 0 0010 11z" clipRule="evenodd" />
    </svg>
  ),
  brand: (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-purple-500" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M6.625 2.655A9 9 0 0119 11a1 1 0 11-2 0 7 7 0 00-9.625-6.492 1 1 0 11-.75-1.853zM4.662 6.32A7 7 0 0017 11a1 1 0 11-2 0 5 5 0 00-7.484-4.324 1 1 0 11-.854-1.756zm2.755 3.197A3 3 0 0115 11a1 1 0 11-2 0 1 1 0 00-1.25-.952 1 1 0 11-.333-1.984z" clipRule="evenodd" />
      <path d="M3.5 11a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
    </svg>
  ),
};

interface DimensionCardProps {
  dimension: Dimension;
  onFieldChange: (dimKey: string, fieldKey: string, value: string) => void;
}

export default function DimensionCard({ dimension, onFieldChange }: DimensionCardProps) {
  const borderColor = DIMENSION_COLORS[dimension.key] || "border-gray-300";
  const icon = DIMENSION_ICONS[dimension.key];
  const descriptionField = dimension.fields.find(f => f.key === "description");
  const description = descriptionField?.value || "";
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(description);

  const handleSave = () => {
    onFieldChange(dimension.key, "description", draft);
    setEditing(false);
  };

  const handleCancel = () => {
    setDraft(description);
    setEditing(false);
  };

  return (
    <div className={`rounded-lg border border-gray-200 bg-white shadow-sm border-l-4 ${borderColor}`}>
      <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3">
        {icon}
        <h3 className="text-sm font-semibold text-gray-800">{dimension.label}</h3>
      </div>
      <div className="px-4 py-3">
        {editing ? (
          <div className="space-y-2">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              rows={3}
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={handleCancel}
                className="rounded-md px-3 py-1 text-xs text-gray-500 hover:bg-gray-100"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                className="rounded-md bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700"
              >
                保存
              </button>
            </div>
          </div>
        ) : (
          <div
            onClick={() => { setDraft(description); setEditing(true); }}
            className="cursor-pointer rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors min-h-[3rem]"
          >
            {description ? (
              <p>{description}</p>
            ) : (
              <p className="text-gray-400 italic">点击添加描述...</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
