#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
QUALITY_DIR="${REPO_ROOT}/artifacts/quality"
LOCAL_DIR="${REPO_ROOT}/artifacts/local"

mkdir -p "${QUALITY_DIR}" "${LOCAL_DIR}"

cd "${REPO_ROOT}"
python optimize_local.py "$@"

echo "Optimize finished. Key artifacts:"
echo "  ${LOCAL_DIR}/list.local.txt"
echo "  ${LOCAL_DIR}/list.local.yml"
echo "  ${LOCAL_DIR}/list.local.meta.yml"
echo "  ${LOCAL_DIR}/snippets/nodes.local.yml"
echo "  ${LOCAL_DIR}/snippets/nodes.local.meta.yml"
echo "  ${QUALITY_DIR}/summary.md"
echo "  ${QUALITY_DIR}/top_nodes.csv"
echo "  ${QUALITY_DIR}/filter_reasons.csv"
echo "  ${QUALITY_DIR}/source_reputation.csv"
