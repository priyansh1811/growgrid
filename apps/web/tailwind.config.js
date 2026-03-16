/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Instrument Serif', 'Georgia', 'serif'],
      },
      colors: {
        forest: {
          DEFAULT: '#0D2B1A',
          light: '#122B1C',
        },
        cream: '#F5F2EC',
        'card-dark': '#162E20',
        'footer-dark': '#071610',
        'text-on-dark': '#E8F5E9',
        'text-muted-dark': '#9EAFA3',
        'accent-gold': {
          DEFAULT: '#C8956C',
          light: '#D4A574',
          dark: '#B07D54',
        },
        primary: {
          50: '#f0f7f2',
          100: '#dceee2',
          200: '#b8dcc5',
          300: '#93C5A4',
          400: '#6BA67E',
          500: '#4A8C62',
          600: '#3A7050',
          700: '#2D5A3F',
          800: '#1E4530',
          900: '#143323',
        },
        surface: { 50: '#f8fafc', 100: '#f1f5f9', 200: '#e2e8f0', 300: '#cbd5e1', 400: '#94a3b8', 500: '#64748b' },
        hero: {
          bg: '#0a0f0a',
          'bg-light': '#111a11',
          lime: '#8BB85C',
          'lime-dim': '#6A9040',
          gold: '#c8a97e',
          'gold-dim': '#a08560',
          text: '#f0f0ec',
          'text-muted': '#9ca38c',
          'field-warm': '#2a1f0a',
          'field-amber': '#c9a050',
        },
      },
    },
  },
  plugins: [],
}
