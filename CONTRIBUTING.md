# Contributing

Keep the interface English and the app completely free/open source. Do not introduce paid SDKs, activation systems or trial restrictions. Retain upstream and third-party notices.

Respect these boundaries:

- Modify only this app and its separate worker. No Nextcloud core, global MIME, `.htaccess`, filecache or AIO image modifications.
- Resolve drawings through the current user's Nextcloud file API; never accept arbitrary paths or user-controlled converter URLs.
- Preserve the opaque-origin iframe, CSRF/admin checks, post-conversion permission/content checks and bounded worker isolation.
- Keep user fonts, drawings, secrets, `.local/`, build images and production configuration out of Git.
- Add a legacy font mapping only with a verified fingerprint, an encoding explanation and representative fixtures. Never execute uploaded AutoLISP.

Use Node 24+, `npm ci --ignore-scripts` and the isolated frontend build script. Worker inputs are pinned; update hashes and notices deliberately. Run the relevant disposable Nextcloud, worker and browser checks; document skipped/private-fixture checks accurately. Reproduce defects with synthetic/non-sensitive inputs where possible.

A pull request should state the problem, resulting behavior, validation and important limitations. Do not claim support for a format, PHP/Nextcloud version or font family solely by widening metadata. New features should include a concise user-facing explanation and a meaningful acceptance check.
