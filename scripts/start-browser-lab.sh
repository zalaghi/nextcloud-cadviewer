#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source_dir=$(mktemp -d "$project/.local/test-scratch/browser-source.XXXXXXXX")
fixture_dir=$(mktemp -d "$project/.local/test-scratch/browser-fixtures.XXXXXXXX")
chmod 755 "$source_dir" "$fixture_dir"
tar -C "$project" -cf - appinfo css lib js assets templates tests img | tar xf - -C "$source_dir"
cp "$project/.local/external-fixtures/ezdxf-persian_text.dxf" "$fixture_dir/public.dxf"
cp "$project/.local/open-engine/free-persian.svg" "$fixture_dir/public.svg"
cp "$project/.local/external-fixtures/maskoni85m(difal.ir).dwg" "$fixture_dir/public.dwg"
cp "$project/.local/open-engine/free-dwg.svg" "$fixture_dir/dwg.svg"
podman run --rm --pull=never --name cadviewer-browser-lab \
  --label cadviewer.disposable-lab=true --network=none --read-only --read-only-tmpfs=false \
  --image-volume=ignore --user=33:33 --cap-drop=ALL --security-opt=no-new-privileges \
  --memory=3g --cpus=2 --pids-limit=128 --ulimit cpu=240:240 \
  --ulimit fsize=268435456:268435456 --ulimit nofile=1024:1024 \
  --tmpfs /scratch:rw,size=2g,mode=1777 -v "$source_dir:/source:ro,z" \
  -v "$fixture_dir:/fixtures:ro,z" --workdir=/scratch --entrypoint=/usr/bin/env \
  docker.io/library/nextcloud:35.0.2-apache -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/scratch/home TMPDIR=/scratch/tmp LANG=C.UTF-8 PHP_MEMORY_LIMIT=512M PHP_UPLOAD_LIMIT=16M \
  timeout 1200 /bin/sh /source/tests/start-browser-lab.sh
