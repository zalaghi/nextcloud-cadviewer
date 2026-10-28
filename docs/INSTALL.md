# Installing CADViewer on Nextcloud AIO or a regular Nextcloud server

An administrator installs two components once. Users then open `.dwg` or `.dxf` files in Nextcloud Files; they do not install software or fonts on their computers. The interface remains English. Drawings are converted on your own worker, without a paid SDK or cloud conversion service.

This is currently a **manual alpha installation**, not an App Store listing or an official AIO community container. Supported app target: **Nextcloud 35**, PHP 8.3–8.5 with current security updates. Do not use `--force` on other versions. The worker requires **Linux x86_64, rootless Podman and cgroup v2**. Shared hosting without a way to run a private worker needs the hosting administrator's assistance.

| Deployment | App location | Worker location |
| --- | --- | --- |
| Nextcloud AIO | Existing persistent `/var/www/html/custom_apps/cadviewer_nextcloud` in `nextcloud-aio-nextcloud` | Separate unprivileged service on the host or another private Linux machine |
| Regular Nextcloud | An existing writable directory in Nextcloud's configured `apps_paths`, under `cadviewer_nextcloud` | Separate unprivileged service, possibly on the same host |

Do not install the worker inside the AIO Nextcloud container, expose a container socket to it, or edit Nextcloud core/global MIME/configuration files. An AIO image update preserves the custom-app volume, but app compatibility and worker updates still need their own testing.

## 1. Get and package the public source

On a build workstation, clone the repository and record the exact revision used. The checked-in JavaScript is already built; Node/npm are only needed when changing the frontend.

```sh
git clone https://github.com/zalaghi/nextcloud-cadviewer.git
cd nextcloud-cadviewer
git rev-parse HEAD
python3 scripts/prepare-bundled-fonts.py
python3 scripts/package-app.py
```

The app archive and its SHA-256 file appear in `.local/releases/`. It contains the app, its corresponding frontend source and notices. It excludes private drawings, private fonts, credentials, `.git`, `node_modules` and the conversion runtime. Repeating packaging into a different empty output directory produces the same bytes for the same source.

Build the worker on a Linux x86_64 machine with rootless Podman, a working systemd user session, Python **3.14** with venv/pip, curl and Bash. This build environment can be separate from the Nextcloud host; the gateway itself uses standard-library Python 3.10+.

```sh
bash scripts/build-worker.sh
podman image inspect localhost/cadviewer-worker:0.1 --format '{{.Id}}'
podman save --format oci-archive \
  -o .local/releases/cadviewer-worker.oci localhost/cadviewer-worker:0.1
cd .local/releases
sha256sum cadviewer-worker.oci > cadviewer-worker.oci.sha256
```

The build downloads pinned official inputs, verifies LibreDWG and Python wheel hashes, then compiles/installs offline under resource limits. It includes all nine Vazirmatn weights and Liberation Sans, with their licenses. Allow several GiB of build disk/RAM; runtime jobs are limited to 2 GiB each. Transfer the OCI archive, checksums and this source checkout to the worker host over a trusted channel. Verify checksums after transfer. A checksum detects transfer corruption, not an untrusted publisher.

## 2. Prepare the worker account

The worker host needs Podman, a container runtime such as crun, Python 3.10+, subordinate UID/GID mappings and working cgroup v2 delegation. On a systemd distribution, have the administrator create a dedicated account and enable its user manager, for example:

```sh
sudo useradd --create-home --shell /bin/bash cadviewer
sudo loginctl enable-linger cadviewer
```

If the account already exists, reuse it. Check that `/etc/subuid` and `/etc/subgid` contain non-overlapping ranges for that account; use your distribution's rootless Podman setup instructions rather than copying someone else's range. Install Podman prerequisites using your distribution's supported packages. Leave the dedicated account unprivileged; it does not need the Docker group or passwordless sudo.

Run the following as **that account**, with its own home, Podman store and systemd user session (for example, log in as the account or use `sudo -iu cadviewer`). If the user bus is not in the login environment, set:

```sh
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
podman info
```

Confirm `rootless: true` and `cgroupVersion: v2`. Import the image under this account, not root:

```sh
podman load -i /PATH/TO/cadviewer-worker.oci
podman image inspect localhost/cadviewer-worker:0.1 --format '{{.Id}}'
```

From the transferred source checkout, initialize a **new** worker directory. Replace `IMAGE_ID` with the full 64-character image ID above and `PRIVATE_IP` with an actual address owned by the worker host and reachable from Nextcloud:

```sh
python3 scripts/init-worker.py --image IMAGE_ID --bind PRIVATE_IP --port 8090
```

This creates `~/cadviewer/` containing the gateway, a private configuration, empty private `fonts/` and `jobs/` directories, a random mode-0600 token file and a user-service template. It never overwrites an existing deployment or prints the token. Bundled fonts are already inside the image, so the private fonts directory may stay empty.

## 3. Restrict the private endpoint and start the service

For regular Nextcloud on the same host, `127.0.0.1:8090` can be used. For AIO, **127.0.0.1 inside the Nextcloud container is not the host**. Use the host's reachable private interface or the gateway of Nextcloud's Docker network. Discover the actual values instead of assuming a fixed subnet:

```sh
docker inspect nextcloud-aio-nextcloud --format '{{json .NetworkSettings.Networks}}'
```

The host administrator must allow the chosen port only from the Nextcloud server/container network and block other sources with the host's existing firewall. Do not publish/forward this port to the Internet or add a public tunnel. Use HTTPS through a private reverse proxy if traffic crosses an untrusted network. The gateway has its own bearer-token authentication in addition to the network boundary.

On **systemd**, after the network restriction is in place, run as the worker account:

