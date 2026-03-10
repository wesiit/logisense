import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#E8EEF4",
          100: "#C5D4E3",
          200: "#9FB7D0",
          300: "#7899BC",
          400: "#5B82AD",
          500: "#3E6B9E",
          600: "#365D8A",
          700: "#2D4D72",
          800: "#243E5B",
          900: "#1A3C5E",
          950: "#0F2238",
        },
        accent: {
          blue: "#3B82F6",
          green: "#10B981",
          yellow: "#F59E0B",
          red: "#EF4444",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
