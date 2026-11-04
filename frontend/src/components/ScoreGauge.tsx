import type { RiskCategory } from '../types/api';
import { CATEGORY_HEX, CATEGORY_LABEL } from '../utils/format';

interface Props {
  score: number;
  category: RiskCategory;
}

/** Semicircle gauge drawn with SVG. Shows a heuristic score, never a probability. */
export default function ScoreGauge({ score, category }: Props) {
  const clamped = Math.max(0, Math.min(100, score));
  const radius = 54;
  const arcLength = Math.PI * radius; // half circle
  const filled = (clamped / 100) * arcLength;
  const color = CATEGORY_HEX[category];
  return (
    <figure className="flex flex-col items-center" aria-label={`Heuristic risk score ${clamped} out of 100, ${CATEGORY_LABEL[category]}`}>
      <svg viewBox="0 0 140 80" className="w-48" role="img" aria-hidden="true">
        <path d="M 16 70 A 54 54 0 0 1 124 70" fill="none" stroke="#22365f" strokeWidth="12" strokeLinecap="round" />
        <path
          d="M 16 70 A 54 54 0 0 1 124 70"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${arcLength}`}
        />
        <text x="70" y="62" textAnchor="middle" fontSize="28" fontWeight="700" fill="#f1f5f9">
          {clamped}
        </text>
        <text x="70" y="76" textAnchor="middle" fontSize="8" fill="#94a3b8">
          / 100 heuristic
        </text>
      </svg>
      <figcaption className="mt-1 text-sm font-semibold" style={{ color }}>
        {CATEGORY_LABEL[category]}
      </figcaption>
    </figure>
  );
}
