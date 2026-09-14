/** @type {import('tailwindcss').Config} */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: v('void'),
        panel: v('panel'),
        panel2: v('panel2'),
        hairline: v('hairline'),
        bone: v('bone'),
        steel: v('steel'),
        signal: v('signal'),
        safe: v('safe'),
        danger: v('danger'),
        caution: v('caution'),
        'signal-dim': 'rgb(var(--signal) / 0.12)',
        'safe-dim': 'rgb(var(--safe) / 0.10)',
        'danger-dim': 'rgb(var(--danger) / 0.10)',
        'caution-dim': 'rgb(var(--caution) / 0.10)',
      },
      fontFamily: {
        display: ['"Archivo Black"', 'Archivo', '"Arial Black"', 'sans-serif'],
        sans: ['"Public Sans"', '"Segoe UI"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"IBM Plex Mono"', 'monospace'],
      },
      borderRadius: {
        sharp: '0px',
        card: '3px',
      },
      maxWidth: {
        page: '1440px',
      },
    },
  },
  plugins: [],
}
