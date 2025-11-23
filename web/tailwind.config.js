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
          wood: {
            light: '#8D6E63',
            DEFAULT: '#6D4C41',
            dark: '#5D4037',
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
        },
        primary: {
          // Keep primary for compatibility, but use Minecraft colors
          50: '#E8F5E9',
          100: '#C8E6C9',
          200: '#A5D6A7',
          300: '#81C784',
          400: '#66BB6A',
          500: '#558B2F', // Minecraft grass green
          600: '#7CB342',
          700: '#558B2F',
          800: '#33691E',
          900: '#1B5E20',
        },
      },
      fontFamily: {
        minecraft: ['"Press Start 2P"', 'monospace'],
        pixel: ['"Press Start 2P"', 'monospace'],
      },
    },
  },
  plugins: [],
};
