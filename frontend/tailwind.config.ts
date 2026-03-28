import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f5ff",
          100: "#e0eaff",
          500: "#4f6df5",
          600: "#3b5bdb",
          700: "#2b4acb",
          900: "#1a2f8a",
        },
      },
    },
  },
  plugins: [],
};
export default config;
