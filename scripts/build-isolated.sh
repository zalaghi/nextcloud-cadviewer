#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
node_binary=${CADVIEWER_NODE:-$(command -v node)}
mkdir -p "$project/.local/test-scratch"
build_input=$(mktemp -d "$project/.local/test-scratch/build-input.XXXXXXXX")
build_output=$(mktemp "$project/.local/test-scratch/build-output.XXXXXXXX.tar")
trap 'rm -rf -- "$build_input"; rm -f -- "$build_output"' EXIT
tar -C "$project" -cf - src scripts/build.mjs package.json package-lock.json assets js | tar xf - -C "$build_input"
systemd-run --user --scope --quiet -p MemoryMax=2G -p TasksMax=128 -p CPUQuota=200% \
timeout --foreground 150s bwrap --unshare-all --die-with-parent --new-session --cap-drop ALL --clearenv \
  --ro-bind /usr /usr --symlink usr/lib64 /lib64 --symlink usr/lib /lib --symlink usr/bin /bin \
  --ro-bind "$node_binary" /opt/node --ro-bind "$build_input" /source \
  --ro-bind "$project/node_modules" /node_modules --proc /proc --dev /dev \
  --size 536870912 --tmpfs /scratch --remount-ro / --chdir /scratch \
  --setenv PATH /usr/bin --setenv HOME /scratch/home --setenv TMPDIR /scratch/tmp \
  /usr/bin/prlimit --cpu=120 --nproc=128 --fsize=67108864 --nofile=1024 -- \
  /bin/sh -c 'set -eu; mkdir -p /scratch/home /scratch/tmp /scratch/work; cp -R /source/. /scratch/work/; ln -s /node_modules /scratch/work/node_modules; /opt/node /scratch/work/scripts/build.mjs >/scratch/build.log 2>&1 || { cat /scratch/build.log >&2; exit 1; }; cat /scratch/build.log >&2; tar -C /scratch/work -cf - js/cadviewer-files.js js/cadviewer-files.js.LICENSE.txt assets' > "$build_output"
# Promote only bounded regular build products; never archive paths or links.
python3 - "$project" "$build_output" <<'PY'
import sys, tarfile
from pathlib import Path, PurePosixPath
root, archive = Path(sys.argv[1]), sys.argv[2]
with tarfile.open(archive, 'r:') as bundle:
    total = 0
    members = bundle.getmembers()
    for member in members:
        p = PurePosixPath(member.name)
        if p.is_absolute() or '..' in p.parts or p.parts[0] not in ('js', 'assets'):
            raise ValueError('Unexpected build path')
        if not member.isdir() and not member.isfile():
            raise ValueError('Unexpected build entry')
        if member.size > 16 * 1024 * 1024:
            raise ValueError('Oversized build file')
        total += member.size
    if total > 128 * 1024 * 1024 or len(members) > 4000:
        raise ValueError('Oversized build output')
    for member in members:
        target = root / member.name
        if target.is_symlink():
            raise ValueError('Symlink in build destination')
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.extractfile(member).read())
PY
