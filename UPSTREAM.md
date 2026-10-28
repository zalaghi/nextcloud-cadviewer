# Provenance and attribution

This project derives from the AGPL-licensed Nextcloud integration at https://github.com/CADViewer/NextCloud, inspected at commit `dbd1f2fd3a504e0fd58af7fed774261133fa9765`.

Original integration authors include Casper Harnung, Kevin Wamba and Zoran Miladinovic. The original GNU AGPL v3 license text is retained in COPYING; package metadata declares AGPL-3.0-or-later. This independent project is maintained by Amir Zalaghi.

The original repository also bundled proprietary CADViewer SDK and AutoXChange materials. Those components, commercial activation paths, legacy converter scripts, vendor assets and sample drawings are **not included** in this public project. Their license checks have not been patched or bypassed. DWG reading and drawing rendering use separate open-source engines instead.

The original nextcloud integration was substantially reworked: public API bootstrap, Files action, authorized ID-based reads, post-conversion permission/content checks, isolated converter gateway, new SVG controls, opaque iframe, SVG sanitization and English-only UI. Global MIME/core edits and legacy filesystem proxy endpoints were removed.

The independent app ID `cadviewer_nextcloud` avoids collision with the upstream `cadviewer` app. Repository history starts with this public implementation so historical proprietary payloads and private research inputs are not published. The original upstream checkout remains a local reference, not part of the new repository history.
