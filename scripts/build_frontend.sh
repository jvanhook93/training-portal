#!/usr/bin/env bash
set -euo pipefail

echo "== Building frontend =="
cd frontend

# install deps
npm ci

# build (Vite output -> frontend/dist)
npm run build

cd ..

echo "== Copying build to Django static/app =="
rm -rf static/app
mkdir -p static/app
cp -r frontend/dist/* static/app/

echo "== Done =="
