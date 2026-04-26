import Button from "../common/Button";

interface RequirementSummaryProps {
  dimensionCount: number;
  version: number;
  onProceed: () => void;
  onBack: () => void;
}

export default function RequirementSummary({
  dimensionCount,
  version,
  onProceed,
  onBack,
}: RequirementSummaryProps) {
  return (
    <div className="shrink-0 border-t border-gray-200 bg-white px-6 py-3">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">
            共{dimensionCount}个维度
          </span>
          <span className="text-xs text-gray-400">版本 v{version}</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={onBack}>
            返回修改对话
          </Button>
          <Button variant="primary" onClick={onProceed}>
            查看候选方案
          </Button>
        </div>
      </div>
    </div>
  );
}
