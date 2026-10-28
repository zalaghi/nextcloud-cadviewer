# Architecture

## Nextcloud boundary

The app ID is `cadviewer_nextcloud`; PHP namespace is `OCA\CadviewerNextcloud`. Registration uses Nextcloud's public bootstrap/events API and the Files action API. Only DWG/DXF files with read permission receive the action. No installation repair steps, global MIME modifications, core patches, direct database queries, global CSP weakening or AIO image edits are used.

`POST /apps/cadviewer_nextcloud/api/preview` accepts a numeric file ID and layout index (0–31). Native Nextcloud authentication and CSRF middleware apply. `DrawingAccess` resolves the ID in the current user's mounted tree, including shares, and reads at most 32 MiB. It never accepts an arbitrary URL or host filesystem path. After conversion, permission, etag and content hash are checked again; revoked access or changed content prevents delivery. Responses are private/no-store. Large successful previews negotiate gzip in this app alone; vector data is unchanged and no global web-server setting is edited.

Administrative connection settings require native administrator and CSRF checks. The endpoint is fixed by the administrator; the client cannot choose an arbitrary conversion destination. Only HTTP(S) endpoints ending exactly in `/convert` are allowed. Plain HTTP is restricted to private IPv4 addresses or internal single-label DNS names. Credentials/query strings/fragments in URLs and redirects are rejected. The token is encrypted through Nextcloud's crypto service.

## Worker boundary

`worker/service.py` is a small private HTTP gateway, run as a dedicated unprivileged OS user. It uses a constant-time bearer-token comparison, validates content length, rejects transfer encoding, duplicate authorization/size/format/layout headers, unknown formats and invalid layout indices. Header/body reads have socket and overall deadlines. Requests are processed serially.

For each drawing it invokes rootless Podman with a fresh job name, a read-only single-file input mount and a read-only font mount. No shell interpolation is used for rendering. The image ID must be immutable. The parser has:

- no network, capabilities, additional volumes, container API socket or credential files;
- read-only root; writable scratch limited to 768 MiB;
- 2 GiB memory, 2 CPUs, 64 processes and bounded file descriptors/file size;
- 60 CPU seconds and an 80-second gateway wall deadline;
- 32 MiB input and 32 MiB SVG output limits;
- at most 500,000 input records, 1,000,000 unique recorded primitives, 50,000 block references, 2,000 layers and 32 selectable layouts.

The gateway drains output with a deadline and byte limit, removes the job container and deletes its temporary input. Cgroup limits must be verified on the deployment host. OpenRC/cgroupfs deployments can supply an explicitly delegated `cgroup_parent`; do not disable resource limits to make a deployment work.

`worker/render.py` converts DWG with GNU LibreDWG, renders DXF with ezdxf's SVG backend, embeds bounded layout/layer/unit metadata and applies the glyph-checked legacy-font recovery described in FONTS.md. Arabic code-page recovery remains fingerprint-scoped. Stored single-line text-style direction is inherited only when the entity omits its own flags. Images/external references are not fetched.

`worker/blocks.py` shares translation-equivalent block geometry through local SVG definitions and references, preserving paint order. Cache keys include resolved layer/color/line properties and the block transform. Only normal +Z extrusion inserts are eligible; clipping, attributes and array inserts use the ordinary renderer. In this 2D projection insertion elevation does not affect XY output. Nested references use the same output transformation and a shared style table. Adjacent opaque strokes with the same style/layer may share a bounded path, preserving individual subpaths. Resource limits remain enforced even for drawings that cannot benefit from reuse.

Conversion failures have fixed error codes for complexity limits, unsupported/damaged input, empty layouts and timeouts. Nextcloud maps only known codes to fixed English messages; no parser tracebacks, filesystem paths or credentials reach the browser.

## Browser boundary

The public `/viewer` endpoint is an inert static shell, without a user session token or drawing. It is sandboxed with `allow-scripts` and without `allow-same-origin`, creating an opaque origin. Its CSP rejects network connections, frames, objects, forms and base changes, and does not allow eval. Script loading is limited to packaged assets. Inline styles remain allowed for SVG presentation.

The parent dialog sends sanitized SVG by `postMessage`; messages are bound to the exact frame window and a per-open random nonce. Request sequence IDs reject stale rendering results. The child can request a bounded layout index, but cannot select a different file ID or supply a path. It never receives the gateway token or Nextcloud request token.

The SVG sanitizer rejects DTDs/entities, scripts, event attributes, foreign objects, external references and unsafe CSS. This is defense in depth; the opaque frame is the primary session isolation boundary. Static asset reads reject traversal, symlinks, invalid extensions and oversized files. Drawing results are never stored in that public asset directory.
