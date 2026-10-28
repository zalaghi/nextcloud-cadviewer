# Security

This is alpha software. Passing regression tests and dependency advisory checks is not a complete security audit or a guarantee of safety.

Use a private authenticated gateway and a dedicated unprivileged worker account. Enforce cgroup and storage/time limits; keep the parser offline and read-only. Never give the parser access to the Nextcloud data directory, gateway token, host home, or Docker/Podman socket. Treat CAD files, fonts and conversion output as untrusted input. Keep PHP, Nextcloud, the worker runtime and underlying OS patched independently.

The app uses native Nextcloud permissions and CSRF/admin middleware. No public-link rendering is implemented. The renderer is restricted to DWG/DXF and bounded inputs/outputs; SVG is sanitized and displayed in an opaque-origin frame. See docs/ARCHITECTURE.md for exact boundaries and docs/VALIDATION.md for what has and has not been tested.

For a suspected vulnerability, use GitHub's private vulnerability reporting feature when available, or contact the maintainer privately through the profile linked in README before disclosing details. Do not upload credentials, session cookies, private/customer drawings, exploit payloads or live server logs into public issues. For ordinary bugs, a minimal non-sensitive synthetic drawing and version information are preferable.

Security reports should identify the affected version, expected versus observed behavior, relevant trust boundary and a minimal safe reproduction in a disposable environment. Do not test availability or unauthorized access against shared/production instances.
