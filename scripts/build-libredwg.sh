#!/usr/bin/env bash
# Trusted release sources are downloaded and verified separately; this build is offline.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
timeout --foreground 900s podman run --rm --pull=never --name cadviewer-free-engine-build \
  --network=none --read-only --read-only-tmpfs=false --image-volume=ignore \
  --user=65534:65534 --cap-drop=ALL --security-opt=no-new-privileges \
  --memory=4g --cpus=2 --pids-limit=128 --ulimit cpu=700:700 \
  --ulimit fsize=536870912:536870912 --ulimit nofile=1024:1024 \
  --tmpfs /scratch:rw,size=4g,mode=1777 \
  -v "$project/.local/open-engine/source:/source:ro,z" --workdir=/scratch \
  --entrypoint=/usr/bin/env 43f51138b1cd8113a36a0a38d89243debb9da1dc64dff2d3f10e945f15eab0bd -i \
  PATH=/usr/local/bin:/usr/bin:/bin HOME=/scratch/home TMPDIR=/scratch/tmp LANG=C.UTF-8 \
  /bin/sh -c 'set -eu
mkdir -p /scratch/home /scratch/tmp
cp -R --preserve=timestamps /source/libredwg-0.14 /scratch/build
cd /scratch/build
./configure --disable-bindings --disable-shared --enable-static --disable-werror CFLAGS="-O2 -g0" >/scratch/build.log 2>&1
make -j2 -C src libredwg.la >>/scratch/build.log 2>&1 || { tail -60 /scratch/build.log >&2; exit 1; }
make -j2 -C programs dwg2dxf >>/scratch/build.log 2>&1 || { tail -60 /scratch/build.log >&2; exit 1; }
tar cf - programs/dwg2dxf COPYING' \
  > "$project/.local/open-engine/build.tar" 2> "$project/.local/evidence/free-engine-build.log"
