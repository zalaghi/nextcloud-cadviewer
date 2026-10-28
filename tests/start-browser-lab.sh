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
php /source/tests/browser-seed.php
php -S 127.0.0.1:8090 /source/tests/browser-fixture-service.php >/scratch/fixture-http.log 2>&1 &
php -S 127.0.0.1:8080 /source/tests/browser-router.php >/scratch/nextcloud-http.log 2>&1 &
echo BROWSER_LAB_READY
wait
