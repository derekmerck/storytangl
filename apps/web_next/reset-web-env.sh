#!/bin/bash
# Reset web client environment to clean slate

echo "🧹 Cleaning web client environment..."

cd apps/web

# Remove all generated/cached files
echo "  Removing node_modules..."
rm -rf node_modules

echo "  Removing lockfile..."
rm -f yarn.lock package-lock.json

echo "  Removing build artifacts..."
rm -rf dist .vite

echo "  Removing test coverage..."
rm -rf coverage

echo "  Removing IDE files..."
rm -rf .idea .vscode

echo "✅ Environment reset complete!"
echo ""
echo "Next steps:"
echo "  1. Update package.json dependencies"
echo "  2. Run: yarn install"
echo "  3. Run: yarn dev"
