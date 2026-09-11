#!/usr/bin/env bash
# Prepare a Hugging Face Space repo from this project.
#
#   ./tools/prepare_space.sh gradio  <target-dir>   # free for everyone
#   ./tools/prepare_space.sh docker  <target-dir>   # needs Docker SDK enabled
#
# Then:  cd <target-dir> && git init && git remote add origin \
#        https://huggingface.co/spaces/<user>/<space> && git add . \
#        && git commit -m "capstone" && git push origin main
set -euo pipefail
SDK="${1:-gradio}"
DEST="${2:-../qtcap-space}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"

case "$SDK" in gradio|docker) ;; *) echo "usage: $0 [gradio|docker] [target-dir]"; exit 1 ;; esac

echo "Preparing a $SDK Space in $DEST"
mkdir -p "$DEST"
# Everything the app needs at runtime. Tests ride along so the in-browser test
# runner works; the knowledge base is the corpus the RAG app answers from.
for item in app tests knowledge_base tools docs pytest.ini healthcheck.py; do
  cp -r "$SRC/$item" "$DEST/"
done
rm -rf "$DEST"/**/__pycache__ 2>/dev/null || true

if [ "$SDK" = "gradio" ]; then
  cp "$SRC/space_app.py" "$DEST/"
  cp "$SRC/space.gradio.README.md" "$DEST/README.md"
  cp "$SRC/requirements-space.txt" "$DEST/requirements.txt"
  # The Space installs from requirements.txt, which must be self-contained.
  sed -i.bak 's|^-r requirements.txt$||' "$DEST/requirements.txt" && rm -f "$DEST/requirements.txt.bak"
  cat "$SRC/requirements.txt" >> "$DEST/requirements.txt"
else
  cp "$SRC/Dockerfile" "$SRC/.dockerignore" "$DEST/"
  cp "$SRC/space.docker.README.md" "$DEST/README.md"
  cp "$SRC/requirements.txt" "$DEST/"
fi

echo
echo "Done. Next:"
echo "  cd $DEST"
echo "  git init && git add . && git commit -m 'Capital Markets Agentic Capstone'"
echo "  git remote add origin https://huggingface.co/spaces/<your-user>/<space-name>"
echo "  git push origin main"
