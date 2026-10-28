#!/usr/bin/env python3
"""Create a NEW private worker directory as its dedicated service account.

Does not install packages, start services, change firewalls or touch Nextcloud.
The secret is written to a mode-0600 file and is never printed.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import subprocess


def initialize(directory, image, bind, port, source):
    directory = Path(directory).absolute()
    if not re.fullmatch(r'(?:sha256:)?[0-9a-f]{64}', image):
        raise ValueError('Use the full immutable worker image ID')
    address = ipaddress.IPv4Address(bind)
    if not (address.is_private or address.is_loopback) or address.is_unspecified or address.is_multicast:
        raise ValueError('Use a specific private IPv4 address reachable from Nextcloud')
    if not 1024 <= port <= 65535:
        raise ValueError('Choose an unprivileged TCP port (1024-65535)')
    if any(c in str(directory) for c in ':,\n\r') or any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError('Unsafe worker directory')
    if directory.exists():
        raise ValueError('Worker directory already exists; initialization never overwrites a deployment')
    if not directory.parent.is_dir():
        raise ValueError('Create the parent directory first')
    service = (source / 'worker/service.py').read_bytes()
    unit = (source / 'worker/cadviewer.service').read_bytes()
    directory.mkdir(mode=0o700)
    # Host parent is private (0700); the read-only bind itself must be readable
    # by the parser's mapped UID 65534, not just the service account.
    (directory / 'fonts').mkdir(mode=0o755)
    (directory / 'fonts').chmod(0o755)
    (directory / 'jobs').mkdir(mode=0o700)
    config = {'image': image, 'fonts': str(directory / 'fonts'), 'scratch': str(directory / 'jobs')}
    for name, data in {
        'config.json': (json.dumps(config, indent=2) + '\n').encode(),
        'worker-token': (secrets.token_urlsafe(48) + '\n').encode(),
        'runtime.env': f'CADVIEWER_BIND={address}\nCADVIEWER_PORT={port}\n'.encode(),
        'service.py': service, 'cadviewer.service': unit,
    }.items():
        descriptor = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, help='Full immutable image ID in this account\'s Podman store')
    parser.add_argument('--bind', required=True, help='Private address reachable from Nextcloud')
    parser.add_argument('--port', type=int, default=8090)
    parser.add_argument('--directory', type=Path, default=Path.home() / 'cadviewer')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as the dedicated unprivileged worker account')
    try:
        if not re.fullmatch(r'(?:sha256:)?[0-9a-f]{64}', args.image):
            raise ValueError('Use the full immutable worker image ID')
        info = json.loads(subprocess.check_output(['podman', 'info', '--format=json']))
        if not info['host']['security']['rootless'] or info['host']['cgroupVersion'] != 'v2':
            raise ValueError('Rootless Podman with cgroup v2 is required')
        subprocess.run(['podman', 'image', 'exists', args.image], check=True)
        directory = initialize(args.directory, args.image, args.bind, args.port, Path(__file__).resolve().parents[1])
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(1, f'{error}\n')
    print(f'Created private worker files in {directory}. Secret saved in worker-token (not printed).')
    print('Apply private network access rules, then follow docs/INSTALL.md to start and test the service.')
    if directory != Path.home() / 'cadviewer':
        print('Custom directory: adapt the systemd unit paths before installing that unit.')


if __name__ == '__main__':
    main()
