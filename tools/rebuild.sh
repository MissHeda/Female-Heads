#!/usr/bin/env bash
# Full rebuild: Blender steps (need an open Blender with the MCP bridge), textures, model, mod, animation check.
# usage (repo root, Git Bash): tools/rebuild.sh [from-step]   steps: base head bake tex export model
set -e
cd "$(dirname "$0")/.."
PY="E:/python/python.exe"; RUN="node $HOME/.claude/blender-bridge/run.js"
NODE="/c/Users/Heda/Desktop/Arma stuff/debin (neu)/node.exe"; ODOL="C:/Users/Heda/GitHub Repos/Arma-Modding-Tools-debin/tools/debin/odol.mjs"
steps=(base head bake tex export model); from=${1:-base}; go=0
bl() { $RUN "tools/blender/$1.py" 2>&1 | grep -v "INFO\|DEBUG\|WARN\|Baking map" | grep -i "$2" || true; }
for s in "${steps[@]}"; do
  [ "$s" = "$from" ] && go=1; [ $go = 1 ] || continue
  echo "== $s"
  case $s in
    base) bl base "missing\|error" ;;
    head) bl build_head "fit \|FH_head verts\|error" ;;
    bake) bl bake "error" ;;
    tex) $PY -I tools/compose_textures.py; powershell -NoProfile -ExecutionPolicy Bypass -File tools/make_paa.ps1 ;;
    export) bl export "points\|non-manifold\|error" ;;
    model) $PY -I tools/make_rvmats.py > /dev/null; $PY -I tools/build_p3d.py | grep -v "bones:"
           "/c/Program Files (x86)/hemtt/hemtt.exe" build 2>&1 | grep -iE "warn|error|Built|missing" || true
           mkdir -p tools/check
           $PY -I tools/pbox.py .hemttout/build/addons/mhfh_heads.pbo 'fh_head_bun.p3d' tools/check > /dev/null
           "$NODE" tools/odump.mjs "$ODOL" tools/check/models_fh_head_bun.p3d tools/check/odol.json > /dev/null
           $PY -I tools/simulate.py tools/check/odol.json tools/ref/anim tools/check/sim.npz ;;
  esac
done
