// Tiny inline icon set (Feather-style outlines). Inline SVG = no icon library to install.
const PATHS = {
  shield: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'],
  grid: ['M3 3h7v7H3z', 'M14 3h7v7h-7z', 'M14 14h7v7h-7z', 'M3 14h7v7H3z'],
  link: [
    'M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71',
    'M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71',
  ],
  mail: ['M3 5h18v14H3z', 'M21 7l-9 6-9-6'],
  history: ['M12 2a10 10 0 100 20 10 10 0 000-20z', 'M12 6v6l4 2'],
  cpu: ['M5 5h14v14H5z', 'M9 9h6v6H9z', 'M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3'],
  menu: ['M3 6h18M3 12h18M3 18h18'],
  close: ['M18 6L6 18M6 6l12 12'],
  download: ['M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4', 'M7 10l5 5 5-5', 'M12 15V3'],
  trash: ['M3 6h18', 'M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2', 'M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6'],
  check: ['M22 11.08V12a10 10 0 11-5.93-9.14', 'M22 4L12 14.01l-3-3'],
  alert: [
    'M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z',
    'M12 9v4M12 17h.01',
  ],
  info: ['M12 2a10 10 0 100 20 10 10 0 000-20z', 'M12 16v-4M12 8h.01'],
  arrow: ['M5 12h14M12 5l7 7-7 7'],
  refresh: ['M23 4v6h-6M1 20v-6h6', 'M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15'],
  lock: ['M5 11h14v10H5z', 'M7 11V7a5 5 0 0110 0v4'],
  search: ['M11 3a8 8 0 100 16 8 8 0 000-16z', 'M21 21l-4.35-4.35'],
} as const;

export type IconName = keyof typeof PATHS;

interface IconProps {
  name: IconName;
  className?: string;
}

export default function Icon({ name, className = 'h-5 w-5' }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {(PATHS[name] as readonly string[]).map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}
