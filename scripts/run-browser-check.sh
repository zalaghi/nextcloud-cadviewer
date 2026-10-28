#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
lab_pid=$(podman inspect --format '{{.State.Pid}}' cadviewer-browser-lab)
runtime=${CADVIEWER_BROWSER_NODE_RUNTIME:?Set the Node runtime directory containing bin/node and node_modules/playwright}
browser=${CADVIEWER_CHROMIUM_DIR:?Set the directory containing chrome-headless-shell}
# Join ONLY the disconnected lab's network namespace. Host networking is absent.
systemd-run --user --scope --quiet -p MemoryMax=2G -p TasksMax=128 -p CPUQuota=200% \
timeout --foreground 150s podman unshare nsenter --target "$lab_pid" --net \
bwrap --unshare-user --unshare-pid --unshare-ipc --unshare-uts --die-with-parent --new-session --cap-drop ALL --clearenv \
  --ro-bind /usr /usr --symlink usr/lib64 /lib64 --symlink usr/lib /lib --symlink usr/bin /bin \
  --ro-bind /etc/fonts /etc/fonts --ro-bind "$runtime/bin/node" /opt/node \
  --ro-bind "$runtime/node_modules" /packages --ro-bind "$browser" /browser \
  --ro-bind "$project/tests/browser-viewer.cjs" /test.cjs --proc /proc --dev /dev \
  --size 536870912 --tmpfs /scratch --size 33554432 --tmpfs /tmp --remount-ro / --chdir /scratch \
  --setenv PATH /usr/bin --setenv DEBUG pw:browser --setenv NODE_PATH /packages --setenv HOME /scratch/home --setenv TMPDIR /scratch/tmp \
  /usr/bin/prlimit --cpu=120 --nproc=128 --fsize=134217728 --nofile=1024 -- /bin/sh -c \
  'mkdir -p /scratch/home /scratch/tmp; /opt/node /test.cjs; result=$?; if [ -f /scratch/viewer.png ]; then tar -C /scratch -cf - viewer.png --ignore-failed-read plan.png; fi; exit "$result"' \
  > "$project/.local/evidence/browser-images.tar" 2> "$project/.local/evidence/browser-viewer.log"

python3 - "$project" <<'PYIMAGE'
import sys, tarfile
from pathlib import Path
root=Path(sys.argv[1])/'.local/evidence'
with tarfile.open(root/'browser-images.tar') as t:
    for member in t.getmembers():
        if member.name not in ('viewer.png','plan.png') or not member.isfile() or member.size>8*1024*1024:
            raise ValueError('Unexpected browser image')
        (root/member.name).write_bytes(t.extractfile(member).read())
PYIMAGE
