/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172333",
        muted: "#66758a",
        paper: "#f5f7fa",
        brand: {
          DEFAULT: "#5267e8",
          dark: "#394dcc",
          soft: "#edf0ff",
        },
        mint: "#26a889",
      },
      boxShadow: {
        card: "0 16px 42px rgba(35, 50, 77, 0.08)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};