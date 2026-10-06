#!/bin/sh
# Build an optional diagnostic binary. Never replaces or stops a running daemon.
set -eu
FARESCOUT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FARESCOUT_BUILD=${1:?Usage: build-socai-diagnostic.sh EMPTY_BUILD_DIRECTORY}
command -v cargo >/dev/null
command -v python3 >/dev/null
if [ -e "$FARESCOUT_BUILD/source" ]; then
  echo '构建目录已有 source，请选择新的空目录，避免改动已有源码。' >&2
  exit 2
fi
mkdir -p "$FARESCOUT_BUILD/source"
curl -fL --connect-timeout 15 --max-time 180 \
  https://codeload.github.com/socai-io/socai/tar.gz/refs/tags/v0.6.1 \
  -o "$FARESCOUT_BUILD/socai-v0.6.1.tar.gz"
python3 - "$FARESCOUT_BUILD/socai-v0.6.1.tar.gz" <<'PY'
import hashlib, sys
from pathlib import Path
digest=hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()
if digest != 'c38fceaede690e00ba4537d07bd501fefe0a2d048fc4eaf4d0d7f77a09d9ead0':
    raise SystemExit('官方归档校验不一致；停止构建，不应用补丁。')
PY
tar -xzf "$FARESCOUT_BUILD/socai-v0.6.1.tar.gz" --strip-components=1 -C "$FARESCOUT_BUILD/source"
patch --batch -d "$FARESCOUT_BUILD/source" -p1 < "$FARESCOUT_ROOT/patches/socai/v0.6.1-websocket-terminal.patch"
patch --batch -d "$FARESCOUT_BUILD/source" -p1 < "$FARESCOUT_ROOT/patches/socai/v0.6.1-isolated-config.patch"
# The upstream tag's lockfile did not match its manifests. Keep the resolved
# dependency set from our successful diagnostic build, then require --locked.
cp "$FARESCOUT_ROOT/patches/socai/diagnostic-Cargo.lock" "$FARESCOUT_BUILD/source/Cargo.lock"
cargo build --locked -p socai-cli --manifest-path "$FARESCOUT_BUILD/source/Cargo.toml"
cargo test --locked -p socai-core --lib cdp::raw_client::transport_tests \
  --manifest-path "$FARESCOUT_BUILD/source/Cargo.toml" -- --test-threads=1
echo "诊断版已构建：$FARESCOUT_BUILD/source/target/debug/socai"
echo '尚未切换运行中的 daemon。配置与切换步骤见 docs/current/cdp-stability-acceptance.md。'
