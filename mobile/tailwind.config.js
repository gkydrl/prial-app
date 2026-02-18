/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,tsx}',
    './src/**/*.{js,ts,tsx}',
  ],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#6C47FF',
          light: '#8B6FFF',
          dark: '#5035CC',
        },
        success: '#22C55E',
        warning: '#F59E0B',
        danger: '#EF4444',
        surface: '#1A1A2E',
        card: '#16213E',
        border: '#2D2D4A',
        muted: '#6B7280',
      },
      fontFamily: {
        sans: ['System'],
      },
    },
  },
  plugins: [],
};
