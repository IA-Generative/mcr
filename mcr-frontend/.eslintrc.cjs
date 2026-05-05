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
  plugins: ['testing-library', 'local-rules'],
  overrides: [
    {
      files: ['eslint-local-rules/**/*.js'],
      env: { node: true },
      rules: { 'no-undef': 'off' },
    },
    {
      files: ['**/__tests__/**/*.[jt]s?(x)', '**/*.spec.[jt]s?(x)', '**/*.test.[jt]s?(x)'],
      extends: ['plugin:testing-library/vue'],
      rules: {
        'no-restricted-syntax': 'off',
        'local-rules/no-vi-fn-outside-hoisted': 'error',
      },
    },
  ],
};
