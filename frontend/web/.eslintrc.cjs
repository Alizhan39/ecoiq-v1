module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  plugins: ['@typescript-eslint', 'react-hooks'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
  ],
  rules: {
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    // The evidence contract, enforced by the linter rather than by review.
    'no-restricted-syntax': [
      'error',
      {
        selector:
          "LogicalExpression[operator='??'][right.value=0]",
        message:
          'Coalescing a null score to 0 fabricates a measurement. Branch on score_status instead.',
      },
      {
        selector:
          "LogicalExpression[operator='??'][right.value=50]",
        message:
          'Coalescing to 50 invents an average. Branch on score_status instead.',
      },
    ],
  },
  ignorePatterns: ['dist', 'node_modules', '*.config.ts'],
};
