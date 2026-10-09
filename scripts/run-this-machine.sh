#!/bin/sh
set -eu
FARESCOUT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FARESCOUT_WORK="$FARESCOUT_ROOT/../../work"
cd "$FARESCOUT_ROOT"
export PYTHONPATH="$FARESCOUT_ROOT/src"
export PYTHONDONTWRITEBYTECODE=1
FARESCOUT_PYTHON_BIN="${FARESCOUT_PYTHON:-$FARESCOUT_ROOT/.venv/bin/python}"
if [ -z "${FARESCOUT_PYTHON:-}" ] && [ ! -x "$FARESCOUT_PYTHON_BIN" ]; then
  if [ -x /private/tmp/farescout-p1-venv/bin/python ]; then
    FARESCOUT_PYTHON_BIN=/private/tmp/farescout-p1-venv/bin/python
  elif [ -x /private/tmp/farescout-poc-venv/bin/python ]; then
    FARESCOUT_PYTHON_BIN=/private/tmp/farescout-poc-venv/bin/python
  else
    FARESCOUT_PYTHON_BIN=$FARESCOUT_WORK/venv/bin/python
  fi
fi
if [ ! -x "$FARESCOUT_PYTHON_BIN" ]; then
  echo '本机临时虚拟环境已不存在，请按 README 创建 .venv 并设置 FARESCOUT_PYTHON。' >&2
  exit 2
fi
# FlyAI uses /usr/bin/env node. Desktop-launched shells may have a different
# PATH from the terminal; allow an explicit runtime without hardcoding it.
FARESCOUT_NODE_RUNTIME=${FARESCOUT_NODE_BIN:-$(
  "$FARESCOUT_PYTHON_BIN" -c 'from dotenv import dotenv_values; print(dotenv_values(".env").get("FARESCOUT_NODE_BIN", ""))'
)}
if [ -n "$FARESCOUT_NODE_RUNTIME" ]; then
  if [ ! -x "$FARESCOUT_NODE_RUNTIME" ]; then
    echo 'FARESCOUT_NODE_BIN 必须指向可执行的 Node 文件，请检查本机 .env。' >&2
    exit 2
  fi
  export PATH="$(dirname -- "$FARESCOUT_NODE_RUNTIME"):$PATH"
fi
if [ -z "${SOCAI_BIN:-}" ]; then
  FARESCOUT_SOCBIN_CONFIG=$(
    "$FARESCOUT_PYTHON_BIN" -c 'from dotenv import dotenv_values; print(dotenv_values(".env").get("SOCAI_BIN", ""))'
  )
  if [ -n "$FARESCOUT_SOCBIN_CONFIG" ] && [ "$FARESCOUT_SOCBIN_CONFIG" != socai ]; then
    SOCAI_BIN=$FARESCOUT_SOCBIN_CONFIG
  elif [ -x "$FARESCOUT_WORK/socai/socai" ]; then
    SOCAI_BIN=$FARESCOUT_WORK/socai/socai
  else
    SOCAI_BIN=socai
  fi
  export SOCAI_BIN
fi
if [ -z "${FLYAI_BIN:-}" ]; then
  FARESCOUT_FLYBIN_CONFIG=$(
    "$FARESCOUT_PYTHON_BIN" -c 'from dotenv import dotenv_values; print(dotenv_values(".env").get("FLYAI_BIN", ""))'
  )
  if [ -n "$FARESCOUT_FLYBIN_CONFIG" ] && [ "$FARESCOUT_FLYBIN_CONFIG" != flyai ]; then
    FLYAI_BIN=$FARESCOUT_FLYBIN_CONFIG
  elif [ -x "$FARESCOUT_WORK/flyai-local/node_modules/@fly-ai/flyai-cli/dist/flyai-bundle.cjs" ]; then
    FLYAI_BIN=$FARESCOUT_WORK/flyai-local/node_modules/@fly-ai/flyai-cli/dist/flyai-bundle.cjs
  else
    FLYAI_BIN=flyai
  fi
  export FLYAI_BIN
fi
if [ -z "${NODE_EXTRA_CA_CERTS:-}" ] && [ -f "$FARESCOUT_WORK/system-ca.pem" ]; then
  export NODE_EXTRA_CA_CERTS="$FARESCOUT_WORK/system-ca.pem"
fi
export NODE_TLS_REJECT_UNAUTHORIZED=1
exec "$FARESCOUT_PYTHON_BIN" -m farescout.cli "$@"
