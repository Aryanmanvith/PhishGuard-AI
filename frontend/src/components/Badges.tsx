import type { RiskCategory, Severity } from '../types/api';
import { CATEGORY_BADGE, CATEGORY_LABEL, SEVERITY_BADGE } from '../utils/format';

export function RiskBadge({ category }: { category: RiskCategory }) {
  return <span className={`chip ${CATEGORY_BADGE[category]}`}>{CATEGORY_LABEL[category]}</span>;
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`chip capitalize ${SEVERITY_BADGE[severity]}`}>{severity}</span>;
}

export function DemoBadge() {
  return (
    <span
      className="chip bg-violet-400/10 text-violet-300 ring-violet-400/30"
      title="Synthetic example input, not a real detection"
    >
      Demo
    </span>
  );
}
