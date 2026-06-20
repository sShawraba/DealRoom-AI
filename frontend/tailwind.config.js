/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          cream:  '#FAF9F5',
          warm:   '#F2EDE3',
          sand:   '#E8E2D0',
          taupe:  '#B8AF9C',
          ink:    '#14211A',
          green:  '#1A5E3A',
          forest: '#123D26',
          gold:   '#D4A84B',
        },
      },
    },
  },
  plugins: [],
};
