module.exports = {
    presets: [
        ['@babel/preset-env', { targets: { node: 'current' } }],
        '@babel/preset-typescript', // for TypeScript
        '@vue/babel-preset-app' // or '@vue/babel-preset-jsx'
    ],
};