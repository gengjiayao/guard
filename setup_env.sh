#!/usr/bin/env bash
# setup_env.sh — restore the build environment for this repo.
#
# Why this exists: waf 1.7.11 (NS-3 19's bootstrapper) embeds a bz2 archive
# that Python 3 mis-parses ("source code cannot contain null bytes"), so
# `./waf` must run under Python 2.7.18. The runtime scripts (run.py,
# fctAnalysis.py …) are still Python 3 — only `./waf` itself needs Py2.
# This script installs pyenv + Python 2.7.18 idempotently and pins the
# repo to 2.7.18 so `python waf` resolves correctly.
#
# Usage:
#   bash setup_env.sh                # install pyenv + 2.7.18 + pin repo
#   bash setup_env.sh build          # ... and run `waf configure && waf`
#   bash setup_env.sh build smoke    # ... and run a tiny --cc guard smoke
#
# After running once, future shells can do:
#   export PATH="$HOME/.pyenv/shims:$PATH"
# (or source the lines pyenv.run prints into your ~/.bashrc once.)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
PY_VERSION="2.7.18"

echo "[setup] repo=$REPO_DIR  pyenv_root=$PYENV_ROOT  python=$PY_VERSION"

# ---------------------------------------------------------------------------
# 1. apt build deps for compiling Python 2.7.18 from source.
#    Skip silently if dpkg / apt-get are unavailable (e.g. non-Debian host).
# ---------------------------------------------------------------------------
need_apt=()
for pkg in libssl-dev libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev \
           libffi-dev libncurses-dev liblzma-dev tk-dev make gcc curl git; do
    if command -v dpkg >/dev/null && ! dpkg -s "$pkg" >/dev/null 2>&1; then
        need_apt+=("$pkg")
    fi
done
if [ "${#need_apt[@]}" -gt 0 ]; then
    echo "[setup] apt installing missing build deps: ${need_apt[*]}"
    sudo apt-get update -y >/dev/null
    sudo apt-get install -y "${need_apt[@]}"
fi

# ---------------------------------------------------------------------------
# 2. pyenv (idempotent)
# ---------------------------------------------------------------------------
if [ ! -x "$PYENV_ROOT/bin/pyenv" ]; then
    echo "[setup] installing pyenv to $PYENV_ROOT ..."
    curl -fsSL https://pyenv.run | bash
fi
export PYENV_ROOT
export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"
eval "$(pyenv init - bash)"

# ---------------------------------------------------------------------------
# 3. Python 2.7.18 (idempotent — pyenv install --skip-existing also works)
# ---------------------------------------------------------------------------
if ! pyenv versions --bare | grep -qx "$PY_VERSION"; then
    echo "[setup] installing Python $PY_VERSION via pyenv (~5 min) ..."
    pyenv install "$PY_VERSION"
fi

# ---------------------------------------------------------------------------
# 4. pin the repo to 2.7.18 (writes .python-version)
# ---------------------------------------------------------------------------
cd "$REPO_DIR"
pyenv local "$PY_VERSION"
echo "[setup] python --version → $(python --version 2>&1)  (expected $PY_VERSION)"

# ---------------------------------------------------------------------------
# 5. optional: build
# ---------------------------------------------------------------------------
if [ "${1:-}" = "build" ] || [ "${2:-}" = "build" ]; then
    if [ ! -d build ] || [ ! -f .lock-waf_linux ]; then
        echo "[setup] running waf configure ..."
        python waf configure --build-profile=optimized --enable-mpi --disable-gtk
    fi
    echo "[setup] running waf build ..."
    python waf
fi

# ---------------------------------------------------------------------------
# 6. optional: tiny smoke (--cc guard, leaf_spine_8, 25% load, 0.01s)
# ---------------------------------------------------------------------------
if [ "${1:-}" = "smoke" ] || [ "${2:-}" = "smoke" ]; then
    rm -rf mix/output/*
    python3 run.py --cc guard --lb fecmp --pfc 1 --irn 0 \
                   --simul_time 0.01 --netload 25 \
                   --topo leaf_spine_8_100G_OS1
    last_id=$(ls mix/output/ | head -1)
    echo "[setup] FCT summary for $last_id:"
    head -5 "mix/output/$last_id"/*_fct_summary.txt
fi

echo "[setup] done. To re-enter this env in a new shell:"
echo "        export PATH=\"$PYENV_ROOT/shims:\$PATH\""
