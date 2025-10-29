# next-init.sh
#!/usr/bin/env bash
yes "" | npx create-next-app@latest __out__/"$1" \
  --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
