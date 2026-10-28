#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
systemd-run --user --scope --quiet -p MemoryMax=2G -p TasksMax=64 -p CPUQuota=200% \
timeout --foreground 90s bwrap --unshare-all --die-with-parent --new-session --cap-drop ALL --clearenv \
  --ro-bind /usr /usr --symlink usr/lib64 /lib64 --symlink usr/lib /lib --symlink usr/bin /bin \
  --ro-bind "$project/.local/free-render-venv" /venv \
  --ro-bind "$project/scripts/prepare-persian-fonts.py" /source/scripts/prepare-persian-fonts.py \
  --ro-bind "$project/tests/test_fonts.py" /source/tests/test_fonts.py \
  --ro-bind "$project/worker" /source/worker --ro-bind "$project/tests/test_worker.py" /test.py \
  --ro-bind "$project/.local/persian-fonts" /fonts --proc /proc --dev /dev \
  --size 536870912 --tmpfs /scratch --remount-ro / --chdir /scratch \
  --setenv PATH /usr/bin --setenv HOME /scratch --setenv TMPDIR /scratch --setenv OPENBLAS_NUM_THREADS 1 \
  --setenv PYTHONDONTWRITEBYTECODE 1 \
  /usr/bin/prlimit --cpu=60 --nproc=64 --fsize=16777216 --nofile=128 -- /bin/sh -c '/venv/bin/python3 /source/tests/test_fonts.py && /venv/bin/python3 /test.py'
