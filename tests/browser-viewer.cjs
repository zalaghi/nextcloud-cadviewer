const { chromium } = require('/packages/playwright')
const fs = require('node:fs')
;(async () => {
    const browser = await chromium.launch({ executablePath: '/browser/chrome-headless-shell', headless: true })
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', e => errors.push(e.message.slice(0, 400)))
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 400)) })
    page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`.slice(0, 400)) })
    try {
        await page.goto('http://127.0.0.1:8080/index.php/login', { waitUntil: 'networkidle', timeout: 45000 })
        await page.locator('input[name="user"]').fill('cadviewer-lab')
        await page.locator('input[name="password"]').fill('local-isolated-lab-only')
        await page.getByRole('button', { name: 'Log in', exact: true }).click()
        await page.waitForURL(/\/apps\//, { timeout: 45000 })
        await page.goto('http://127.0.0.1:8080/index.php/apps/files/files', { waitUntil: 'domcontentloaded' })
        const welcomeClose = page.getByRole('button', { name: 'Close', exact: true })
        await welcomeClose.first().click({ timeout: 8000 }).catch(() => {})
        await page.getByRole('button', { name: 'Open with CADViewer: Persian CAD.dxf' }).click({ timeout: 30000 })
        const frameElement = page.locator('.cadviewer-dialog iframe')
        await frameElement.waitFor({ timeout: 15000 })
        const frame = await frameElement.elementHandle().then(e => e.contentFrame())
        await frame.waitForFunction(() => document.querySelectorAll('#cad-drawing path').length > 25, { timeout: 30000 })
        await page.locator('.cadviewer-status').waitFor({ state: 'hidden', timeout: 15000 })
        const state = await frame.evaluate(() => {
            let isolated = false
            try { void parent.document } catch (e) { isolated = e.name === 'SecurityError' }
            return { isolated, language: document.documentElement.lang,
                paths: document.querySelectorAll('#cad-drawing path').length,
                drawing: !!document.querySelector('#cad-drawing'),
                title: document.title }
        })
        if (!state.isolated || state.language !== 'en' || !state.drawing) throw new Error('Viewer acceptance checks failed')
        const originalBox = await frame.locator('#cad-drawing').getAttribute('viewBox')
        await frame.getByRole('button', { name: 'Zoom in', exact: true }).click()
        if (await frame.locator('#cad-drawing').getAttribute('viewBox') === originalBox) throw new Error('Zoom did not change view')
        await frame.getByRole('button', { name: 'Fit', exact: true }).click()
        if (await frame.locator('#cad-drawing').getAttribute('viewBox') !== originalBox) throw new Error('Fit did not restore view')
        await frame.getByRole('button', { name: 'Layers', exact: true }).click()
        const layer = frame.locator('.layers input').first()
        await layer.uncheck()
        if (!(await frame.locator('#cad-drawing [data-layer][hidden]').count())) throw new Error('Layer toggle failed')
        await layer.check()
        await frame.getByRole('button', { name: 'Layers', exact: true }).click()
        if (/trial|activation|license key/i.test(await frame.locator('body').innerText())) throw new Error('Commercial activation UI remains')
        await page.screenshot({ path: '/scratch/viewer.png' })
        console.error(JSON.stringify({ status: 'PASS', state, errors }, null, 2))
        await frame.getByRole('button', { name: 'Monochrome', exact: true }).click()
        if (!(await frame.locator('.viewport.monochrome').count())) throw new Error('Monochrome toggle failed')
        await page.screenshot({ path: '/scratch/viewer.png' })
        // A failed layout conversion keeps the existing drawing and restores the selector.
        await frame.getByRole('combobox', { name: 'Layout', exact: true }).selectOption('1')
        await frame.getByText('The requested layout could not be opened.', { exact: true }).waitFor()
        if (await frame.getByRole('combobox', { name: 'Layout', exact: true }).inputValue() !== '0') throw new Error('Layout recovery failed')
        await page.getByRole('button', { name: 'Close CADViewer' }).click()
        if (await page.locator('.cadviewer-dialog').count()) throw new Error('Dialog did not close')
        await page.getByRole('button', { name: 'Open with CADViewer: Persian Plan.dwg' }).click()
        const dwgElement = page.locator('.cadviewer-dialog iframe')
        await dwgElement.waitFor()
        const dwgFrame = await dwgElement.elementHandle().then(e => e.contentFrame())
        await dwgFrame.waitForFunction(() => document.querySelectorAll('#cad-drawing path').length > 25)
        await page.locator('.cadviewer-status').waitFor({ state: 'hidden' })
        await dwgFrame.getByRole('button', { name: 'Monochrome', exact: true }).click()
        await page.screenshot({ path: '/scratch/plan.png' })
        await page.getByRole('button', { name: 'Close CADViewer' }).click()
        console.error('PASS DXF and DWG Files integration, isolated frame, controls and layout error recovery')
    } catch (error) {
        await page.screenshot({ path: '/scratch/viewer.png' }).catch(() => {})
        console.error(JSON.stringify({ status: 'FAIL', message: error.message,
            text: (await page.locator('body').innerText().catch(() => 'Page unavailable')).slice(0, 6000), errors }, null, 2))
        process.exitCode = 1
    } finally {
        await browser.close()
    }
})()
