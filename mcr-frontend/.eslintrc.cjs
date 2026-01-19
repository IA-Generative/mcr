/* eslint-env node */
require('@rushstack/eslint-patch/modern-module-resolution');

module.exports = {
  root: true,
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    '@vue/eslint-config-typescript',
    '@vue/eslint-config-prettier/skip-formatting',
  ],
  rules: {
    'comma-dangle': ['error', 'always-multiline'],
    'no-irregular-whitespace': 1,
    'vue/block-lang': [
      'error',
      {
        script: {
          lang: 'ts',
        },
      },
    ],
    'vue/block-order': 'error',
  },
  parserOptions: {
    ecmaVersion: 'latest',
  },
  plugins: ['testing-library'],
  overrides: [
    {
      files: ['**/__tests__/**/*.[jt]s?(x)', '**/*.spec.[jt]s?(x)', '**/*.test.[jt]s?(x)'],
      extends: ['plugin:testing-library/vue'],
    },
  ],
};
