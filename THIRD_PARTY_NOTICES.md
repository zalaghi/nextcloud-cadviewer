# Third-party components

| Component | Version used | License / source |
| --- | --- | --- |
| Original Nextcloud integration | dbd1f2fd3a504e0fd58af7fed774261133fa9765 | AGPL; https://github.com/CADViewer/NextCloud |
| GNU LibreDWG | 0.14 | GPL-3.0-or-later; https://www.gnu.org/software/libredwg/ |
| ezdxf | 1.4.5 | MIT; https://github.com/mozman/ezdxf |
| fontTools | 4.68.0 | MIT; https://github.com/fonttools/fonttools |
| NumPy | 2.5.4 | BSD-3-Clause and bundled dependency notices; https://numpy.org/ |
| Pillow | 13.0.0 | HPND and bundled dependency notices; https://python-pillow.github.io/ |
| pyparsing | 3.3.3 | MIT; https://github.com/pyparsing/pyparsing |
| typing_extensions | 4.16.0 | PSF-2.0; https://github.com/python/typing_extensions |
| @nextcloud/files | 4.1.1 | AGPL-3.0-or-later; https://github.com/nextcloud-libraries/nextcloud-files |
| Vazirmatn | 33.003, nine static weights | SIL OFL 1.1; https://github.com/rastikerdar/vazirmatn; original OFL.txt and AUTHORS.txt in fonts/vazirmatn/ |
| Liberation Sans fallback | 2.1.5, Regular | SIL OFL 1.1; https://github.com/liberationfonts/liberation-fonts; original LICENSE in fonts/liberation/ |

The worker image includes the exact LibreDWG source archive and license, the app license, the bundled fonts' notices and checksum manifest, and installed Python distribution notices. The application includes the generated JavaScript bundle's license notices. Transitive JavaScript dependencies are recorded in package-lock.json. Python wheels are hash-locked in worker/requirements.lock.

Do not remove these notices when redistributing. No private SHX fonts, AutoLISP files, external drawings, proprietary SDK, or commercial converter binaries are shipped here. Host operating systems and OCI base images retain their own package licenses and update obligations.
