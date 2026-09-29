#!/usr/bin/env bash
# deploy.sh -- tcos.app: build, gate, lab, promote. Two explicit steps, never
# one (HEE_POLICY 17). Modeled on tcos-www's deploy.sh; drive it with
# `hee release -lab | -cut | -promote`, not by hand.
#
#   ./deploy.sh lab       regenerate index.html from apps.yaml, gate, push to
#                         app.lab.tcos.us via .github's Makefile (lab-tcos-app)
#   ./deploy.sh promote   gate the COMMITTED page (no rebuild), deploy the
#                         tcos-app Worker with the session signature on the
#                         version, verify, record a GPG-signed prod/tcos-app/<v>
#
# Requires: hee on PATH, ~/git/.github (lab), and for promote the sealed token
# via `hee cred -pass cloudflare-tcos-www -dir <dir> -exec` (see the card).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cmd="${1:-}"
[ "$cmd" = lab ] || [ "$cmd" = promote ] || { echo "usage: $0 lab|promote" >&2; exit 1; }
PAGES=(index.html)
ASSET_DIRS=(css)
ASSET_FILES=(robots.txt)
HOST=tcos.app

cd "$HERE"
if [ "$cmd" = promote ]; then
  # Prod deploys a commit that is on main; checked first so a refusal leaves
  # the tree exactly as it was.
  if [ -n "$(git status --porcelain -- "${PAGES[@]}" apps.yaml generate-index.py "${ASSET_DIRS[@]}" "${ASSET_FILES[@]}")" ]; then
    echo "❌ CRITICAL promote: uncommitted changes in what would ship -- run ./deploy.sh lab, commit, merge; prod deploys a commit" >&2; exit 2
  fi
  git fetch -q origin main
  if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    echo "❌ CRITICAL promote: HEAD $(git rev-parse --short HEAD) is not origin/main $(git rev-parse --short origin/main) -- git switch main && git pull" >&2; exit 2
  fi
  echo "=== promote: committed page at $(git rev-parse --short HEAD) (origin/main), no rebuild ==="
else
  echo "=== build (apps.yaml -> index.html) ==="
  python3 generate-index.py
fi
echo "=== gates ==="
python3 generate-index.py --check || { echo "❌ CRITICAL deploy: index.html is not what apps.yaml generates -- stopping" >&2; exit 2; }
hee check all "$HERE" >/dev/null 2>&1 || { echo "❌ CRITICAL deploy: hee check all fails -- stopping" >&2; exit 2; }
if grep -l -E '^(<<<<<<< |=======$|>>>>>>> )' "${PAGES[@]}" 2>/dev/null | grep -q .; then
  echo "❌ CRITICAL deploy: git conflict markers in generated pages -- stopping" >&2; exit 2
fi
echo "  index matches apps.yaml; hee check all: OK; no conflict markers"

if [ "$cmd" = lab ]; then
  make -C "$HOME/git/.github" lab-tcos-app TCOS_APP="$HERE" >/dev/null
  printf '  app.lab.tcos.us/  %s\n' "$(curl -s -o /dev/null -w '%{http_code}' https://app.lab.tcos.us/)"
  echo "=== lab updated -- review https://app.lab.tcos.us, then hee release -cut ==="
  exit 0
fi

SIG="$(hee ver session --tag 2>/dev/null || hee ver session 2>/dev/null | awk '/sig_tag|rc_tag/{print $2; exit}')"
[ -n "$SIG" ] || { echo "❌ CRITICAL promote: no session signature from hee ver session" >&2; exit 2; }
SRC_SHA="$(git rev-parse --short HEAD)"
STAMP="${RELEASE_VERSION:-$(date -u +%Y%m%dT%H%MZ)}"
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
cp "${PAGES[@]}" "${ASSET_FILES[@]}" "$STAGE/" && cp -r "${ASSET_DIRS[@]}" "$STAGE/"
# wrangler needs Node >= 20; with older Node it prints one line and exits 1,
# which the grep below would swallow.
node_major="$(node -v 2>/dev/null | sed 's/^v//; s/\..*//')"
[ "${node_major:-0}" -ge 20 ] || { echo "❌ CRITICAL promote: Node >= 20 required, found $(node -v 2>/dev/null || echo none)" >&2; exit 2; }
# hee cred -exec injects the secret as HEE_CRED_PASS; wrangler wants CLOUDFLARE_API_TOKEN.
CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-${HEE_CRED_PASS:-}}"; export CLOUDFLARE_API_TOKEN
: "${CLOUDFLARE_API_TOKEN:?run via hee release -promote (hee cred -exec)}"
CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-$(curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" https://api.cloudflare.com/client/v4/accounts | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"][0]["id"])')}"
export CLOUDFLARE_ACCOUNT_ID
echo "=== promote: tcos-app worker, src=$SRC_SHA session=$SIG ==="
( cd "$STAGE" && npx --yes wrangler@4.86.0 deploy --name tcos-app --assets . --compatibility-date=2026-08-15 \
    --message "hee:$SIG tcos-app src=$SRC_SHA" --tag "${SIG%%_*}" 2>&1 | grep -E 'Success|rror|requires'; exit "${PIPESTATUS[0]}" ) \
  || { echo "❌ CRITICAL promote: wrangler deploy failed -- nothing verified, nothing tagged" >&2; exit 2; }
echo "=== verify prod ==="
code="$(curl -s -o /dev/null -w '%{http_code}' "https://$HOST/")"
body="$(curl -s "https://$HOST/")"
markers="$(printf '%s\n' "$body" | grep -c -E '^(<<<<<<< |=======$|>>>>>>> )' || true)"
printf '  /  %s markers=%s\n' "$code" "$markers"
if [ "$code" != 200 ] || [ "$markers" != 0 ]; then
  echo "❌ CRITICAL promote: prod verification failed -- fix forward or redeploy the previous commit" >&2; exit 2
fi
TAG="prod/tcos-app/$STAMP"
hee git tag "$TAG" -m "prod promotion: $HOST
worker: tcos-app
source: $SRC_SHA
session: $SIG
verified: / 200, no conflict markers" "$SRC_SHA" --yes --push \
  || { echo "⚠️ WARNING promote: deployed and verified, but the prod tag could not be created/pushed -- hee git tag $TAG -m ... $SRC_SHA --yes --push" >&2; }
