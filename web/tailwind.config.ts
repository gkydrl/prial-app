import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: "#1D4ED8",
        "brand-light": "#3B82F6",
        "brand-dark": "#1E3A8A",
        surface: "#F9FAFB",
        success: "#16A34A",
        danger: "#DC2626",
        bekle: "#F59E0B",
        "bekle-dark": "#D97706",
      },
    },
  },
  plugins: [],
};

export default config;
