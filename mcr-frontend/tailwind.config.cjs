/* eslint-env node */
/** @type {import('tailwindcss').Config} */

module.exports = {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        grey: {
          200:  'var(--grey-200-850)',
          625:  'var(--grey-625-425)',
          900:  'var(--grey-900-175)',
          950:  { DEFAULT: 'var(--grey-950-100)' },
          1000: { DEFAULT: 'var(--grey-1000-100)' },
        },
        "blue-france": {
          sun: {
            DEFAULT: 'var(--blue-france-sun-113-625)',     // primary
            hover: 'var(--blue-france-sun-113-625-hover)',
            active: 'var(--blue-france-sun-113-625-active)',
          },
          main: 'var(--blue-france-main-525)',             // mid
          850: 'var(--blue-france-850-200)',               // soft
          925: {
            DEFAULT: 'var(--blue-france-925-125)',
            hover: 'var(--blue-france-925-125-hover)',
            active: 'var(--blue-france-925-125-active)',
          },
          950: {
            DEFAULT: 'var(--blue-france-950-100)',
            hover: 'var(--blue-france-950-100-hover)',
            active: 'var(--blue-france-950-100-active)',
          },
          975: {
            DEFAULT: 'var(--blue-france-975-75)',
            hover: 'var(--blue-france-975-75-hover)',
            active: 'var(--blue-france-975-75-active)',
          },
        },
        primary: 'var(--background-action-high-blue-france)',
        'body-grey': 'var(--grey-625-425)',
        'warning-bg': 'var(--warning-950-100)',
        'warning-text': 'var(--warning-425-625)',
        'info-bg': 'var(--info-950-100)',
        'info-text': 'var(--info-425-625)',
      },
      animation: {
        'ping-slow': 'ping 1.5s linear infinite',
      },
    },
  },
  plugins: [],
};
