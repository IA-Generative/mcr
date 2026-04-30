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
          1000: { DEFAULT: 'var(--grey-1000-50)' },
        },
        'blue-france': {
          sun: {
            DEFAULT: 'var(--blue-france-sun-113-625)',
            hover: 'var(--blue-france-sun-113-625-hover)',
            active: 'var(--blue-france-sun-113-625-active)',
          },
          main: 'var(--blue-france-main-525)',
          850: 'var(--blue-france-850-200)',
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
        'background-contrast-grey': 'var(--background-contrast-grey)',
        info: {
          425: { DEFAULT: 'var(--info-425-625)' },
          950: { DEFAULT: 'var(--info-950-100)' },
        },
        success: {
          425: { DEFAULT: 'var(--success-425-625)' },
          950: { DEFAULT: 'var(--success-950-100)' },
        },
        warning: {
          425: { DEFAULT: 'var(--warning-425-625)' },
          950: { DEFAULT: 'var(--warning-950-100)' },
        },
        error: {
          425: { DEFAULT: 'var(--error-425-625)' },
          950: { DEFAULT: 'var(--error-950-100)' },
        },
        'yellow-tournesol': {
          sun: 'var(--yellow-tournesol-sun-407-moon-922)',
          950: 'var(--yellow-tournesol-950-100)',
        },
        'purple-glycine': {
          sun: 'var(--purple-glycine-sun-319-moon-630)',
          925: 'var(--purple-glycine-925-125)',
        },
        'beige-gris-galet': {
          950: 'var(--beige-gris-galet-950-100)',
        },
      },
      animation: {
        'ping-slow': 'ping 1.5s linear infinite',
      },
    },
  },
  plugins: [],
};
