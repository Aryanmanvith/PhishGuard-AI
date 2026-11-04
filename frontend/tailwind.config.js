/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Dark navy palette used for backgrounds, borders and surfaces.
        ink: {
          950: '#070d1a',
          900: '#0b1426',
          800: '#101c33',
          700: '#18284a',
          600: '#22365f',
          500: '#33497a',
        },
        accent: { DEFAULT: '#22d3ee', soft: '#67e8f9', dim: '#0e7490' },
      },
      fontFamily: {
        // System fonts only: no external font requests (privacy + offline friendly).
        sans: ['ui-sans-serif', 'system-ui', '"Segoe UI"', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', '"Cascadia Code"', 'Consolas', '"SF Mono"', 'Menlo', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(34, 211, 238, 0.25), 0 8px 30px -12px rgba(34, 211, 238, 0.35)',
      },
    },
  },
  plugins: [],
};
