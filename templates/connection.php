<?php
declare(strict_types=1);
/** @var array $_ */
?>
<div class="section" lang="en" dir="ltr">
    <h2>CADViewer</h2>
    <p>Free, open-source DWG and DXF viewing in Files. Drawing conversion runs in a separate, isolated service.</p>
    <p>CADViewer does not change Nextcloud core files, MIME mappings, or the AIO image.</p>
    <form id="cadviewer-connection">
        <p><label for="cadviewer-endpoint">Conversion service URL</label><br>
        <input id="cadviewer-endpoint" name="endpoint" type="url" size="60" required
            placeholder="https://cad-worker.example/convert" value="<?php p($_['endpoint']); ?>"></p>
        <p><label for="cadviewer-token">Conversion service token</label><br>
        <input id="cadviewer-token" name="token" type="password" autocomplete="new-password" size="60"
            placeholder="Leave blank to keep the saved token"></p>
        <button type="submit">Save</button>
        <p id="cadviewer-connection-status" role="status"></p>
    </form>
    <p>Install drawing fonts in the conversion service. Persian SHX fonts affect drawing text only; the viewer interface is English.</p>
</div>
