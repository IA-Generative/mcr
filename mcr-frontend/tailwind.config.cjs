/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: 'var(--background-action-high-blue-france)',
        'body-grey': 'var(--grey-625-425)',
      },
      animation: {
        'ping-slow': 'ping 1.5s linear infinite',
      },
    },
  },
  plugins: [],
};
