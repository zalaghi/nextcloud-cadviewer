# Deployment boundary and procedure

For concrete first-install commands, follow [INSTALL.md](INSTALL.md): source packaging, worker account/service, AIO, regular Nextcloud, settings and acceptance. This document explains the deployment boundary and host-specific requirements.

This alpha has been built and tested locally and installed on a Nextcloud AIO test deployment. See VALIDATION.md for the precise acceptance scope. Its intended installation scope is only the app's own persistent `custom_apps/cadviewer_nextcloud` directory and a separate conversion service. Do not modify Nextcloud core, global configuration, global MIME mappings, `.htaccess`, AIO containers or AIO images.

## Build inputs

Use Linux x86_64 with rootless Podman, bubblewrap, a systemd user session, Python 3.14, Node 24 and npm. `scripts/build-isolated.sh` accepts `CADVIEWER_NODE` for the Node executable. `scripts/build-worker.sh` fetches pinned official GCC/Python images, LibreDWG 0.14 with a verified SHA-256, and hash-locked binary Python wheels. Compilation and installation then run offline in bounded containers. It does not read user credentials or a live Nextcloud installation.

The build verifies and includes the repository's Vazirmatn 33.003 and Liberation Sans 2.1.5 fonts, their original OFL notices and the font manifest. It no longer needs a font installed on the build host. Supplied Persian SHX fonts are never built into the image. The image contains the exact LibreDWG source archive, its GPL notice, the app notice and Python package notices.

## Worker

Use a dedicated unprivileged operating-system account with rootless Podman. Install the built immutable image into that account's image store; do not expose a Docker/Podman API socket to a drawing parser. Copy `worker/service.py`, a private configuration file based on `worker/config.example.json`, a private random authentication-token file and the required drawing fonts. Paths in the config must be absolute. `image` is the full immutable image ID, not a mutable tag. Make the job directory writable only by the service account; the fonts are mounted read-only into parser jobs.

Run the gateway as that account:

```sh
python3 /srv/cadviewer/service.py \
  --config /srv/cadviewer/config.json \
  --token-file /srv/cadviewer/worker-token \
  --bind PRIVATE_SERVICE_ADDRESS --port 8090
```

Create the token as at least 32 random bytes encoded with URL-safe Base64 (43+ characters). The token is not an activation/license system. Bind to an isolated private address reachable only from Nextcloud, with a private firewall rule; use HTTPS if crossing an untrusted network. The HTTP gateway deliberately has no file-browser, upload-store, URL-fetch or administrative endpoint. One job is processed at a time. Each job accepts at most 32 MiB, returns at most 32 MiB, and has an 80-second deadline. The parser has no network, capabilities or persistent writable filesystem, and has 2 GiB memory, 2 CPUs, 64 processes and 768 MiB scratch limits.

Place matching fonts in the private font directory. `scripts/prepare-persian-fonts.py` can inspect and stage the user's SHX files into a new directory without altering originals. Never run supplied AutoLISP. Font redistribution rights are separate from the free app's license.

## Alpine / OpenRC hosts

AIO's host operating system may use OpenRC instead of systemd. Install the worker runtime on the host or a separate worker machine, never inside the Nextcloud AIO container. Rootless Podman requires subordinate UID/GID ranges and cgroup v2. Use a dedicated service account, a delegated cgroup with an outer administrator-owned resource ceiling, and a private bind address. Configure an OpenRC service to prepare the delegated cgroup before dropping to the worker account. Fail startup if resource preparation or a required firewall rule fails. Validate resource limits before enabling conversion. Do not use privileged parser containers or remove cgroup limits as a workaround.

## Nextcloud app

Keep a backup of an existing app directory before installing a custom build. Install only the app bundle in Nextcloud's persistent custom-apps volume. Enable it normally; do not use `--force`, MIME repair commands or rewrite changes. In Administration → CADViewer, save the private `/convert` endpoint and authentication token. These are stored in app configuration only.

This project uses its own app ID `cadviewer_nextcloud`, separate from the upstream commercial integration. AIO image updates and application updates are different operations; the app is stored in the persistent custom-apps volume.

Before production acceptance, open the actual user's DWG from Files, test a read-only share and denied access, confirm fonts against an AutoCAD reference, verify worker isolation on the chosen host and check the AIO runtime's security status separately. App code cannot patch PHP or OS libraries.

## Rollback

Disable the app and restore its previous directory if one existed. Stop the separate worker service. This code has no installation/uninstallation repair steps and requires no reverse changes to core files or global MIME mappings. Preserve any custom app settings/worker configuration securely if a later reinstall is planned.

When operating a modified AGPL application for network users, make its corresponding source available to those users; include this fork, frontend sources, dependency notices and build instructions. The deployment bundle includes the app sources, and the worker image includes the exact LibreDWG source archive.
