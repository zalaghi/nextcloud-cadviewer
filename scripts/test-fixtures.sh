#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
image_id=$(podman image inspect localhost/cadviewer-worker:0.1 --format '{{.Id}}')
job_name="cadviewer-fixture-$$"
trap 'podman rm -f -v "$job_name" >/dev/null 2>&1 || true' EXIT
for extension in dxf dwg; do
  if [ "$extension" = dxf ]; then fixture=ezdxf-persian_text.dxf; else fixture='maskoni85m(difal.ir).dwg'; fi
  timeout --foreground 80s podman run --rm --pull=never --name "$job_name" \
    --network=none --read-only --read-only-tmpfs=false --image-volume=ignore \
    --user=65534:65534 --cap-drop=ALL --security-opt=no-new-privileges \
    --memory=2g --cpus=2 --pids-limit=64 --ulimit cpu=60:60 \
    --ulimit fsize=134217728:134217728 --ulimit nofile=128:128 \
    --tmpfs /scratch:rw,size=768m,mode=1777 \
    -v "$project/.local/persian-fonts:/fonts:ro,z" \
    -v "$project/.local/external-fixtures/$fixture:/input.$extension:ro,z" \
    --workdir=/scratch --entrypoint=/usr/bin/env "$image_id" -i \
    PATH=/usr/local/bin:/usr/bin:/bin HOME=/scratch TMPDIR=/scratch \
    PYTHONPATH=/opt/python PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 LANG=C.UTF-8 \
    /usr/local/bin/python3 /opt/cadviewer/render.py "/input.$extension" \
    > "$project/.local/open-engine/free-$extension.svg"
  echo "PASS offline $extension fixture conversion"
done
