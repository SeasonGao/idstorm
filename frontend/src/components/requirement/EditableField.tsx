import { useState, useRef, useEffect } from "react";
import type { DimensionField } from "../../types";

interface EditableFieldProps {
  field: DimensionField;
  onSave: (key: string, value: string) => void;
}

export default function EditableField({ field, onSave }: EditableFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(field.value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const handleSave = () => {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== field.value) {
      onSave(field.key, trimmed);
    } else {
      setDraft(field.value);
    }
    setEditing(false);
  };

  const handleCancel = () => {
    setDraft(field.value);
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") handleCancel();
  };

  return (
    <div className="group">
      <label className="mb-1 block text-xs font-medium text-gray-500">
        {field.label}
      </label>
      {editing ? (
        <div className="flex items-center gap-1">
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleSave}
            className="flex-1 rounded border border-blue-400 px-2 py-1 text-sm text-gray-800 outline-none focus:ring-1 focus:ring-blue-400"
          />
          <button
            onClick={handleSave}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-green-600 hover:bg-green-50"
            title="保存"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </button>
          <button
            onMouseDown={(e) => { e.preventDefault(); handleCancel(); }}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-red-500 hover:bg-red-50"
            title="取消"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      ) : (
        <div
          onClick={() => {
            if (field.editable) {
              setDraft(field.value);
              setEditing(true);
            }
          }}
          className={`rounded px-2 py-1 text-sm ${
            field.editable
              ? "cursor-pointer text-gray-800 hover:bg-blue-50"
              : "text-gray-600"
          }`}
        >
          {field.value || <span className="text-gray-400 italic">未填写</span>}
        </div>
      )}
    </div>
  );
}
