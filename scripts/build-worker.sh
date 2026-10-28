#!/usr/bin/env bash
# Linux x86_64 / Python 3.14. Fetch inputs first, then build and install offline.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project"
engine="$project/.local/open-engine"
mkdir -p "$engine/source" "$engine/runtime" "$engine/wheels" "$engine/image/fonts" "$engine/image/licenses" "$project/.local/evidence"
gcc_image=docker.io/library/gcc@sha256:dc99c5016a0fb74d4e9a392e7892966ec7f358af744799bd3479239598f79d45
python_image=docker.io/library/python@sha256:cd89c30eda26ee911a4611b18680086e0ea42e6f5f8cbe653d07fa7958c9cec8
podman pull "$gcc_image"
podman pull "$python_image"
if [ ! -f "$engine/libredwg-0.14.tar.xz" ]; then
  curl --fail --location --proto '=https' --tlsv1.2 --max-time 120 \
    https://github.com/LibreDWG/libredwg/releases/download/0.14/libredwg-0.14.tar.xz \
    -o "$engine/libredwg-0.14.tar.xz"
fi
python3 - "$engine" <<'PY'
import sys, hashlib, tarfile
from pathlib import Path
root=Path(sys.argv[1]);source=root/'libredwg-0.14.tar.xz'
if hashlib.sha256(source.read_bytes()).hexdigest()!='62ebb73b984f865960f20ed26619ea5f8789d5e3fd088fa40a2598384da81275':
    raise ValueError('LibreDWG source checksum mismatch')
if not (root/'source/libredwg-0.14').exists():
    with tarfile.open(source) as t: t.extractall(root/'source',filter='data')
PY
# Wheel download performs no source build or package import.
python3.14 -m venv .local/free-render-venv
.local/free-render-venv/bin/python3 -m pip download --require-hashes --only-binary=:all: \
  -r worker/requirements.lock --dest "$engine/wheels"
bash scripts/build-libredwg.sh
python3 - "$engine" <<'PY'
import sys,tarfile
from pathlib import Path
root=Path(sys.argv[1])
with tarfile.open(root/'build.tar') as t:
    for name,dest in [('programs/dwg2dxf','dwg2dxf'),('COPYING','LibreDWG-COPYING')]:
        member=t.getmember(name)
        if not member.isfile() or member.size>32*1024*1024: raise ValueError('Invalid build output')
        (root/'runtime'/dest).write_bytes(t.extractfile(member).read())
(root/'runtime/dwg2dxf').chmod(0o755)
PY
# Installing verified wheels is also offline, unprivileged, and disk bounded.
timeout 150 podman run --rm --pull=never --network=none --read-only --read-only-tmpfs=false \
  --image-volume=ignore --user=65534:65534 --cap-drop=ALL --security-opt=no-new-privileges \
  --memory=2g --cpus=2 --pids-limit=64 --ulimit cpu=120:120 \
  --ulimit fsize=536870912:536870912 --ulimit nofile=128:128 \
  --tmpfs /scratch:rw,size=1g,mode=1777 -v "$engine/wheels:/wheels:ro,z" \
  -v "$project/worker/requirements.lock:/requirements.lock:ro,z" \
  --entrypoint=/usr/bin/env "$python_image" -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/scratch TMPDIR=/scratch \
  /bin/sh -c 'set -eu; python3 -m pip install --no-index --no-compile --no-cache-dir --only-binary=:all: --require-hashes --find-links=/wheels --target=/scratch/site -r /requirements.lock >&2; tar -C /scratch -cf - site' \
  > "$engine/site.tar"
python3 - "$engine" <<'PY'
import sys,tarfile
from pathlib import Path
root=Path(sys.argv[1])
with tarfile.open(root/'site.tar') as t:
    members=t.getmembers()
    if len(members)>15000 or sum(m.size for m in members)>300*1024*1024: raise ValueError('Oversized dependency artifact')
    for m in members:
        p=Path(m.name)
        if p.is_absolute() or '..' in p.parts or p.parts[0]!='site' or not(m.isdir() or m.isfile()): raise ValueError('Invalid dependency artifact')
    t.extractall(root/'image',filter='data')
PY
# Only checksum-verified public fonts enter the distributable image.
font_stage=$(mktemp -d "$engine/bundled-fonts.XXXXXX")
trap 'rm -rf -- "$font_stage"' EXIT
python3 scripts/prepare-bundled-fonts.py --stage "$font_stage"
# Clear previous font layers so a reused local build cannot publish private fonts.
rm -rf -- "$engine/image/fonts" "$engine/image/licenses"
cp -R "$font_stage/fonts" "$engine/image/fonts"
cp -R "$font_stage/licenses" "$engine/image/licenses"
cp "$engine/runtime/dwg2dxf" "$engine/image/"
cp "$engine/runtime/LibreDWG-COPYING" "$engine/image/licenses/"
cp "$engine/libredwg-0.14.tar.xz" worker/render.py worker/blocks.py "$engine/image/"
cp COPYING "$engine/image/licenses/CADViewer-COPYING"
systemd-run --user --scope --quiet -p MemoryMax=2G -p TasksMax=64 -p CPUQuota=200% \
timeout 180 podman build --network=none --pull=never --layers=false --memory=2g \
  --cpu-quota=200000 --ulimit cpu=120:120 --ulimit fsize=536870912:536870912 \
  -f worker/Containerfile -t localhost/cadviewer-worker:0.1 "$engine/image"
podman image inspect localhost/cadviewer-worker:0.1 --format '{{.Id}}'
