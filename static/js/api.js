/**
 * Funcions AJAX per comunicar-se amb l'API Flask.
 */
const API = {
    async get(url) {
        const resp = await fetch(url);
        if (resp.status === 401) {
            window.location = '/auth/login';
            return null;
        }
        if (!resp.ok) throw new Error(`GET ${url}: ${resp.status}`);
        return resp.json();
    },

    async post(url, data = {}) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (resp.status === 401) {
            window.location = '/auth/login';
            return null;
        }
        return resp.json();
    },

    async patch(url, data) {
        const resp = await fetch(url, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (resp.status === 401) {
            window.location = '/auth/login';
            return null;
        }
        return resp.json();
    },

    async del(url) {
        const resp = await fetch(url, { method: 'DELETE' });
        if (resp.status === 401) {
            window.location = '/auth/login';
            return null;
        }
        return resp.json();
    },
};
