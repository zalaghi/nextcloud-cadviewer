#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
systemd-run --user --scope --quiet -p MemoryMax=2G -p TasksMax=64 -p CPUQuota=200% \
timeout --foreground 90s bwrap --unshare-all --die-with-parent --new-session --cap-drop ALL --clearenv \
  --ro-bind /usr /usr --symlink usr/lib64 /lib64 --symlink usr/lib /lib --symlink usr/bin /bin \
  --ro-bind "$project/.local/free-render-venv" /venv \
  --ro-bind "$project/worker/render.py" /render.py \
  --ro-bind "$project/.local/external-fixtures/ezdxf-persian_text.dxf" /input.dxf \
  --ro-bind "$project/.local/persian-fonts" /fonts --proc /proc --dev /dev \
  --size 536870912 --tmpfs /scratch --remount-ro / --chdir /scratch \
  --setenv PATH /usr/bin --setenv HOME /scratch --setenv TMPDIR /scratch --setenv OPENBLAS_NUM_THREADS 1 \
  /usr/bin/prlimit --cpu=60 --nproc=64 --fsize=16777216 --nofile=128 -- \
  /venv/bin/python3 /render.py /input.dxf \
  > "$project/.local/open-engine/free-persian.svg" 2> "$project/.local/evidence/free-render.log"
