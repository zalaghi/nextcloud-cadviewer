/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Offline SVG controls in an opaque-origin frame. No Nextcloud credentials. */
(() => {
    'use strict'
    const channel = location.hash.slice(1)
    if (!/^[0-9a-f-]{36}$/.test(channel) || parent === window) return
    const notify = (type, data = {}) => parent.postMessage({ type, channel, ...data }, '*')
    const element = (name, text, className) => {
        const node = document.createElement(name)
        if (text) node.textContent = text
        if (className) node.className = className
        return node
    }
    const main = document.getElementById('viewer')
    const toolbar = element('div', '', 'toolbar')
    toolbar.setAttribute('role', 'toolbar')
    toolbar.setAttribute('aria-label', 'Drawing controls')
    const viewport = element('div', '', 'viewport')
    viewport.tabIndex = 0
    viewport.setAttribute('aria-label', 'Drawing. Use plus and minus to zoom, arrows to pan, and F to fit.')
    const status = element('div', 'Preparing drawing…', 'status')
    status.setAttribute('role', 'status')
    const layersPanel = element('aside', '', 'layers')
    layersPanel.hidden = true
    layersPanel.setAttribute('aria-label', 'Drawing layers')
    const content = element('div', '', 'content')
    content.append(layersPanel, viewport)
    main.append(toolbar, content, status)
    let drawing, fullBox, box, metadata, measuring = false, firstPoint, drag, requestId = 0, strokes = []
    const applyLineweights = () => {
        const enabled = viewport.classList.contains('lineweights')
        // Inline styles also apply inside SVG <use> shadow trees. Ancestor CSS
        // selectors alone do not reliably reach paths in repeated blocks.
        for (const { path, width, effect } of strokes) {
            path.style.strokeWidth = enabled ? width : '1px'
            path.style.vectorEffect = enabled ? effect : 'non-scaling-stroke'
        }
    }
    const button = (title, action) => {
        const node = element('button', title)
        node.type = 'button'
        node.addEventListener('click', action)
        toolbar.append(node)
        return node
    }
    const applyBox = () => drawing?.setAttribute('viewBox', box.join(' '))
    const fit = () => { if (drawing) { box = [...fullBox]; applyBox() } }
    const zoom = (factor, center) => {
        if (!drawing) return
        const ratio = box[2] * factor / fullBox[2]
        if (ratio < 0.00001 || ratio > 20) return
        const [x, y] = center || [box[0] + box[2] / 2, box[1] + box[3] / 2]
        box = [x + (box[0] - x) * factor, y + (box[1] - y) * factor, box[2] * factor, box[3] * factor]
        applyBox()
    }
    button('Zoom in', () => zoom(0.75))
    button('Zoom out', () => zoom(1.333333))
    button('Fit', fit)
    const layersButton = button('Layers', () => {
        layersPanel.hidden = !layersPanel.hidden
        layersButton.setAttribute('aria-expanded', String(!layersPanel.hidden))
    })
    layersButton.setAttribute('aria-expanded', 'false')
    const monochromeButton = button('Monochrome', () => {
        viewport.classList.toggle('monochrome')
        monochromeButton.setAttribute('aria-pressed', String(viewport.classList.contains('monochrome')))
    })
    monochromeButton.setAttribute('aria-pressed', 'false')
    const lineweightsButton = button('Lineweights', () => {
        viewport.classList.toggle('lineweights')
        lineweightsButton.setAttribute('aria-pressed', String(viewport.classList.contains('lineweights')))
        applyLineweights()
    })
    lineweightsButton.setAttribute('aria-pressed', 'false')
    lineweightsButton.title = 'Show rendered lineweights. Off keeps strokes thin while zooming.'
    const measureButton = button('Measure', () => {
        measuring = !measuring
        firstPoint = null
        viewport.classList.toggle('measuring', measuring)
        measureButton.setAttribute('aria-pressed', String(measuring))
        status.textContent = measuring ? 'Select two points. Distances follow the units saved in the drawing.' : 'Drag to pan · Scroll to zoom · Double-click to fit'
        drawing?.querySelectorAll('[data-measurement]').forEach(node => node.remove())
    })
    measureButton.setAttribute('aria-pressed', 'false')
    const label = element('label', 'Layout ')
    const layoutSelect = element('select')
    layoutSelect.setAttribute('aria-label', 'Layout')
    label.append(layoutSelect)
    toolbar.append(label)
    layoutSelect.addEventListener('change', () => {
        layoutSelect.disabled = true
        status.textContent = 'Preparing layout…'
        notify('cadviewer:layout', { layoutIndex: Number(layoutSelect.value) })
    })
    const point = (event) => {
        const p = drawing.createSVGPoint()
        p.x = event.clientX; p.y = event.clientY
        const transformed = p.matrixTransform(drawing.getScreenCTM().inverse())
        return [transformed.x, transformed.y]
    }
    viewport.addEventListener('wheel', event => {
        if (!drawing) return
        event.preventDefault()
        zoom(Math.exp(Math.max(-1, Math.min(1, event.deltaY / 300))), point(event))
    }, { passive: false })
    viewport.addEventListener('dblclick', fit)
    viewport.addEventListener('pointerdown', event => {
        if (!drawing || event.button !== 0) return
        viewport.focus()
        const p = point(event)
        if (measuring) {
            if (!firstPoint) { firstPoint = p; status.textContent = 'Select the second point.'; return }
            drawing.querySelectorAll('[data-measurement]').forEach(node => node.remove())
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
            for (const [key, value] of Object.entries({ x1: firstPoint[0], y1: firstPoint[1], x2: p[0], y2: p[1], stroke: '#e11d48', 'stroke-width': 2, 'vector-effect': 'non-scaling-stroke', 'data-measurement': '' })) line.setAttribute(key, value)
            drawing.append(line)
            const distance = Math.hypot(p[0] - firstPoint[0], p[1] - firstPoint[1]) * metadata.unitsPerSvgUnit
            status.textContent = `Distance: ${distance.toLocaleString('en-US', { maximumFractionDigits: 4 })} ${metadata.unit}. Approximate point selection; verify critical dimensions in CAD.`
            firstPoint = null
            return
        }
        drag = { point: p, box: [...box], id: event.pointerId }
        viewport.setPointerCapture(event.pointerId)
    })
    viewport.addEventListener('pointermove', event => {
        if (!drag || event.pointerId !== drag.id) return
        const p = point(event)
        box[0] += drag.point[0] - p[0]; box[1] += drag.point[1] - p[1]
        applyBox()
    })
    const endDrag = () => { drag = null }
    viewport.addEventListener('pointerup', endDrag)
    viewport.addEventListener('pointercancel', endDrag)
    viewport.addEventListener('keydown', event => {
        if (!drawing) return
        if (event.key === '+' || event.key === '=') zoom(0.75)
        else if (event.key === '-') zoom(1.333333)
        else if (event.key.toLowerCase() === 'f') fit()
        else if (event.key.startsWith('Arrow')) {
            const deltas = { ArrowLeft: [-0.1, 0], ArrowRight: [0.1, 0], ArrowUp: [0, -0.1], ArrowDown: [0, 0.1] }
            const [dx, dy] = deltas[event.key]
            box[0] += box[2] * dx; box[1] += box[3] * dy; applyBox()
        } else return
        event.preventDefault()
    })
    window.addEventListener('message', event => {
        if (event.source !== parent || event.data?.channel !== channel) return
        if (event.data.type === 'cadviewer:failed') {
            layoutSelect.disabled = false
            if (metadata) layoutSelect.value = String(metadata.layout)
            status.textContent = 'The requested layout could not be opened.'
            return
        }
        if (event.data.type !== 'cadviewer:load' || !Number.isSafeInteger(event.data.requestId) || event.data.requestId < requestId) return
        if (typeof event.data.svg !== 'string' || event.data.svg.length > 32 * 1024 * 1024) {
            notify('cadviewer:error', { requestId: event.data.requestId })
            return
        }
        requestId = event.data.requestId
        try {
            const parsed = new DOMParser().parseFromString(event.data.svg, 'image/svg+xml')
            const root = parsed.documentElement
            if (root.localName !== 'svg' || root.namespaceURI !== 'http://www.w3.org/2000/svg' || parsed.querySelector('parsererror')) throw new Error('Invalid SVG')
            const info = JSON.parse(root.querySelector('metadata[id="cadviewer-info"]').textContent)
            if (!Array.isArray(info.layouts) || !info.layouts.length || info.layouts.length > 32 || !info.layouts.every(n => typeof n === 'string')
                || !Number.isSafeInteger(info.layout) || !info.layouts[info.layout] || !Number.isFinite(info.unitsPerSvgUnit) || info.unitsPerSvgUnit <= 0) throw new Error('Invalid metadata')
            fullBox = root.getAttribute('viewBox').trim().split(/[\s,]+/).map(Number)
            if (fullBox.length !== 4 || !fullBox.every(Number.isFinite) || fullBox[2] <= 0 || fullBox[3] <= 0) throw new Error('Invalid geometry')
            drawing = document.importNode(root, true)
            drawing.id = 'cad-drawing'
            drawing.removeAttribute('width'); drawing.removeAttribute('height')
            drawing.setAttribute('preserveAspectRatio', 'xMidYMid meet')
            viewport.replaceChildren(drawing)
            strokes = Array.from(drawing.querySelectorAll('path'), path => ({
                path, width: path.style.strokeWidth, effect: path.style.vectorEffect,
            }))
            applyLineweights()
            metadata = info; firstPoint = null; drag = null
            fit()
            layoutSelect.replaceChildren(...info.layouts.map((name, i) => {
                const option = element('option', name.slice(0, 200)); option.value = i; return option
            }))
            layoutSelect.value = String(info.layout); layoutSelect.disabled = false
            const byLayer = new Map()
            drawing.querySelectorAll('[data-layer]').forEach(node => {
                const name = node.getAttribute('data-layer')
                if (!byLayer.has(name)) byLayer.set(name, [])
                byLayer.get(name).push(node)
            })
            layersPanel.replaceChildren(element('h2', 'Layers'))
            for (const [name, nodes] of byLayer) {
                const row = element('label')
                const check = element('input'); check.type = 'checkbox'; check.checked = true
                check.addEventListener('change', () => nodes.forEach(node => node.toggleAttribute('hidden', !check.checked)))
                row.append(check, element('span', name)); layersPanel.append(row)
            }
            const missing = Array.isArray(info.missingFonts) ? info.missingFonts.filter(f => typeof f === 'string').slice(0, 20) : []
            status.textContent = missing.length ? `Drawing opened with substitute fonts: ${missing.join(', ')}. Text appearance may differ from the original.` : 'Drag to pan · Scroll to zoom · Double-click to fit'
            notify('cadviewer:loaded', { requestId })
        } catch { notify('cadviewer:error', { requestId }) }
    })
    notify('cadviewer:ready')
})()