```sh
mkdir -p ~/.config/systemd/user
install -m 600 ~/cadviewer/cadviewer.service ~/.config/systemd/user/cadviewer.service
systemctl --user daemon-reload
systemctl --user enable --now cadviewer.service
systemctl --user status cadviewer.service
```

The default unit expects `~/cadviewer/`; adapt its paths if initialization used `--directory`. The user manager must delegate cgroups to rootless Podman. The gateway unit has a 3 GiB/2 CPU/128-task outer ceiling; individual parser jobs have stricter limits and no network. If the host cannot enforce those limits, correct delegation before using the service. Do not remove limits to make an incompatible host start.

On **Alpine/OpenRC**, the app installation is identical, but the systemd unit above does not apply. Use the [OpenRC requirements](DEPLOYMENT.md#alpine--openrc-hosts) and the distribution's service supervision/cgroup setup, or run the worker on a separate supported systemd machine. The previously tested Alpine AIO installation used host-specific OpenRC delegation; this repository does not claim a universal OpenRC installer.

## 4A. Install the app on Nextcloud AIO

Use the app archive created in step 1. These commands are for a **first installation**; an existing app directory intentionally stops the copy. Run from `.local/releases` on the AIO host after transferring the archive and checksum:

```sh
sha256sum -c cadviewer_nextcloud-0.1.0-alpha.4.tar.gz.sha256
docker exec nextcloud-aio-nextcloud test -d /var/www/html/custom_apps
docker exec nextcloud-aio-nextcloud test ! -e /var/www/html/custom_apps/cadviewer_nextcloud
```

Proceed only if both directory checks succeed. Copy the archive contents into the already persistent custom-app directory:

```sh
docker exec -i --user www-data nextcloud-aio-nextcloud \
  tar -xzf - -C /var/www/html/custom_apps < cadviewer_nextcloud-0.1.0-alpha.4.tar.gz
docker exec --user www-data nextcloud-aio-nextcloud \
  php occ app:enable cadviewer_nextcloud
```

No AIO image rebuild/restart, global MIME repair, `config.php` change or Nextcloud database edit is needed. See [Nextcloud's app commands](https://docs.nextcloud.com/server/stable/admin_manual/occ_apps.html) and [AIO documentation](https://github.com/nextcloud/all-in-one) for the host's normal administration.

## 4B. Install the app on regular Nextcloud

Find the existing writable app directory, using the PHP version and web-server account for that installation:

```sh
sudo -u www-data php /var/www/nextcloud/occ config:system:get apps_paths
```

Use the existing configured writable directory; do not blindly create a directory Nextcloud does not scan. The example below assumes it is `/var/www/nextcloud/custom_apps`. Replace the path and account if your installation differs. If no such writable directory is available, ask the host administrator to provide the deployment path before proceeding.

```sh
sha256sum -c cadviewer_nextcloud-0.1.0-alpha.4.tar.gz.sha256
test ! -e /var/www/nextcloud/custom_apps/cadviewer_nextcloud
```

After both checks succeed:

```sh
sudo -u www-data tar -xzf cadviewer_nextcloud-0.1.0-alpha.4.tar.gz \
  -C /var/www/nextcloud/custom_apps
sudo -u www-data php /var/www/nextcloud/occ app:enable cadviewer_nextcloud
```

If the deployment account owns that directory instead, have it extract the archive and grant the web-server account the installation's normal read permissions. Do not recursively change ownership of the whole Nextcloud tree. For Docker installations other than AIO, use the equivalent commands inside the Nextcloud container with a persistent custom-app mount.

## 5. Connect the app and open a drawing

As a Nextcloud administrator, open **Administration settings → CADViewer**. Set **Conversion service URL** to the private URL, such as `http://PRIVATE_IP:8090/convert`. Securely copy the contents of the worker's `worker-token` file into **Conversion service token** and save. Do not place the token in a URL, Git repository, shell arguments, public log or support screenshot. The app encrypts it in app-specific configuration; do not use `occ config:app:set` to bypass that encryption.

Upload a known DWG or DXF to Files and click it. Test a normal account and a read-only share between logged-in users; a denied file must remain inaccessible. Public-link previews are not implemented. Each conversion can take up to 80 seconds. If a reverse proxy has a shorter timeout, the administrator must account for that in the normal hosting configuration.

Check representative labels and dimensions against the source CAD application. Check gateway logs with `journalctl --user -u cadviewer.service` on systemd. A running gateway alone does not prove successful conversion or faithful font rendering. Missing-font warnings identify substitutions; import the exact fonts when required.

## 6. Add private drawing fonts, update and roll back

For additional SHX/KATEB/TrueType fonts, follow [FONTS.md](FONTS.md). Stage a new private directory, preserve the original collection, then point only the worker's `fonts` configuration at the staged directory and restart the gateway. The bundled Vazirmatn fonts use their original names, for example `Vazirmatn-Regular.ttf`; do not rename them to masquerade as Tahoma or a legacy SHX font. Close and reopen affected drawings after a font change; an already open viewer still contains its earlier preview.

Before an update, back up the app directory, encrypted app settings through the normal Nextcloud backup, worker configuration/token, private fonts and old immutable image ID. Disable **only** `cadviewer_nextcloud`, replace its own directory with the new verified package, import the new worker image as its service account and change the image ID in its config. Run Nextcloud's native app update/upgrade mechanism, enable the app normally, restart the gateway and recheck an actual drawing. Do not hand-edit `installed_version` or database records. Follow the host's usual change window if Nextcloud reports that a native upgrade is pending.

To roll back, disable the app, restore its previous app directory and restore the previous worker config/image. Preserve the secret and fonts securely. No reverse change to Nextcloud core or an AIO image is needed. Future App Store publishing/signing and prebuilt image releases are separate distribution work; this guide describes the reproducible source installation available today.
