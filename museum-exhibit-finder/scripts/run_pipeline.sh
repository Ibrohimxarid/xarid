#!/usr/bin/env bash
# Full research run.
#   scripts/run_pipeline.sh [label] [--discover]
# Without --discover only the offline knowledge-base steps run
# (validate → dedupe → build → export → report).
set -euo pipefail
cd "$(dirname "$0")/.."
LABEL="${1:-run}"
if [[ "${2:-}" == "--discover" ]]; then
  mef search --limit "${MEF_QUERY_LIMIT:-80}"
  mef collect --min-relevance 2 --limit "${MEF_PAGE_LIMIT:-100}"
  mef triage --min-relevance 3
  echo "Review drafts in research/inbox/ and move verified files to research/museums/."
fi
mef all --label "$LABEL"
