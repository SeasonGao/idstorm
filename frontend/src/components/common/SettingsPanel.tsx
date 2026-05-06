import { useEffect, useState } from "react";
import apiClient from "../../api/client";
import Button from "../common/Button";

interface MaskedKeys {
  deepseek_api_key: string;
  doubao_api_key: string;
  openai_api_key: string;
}

interface KeyField {
  key: keyof MaskedKeys;
  label: string;
  placeholder: string;
}

const KEY_FIELDS: KeyField[] = [
  { key: "deepseek_api_key", label: "DeepSeek API Key", placeholder: "sk-..." },
  { key: "doubao_api_key", label: "豆包 API Key", placeholder: "留空则使用默认配置" },
  { key: "openai_api_key", label: "OpenAI API Key", placeholder: "sk-..." },
];

export default function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [keys, setKeys] = useState<Record<string, string>>({
    deepseek_api_key: "",
    doubao_api_key: "",
    openai_api_key: "",
  });
  const [masked, setMasked] = useState<MaskedKeys | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get("/config/keys").then((res) => {
      setMasked(res.data);
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const payload: Record<string, string> = {};
      for (const f of KEY_FIELDS) {
        if (keys[f.key].trim()) {
          payload[f.key] = keys[f.key].trim();
        }
      }
      if (Object.keys(payload).length === 0) {
        setMessage("未填写任何新密钥");
        setSaving(false);
        return;
      }
      const res = await apiClient.post("/config/keys", payload);
      setMasked(res.data);
      setKeys({ deepseek_api_key: "", doubao_api_key: "", openai_api_key: "" });
      setMessage("保存成功");
    } catch {
      setMessage("保存失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-800">API Key 配置</h3>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p className="mb-4 text-xs text-gray-500">
          配置你自己的 API Key，留空则使用服务器默认配置。密钥保存在本地服务器，不会上传。
        </p>

        <div className="space-y-4">
          {KEY_FIELDS.map((f) => (
            <div key={f.key}>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                {f.label}
              </label>
              {masked && masked[f.key] && (
                <p className="mb-1 text-xs text-gray-400">
                  当前：{masked[f.key]}
                </p>
              )}
              <input
                type="password"
                value={keys[f.key]}
                onChange={(e) => setKeys((prev) => ({ ...prev, [f.key]: e.target.value }))}
                placeholder={f.placeholder}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          ))}
        </div>

        {message && (
          <p className={`mt-3 text-sm ${message === "保存成功" ? "text-green-600" : "text-red-600"}`}>
            {message}
          </p>
        )}

        <div className="mt-5 flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            关闭
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "保存中..." : "保存"}
          </Button>
        </div>
      </div>
    </div>
  );
}
