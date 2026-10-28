document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('cadviewer-connection')
    if (!form) return
    form.addEventListener('submit', async (event) => {
        event.preventDefault()
        const status = document.getElementById('cadviewer-connection-status')
        const button = form.querySelector('button')
        button.disabled = true
        status.textContent = 'Saving…'
        try {
            const response = await fetch(OC.generateUrl('/apps/cadviewer_nextcloud/api/connection'), {
                method: 'POST', credentials: 'same-origin',
                headers: { requesttoken: OC.requestToken, 'Content-Type': 'application/json' },
                body: JSON.stringify(Object.fromEntries(new FormData(form))),
            })
            const result = await response.json()
            status.textContent = result.message || 'Settings could not be saved.'
            if (response.ok) form.elements.token.value = ''
        } catch {
            status.textContent = 'Settings could not be saved.'
        } finally {
            button.disabled = false
        }
    })
})
