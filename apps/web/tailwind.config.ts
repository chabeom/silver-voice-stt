import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: "#f9faf4",
          panel: "#ffffff",
          ink: "#0f172a",
          accent: "#0369a1",
          accentSoft: "#e0f2fe",
          alert: "#b91c1c",
          alertSoft: "#ffe4e6"
        }
      },
      fontSize: {
        base: ["18px", "1.6"],
        lg: ["20px", "1.6"],
        xl: ["24px", "1.4"],
        "2xl": ["32px", "1.3"]
      }
    }
  },
  plugins: []
};

export default config;

