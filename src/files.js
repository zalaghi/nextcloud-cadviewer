import { FileType, DefaultType, Permission, registerFileAction } from '@nextcloud/files'

const CAD_EXTENSIONS = new Set(['dwg', 'dxf'])
let currentDialog = null

export function supportsDrawing(node) {
    return node.type === FileType.File && (node.permissions & Permission.READ) !== 0
        && CAD_EXTENSIONS.has(node.basename.split('.').pop().toLowerCase())
}

export async function openDrawing(node) {
    if (currentDialog) currentDialog.close()
    const previousFocus = document.activeElement
    const dialog = document.createElement('dialog')
    currentDialog = dialog
    dialog.className = 'cadviewer-dialog'
    dialog.lang = 'en'
    dialog.dir = 'ltr'
    dialog.setAttribute('aria-label', `CADViewer: ${node.basename}`)
    const header = document.createElement('header')
    const title = document.createElement('strong')
    title.textContent = node.basename
    const close = document.createElement('button')
    close.textContent = 'Close'
    close.setAttribute('aria-label', 'Close CADViewer')
    header.append(title, close)
    const status = document.createElement('p')
    status.className = 'cadviewer-status'
    status.setAttribute('role', 'status')
    status.textContent = 'Preparing drawing…'
    const frame = document.createElement('iframe')
    frame.title = 'CADViewer drawing'
    frame.setAttribute('sandbox', 'allow-scripts')
    frame.referrerPolicy = 'no-referrer'
    const channel = crypto.randomUUID()
    let abort = new AbortController()
    let requestId = 0
    let preview = null
    let ready = false
    let timer
    const send = () => {
        if (ready && preview) {
            frame.contentWindow.postMessage({ type: 'cadviewer:load', channel, ...preview }, '*')
            preview = null
        }
    }
    const onMessage = (event) => {
        // An opaque sandbox necessarily has origin "null". Bind to its exact WindowProxy and nonce.
        if (event.source !== frame.contentWindow || event.origin !== 'null' || event.data?.channel !== channel) return
        if (event.data.type === 'cadviewer:ready') { ready = true; send() }
        if (event.data.type === 'cadviewer:layout' && Number.isInteger(event.data.layoutIndex) && event.data.layoutIndex >= 0 && event.data.layoutIndex < 32) load(event.data.layoutIndex)
        if (event.data.type === 'cadviewer:loaded' && event.data.requestId === requestId) { status.hidden = true; clearTimeout(timer) }
        if (event.data.type === 'cadviewer:error' && event.data.requestId === requestId) { status.textContent = 'The drawing preview could not be displayed.'; clearTimeout(timer) }
    }
    window.addEventListener('message', onMessage)
    close.addEventListener('click', () => dialog.close())
    dialog.addEventListener('close', () => {
        abort.abort()
        clearTimeout(timer)
        window.removeEventListener('message', onMessage)
        dialog.remove()
        if (currentDialog === dialog) currentDialog = null
        previousFocus?.focus()
    }, { once: true })
    dialog.append(header, status, frame)
    document.body.append(dialog)
    frame.src = OC.generateUrl('/apps/cadviewer_nextcloud/viewer') + '#' + channel
    dialog.showModal()
    close.focus()
    async function load(layoutIndex = 0) {
        abort.abort()
        abort = new AbortController()
        const signal = abort.signal
        const id = ++requestId
        preview = null
        clearTimeout(timer)
        status.hidden = false
        status.textContent = 'Preparing drawing…'
        timer = setTimeout(() => { status.hidden = false; status.textContent = 'The drawing is taking too long to open. Please close it and try again.'; abort.abort() }, 100000)
        try {
            const response = await fetch(OC.generateUrl('/apps/cadviewer_nextcloud/api/preview'), {
                method: 'POST', credentials: 'same-origin', signal,
                headers: { requesttoken: OC.requestToken, 'Content-Type': 'application/json' },
                body: JSON.stringify({ fileId: node.fileid, layoutIndex }),
            })
            const result = await response.json()
            if (signal.aborted || id !== requestId) return
            if (!response.ok || typeof result.svg !== 'string') throw new Error(result.message || 'CADViewer could not open this drawing.')
            preview = { svg: result.svg, requestId: id }
            send()
        } catch (error) {
            if (!signal.aborted && id === requestId) {
                status.textContent = error.message
                clearTimeout(timer)
                frame.contentWindow.postMessage({ type: 'cadviewer:failed', channel }, '*')
            }
        }
    }
    await load()
    return null
}

registerFileAction({
    id: 'cadviewer-nextcloud-open', displayName: () => 'Open with CADViewer',
    iconSvgInline: () => '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M3 3h18v18H3zm2 2v14h14V5zm2 10 4-8 6 10h-3l-3-5-2 3z"/></svg>',
    enabled: ({ nodes, view }) => view?.id !== 'trashbin' && nodes.length === 1 && nodes.every(supportsDrawing),
    exec: ({ nodes }) => openDrawing(nodes[0]), default: DefaultType.DEFAULT, order: 20,
})
