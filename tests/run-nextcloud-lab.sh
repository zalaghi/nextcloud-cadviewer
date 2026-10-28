#!/bin/sh
set -eu
umask 077
mkdir -p /scratch/home /scratch/tmp /scratch/nextcloud
cp -R /usr/src/nextcloud/. /scratch/nextcloud/
mkdir -p /scratch/nextcloud/custom_apps/cadviewer_nextcloud
cp -R /source/. /scratch/nextcloud/custom_apps/cadviewer_nextcloud/
cd /scratch/nextcloud
php occ maintenance:install --database=sqlite --admin-user=cadviewer-lab \
    --admin-pass=local-isolated-lab-only --data-dir=/scratch/nextcloud/data
php /source/tests/core-integrity.php before
php occ app:enable cadviewer_nextcloud
php /source/tests/nextcloud-smoke.php
php /source/tests/nextcloud-security.php > /scratch/security-test.log 2>&1 || {
    cat /scratch/security-test.log
    exit 1
}
cat /scratch/security-test.log
grep -qx 'PASS focused security regression suite (not a complete app audit)' /scratch/security-test.log
php /source/tests/nextcloud-viewer.php
php occ app:disable cadviewer_nextcloud
php /source/tests/core-integrity.php after
find /source/lib /source/appinfo /source/templates \
    -name '*.php' -print0 | xargs -0 -n 1 php -l
