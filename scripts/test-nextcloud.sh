#!/usr/bin/env bash
# Disposable offline test installation. No existing Nextcloud or host services.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
lab_image=${CADVIEWER_TEST_IMAGE:-docker.io/library/nextcloud:35.0.2-apache}
lab_container="cadviewer-smoke-$$"
mkdir -p "$project_dir/.local/test-scratch"
lab_source=$(mktemp -d "$project_dir/.local/test-scratch/source.XXXXXXXX")
cleanup() {
  podman rm -f -v "$lab_container" >/dev/null 2>&1 || true
  rm -rf -- "$lab_source"
}
trap cleanup EXIT
# Only a disposable copy is exposed, never private samples, .git or evidence.
tar -C "$project_dir" --exclude=.git --exclude=node_modules --exclude=.local \
  --exclude=__pycache__ -cf - . | tar xf - -C "$lab_source"
timeout --foreground 240s podman run --rm --pull=never --name "$lab_container" \
  --network=none --read-only --read-only-tmpfs=false --image-volume=ignore \
  --user=33:33 --cap-drop=ALL --security-opt=no-new-privileges \
  --memory=3g --cpus=2 --pids-limit=128 \
  --ulimit cpu=120:120 --ulimit fsize=268435456:268435456 \
  --ulimit nofile=1024:1024 --tmpfs /scratch:rw,size=2g,mode=1777 \
  -v "$lab_source:/source:ro,z" --workdir=/scratch \
  --entrypoint=/usr/bin/env "$lab_image" -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/scratch/home TMPDIR=/scratch/tmp LANG=C.UTF-8 \
  PHP_MEMORY_LIMIT=512M PHP_UPLOAD_LIMIT=16M \
  /bin/sh /source/tests/run-nextcloud-lab.sh
