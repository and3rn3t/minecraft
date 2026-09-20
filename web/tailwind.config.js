/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Minecraft color palette
        minecraft: {
          grass: {
            light: '#7CB342',
            DEFAULT: '#558B2F',
            dark: '#33691E',
          },
          dirt: {
            light: '#8D6E63',
            DEFAULT: '#6D4C41',
            dark: '#5D4037',
          },
          stone: {
            light: '#9E9E9E',
            DEFAULT: '#757575',
            dark: '#616161',
          },
          water: {
            light: '#42A5F5',
            DEFAULT: '#2196F3',
            dark: '#1976D2',
          },
          background: {
            light: '#424242',
            DEFAULT: '#3E2723',
            dark: '#212121',
          },
          text: {
            light: '#FFFFFF',
            DEFAULT: '#E0E0E0',
            dark: '#BDBDBD',
          },
          // Red and orange were absent here despite 22 and 7 raw hex uses
          // across the JSX (#C62828, #F57C00 and their hover/border shades).
          // Values match the button/toast/StatusCard treatments already in
          // use, so defining them doesn't change how anything looks today.
          danger: {
            light: '#F44336',
            DEFAULT: '#C62828',
            dark: '#B71C1C',
          },
          warning: {
            light: '#FFB74D',
            DEFAULT: '#F57C00',
            dark: '#E65100',
          },
          // Semantic aliases of the material colors above, so a component
          // can say what it means (a success state) rather than which
          // material happens to render it (grass green). Same values.
          success: {
            light: '#7CB342',
            DEFAULT: '#558B2F',
            dark: '#33691E',
          },
          info: {
            light: '#42A5F5',
            DEFAULT: '#2196F3',
            dark: '#1976D2',
          },
        },
      },
      fontFamily: {
        // Display face: headings, nav, buttons, labels — the places a
        // blocky pixel font reads as intentional rather than illegible.
        minecraft: ['"Press Start 2P"', 'monospace'],
        pixel: ['"Press Start 2P"', 'monospace'],
        // Body face: everything read at length (copy, tables, values).
        // Keeps the retro character without sacrificing legibility.
        body: ['"VT323"', 'monospace'],
      },
      // A named scale to replace the ~285 arbitrary text-[8px]/text-[10px]
      // uses across the app. Sizes match what's already on screen; this
      // just gives pages a name to reach for instead of a raw pixel value.
      fontSize: {
        caption: ['8px', { lineHeight: '1.6' }],
        body: ['10px', { lineHeight: '1.8' }],
        label: ['11px', { lineHeight: '1.6' }],
        h2: ['16px', { lineHeight: '1.4' }],
        h1: ['20px', { lineHeight: '1.3' }],
        display: ['24px', { lineHeight: '1.3' }],
      },
      // `animate-pulse` needs no entry here — Tailwind's own default matches
      // the hand-rolled @keyframes pulse in index.css exactly, which is why
      // that one was safe to remove as dead weight. `fadeIn` is the one
      // that's used as a utility class (Dashboard.jsx, Login.jsx) but was
      // never registered, so `animate-fadeIn` has been silently emitting
      // nothing.
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        fadeIn: 'fadeIn 0.3s ease-out',
      },
      boxShadow: {
        // The glow behind each StatusCard status, hoisted from its inline
        // arbitrary-value classes so other components can reuse them.
        'glow-success': '0 0 15px rgba(124, 179, 66, 0.3)',
        'glow-danger': '0 0 15px rgba(198, 40, 40, 0.3)',
        'glow-warning': '0 0 15px rgba(245, 124, 0, 0.3)',
        'glow-info': '0 0 15px rgba(33, 150, 243, 0.3)',
      },
    },
  },
  plugins: [],
};
