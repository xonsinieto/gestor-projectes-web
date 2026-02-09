/**
 * Gestor de Projectes — Logica principal del frontend web.
 */
const App = {
    projecteActual: null,
    filtrePersona: '',
    cercaText: '',
    mostrarArxivats: false,
    _cercaTimer: null,
    _pollTimer: null,
    usuaris: [],
    _projectesData: [],
    _resumUsuaris: [],
    _fotosCache: {},  // Cache: nom -> url (blob o fallback)

    // Colors d'usuari (mateixos que desktop)
    COLORS_USUARIS: ['#3B82F6','#10B981','#F59E0B','#EF4444','#8B5CF6','#EC4899','#06B6D4','#F97316'],

    // --- INICIALITZACIO ---

    async init() {
        this._bindEvents();
        await this.carregarProjectes();
        this._iniciarPolling();
        this._carregarNotificacions();
    },

    _bindEvents() {
        document.getElementById('btn-afegir-projecte').addEventListener('click', () => this.mostrarDialogAfegirProjecte());
        document.getElementById('btn-afegir-tasca').addEventListener('click', () => this.mostrarDialogAfegirTasques());
        document.getElementById('btn-tornar').addEventListener('click', () => this.tornarALlista());
        document.getElementById('btn-notif').addEventListener('click', () => this.toggleNotificacions());
        document.getElementById('cerca').addEventListener('input', (e) => this._onCerca(e.target.value));
        document.getElementById('btn-arxivats').addEventListener('click', () => this.toggleArxivats());
    },

    // --- UTILS COLOR ---

    _colorPerUsuari(nom) {
        const idx = this.usuaris.indexOf(nom);
        return this.COLORS_USUARIS[(idx >= 0 ? idx : 0) % this.COLORS_USUARIS.length];
    },

    _colorPerPercentatge(pct) {
        if (pct >= 100) return '#10B981';
        if (pct >= 50) return '#F59E0B';
        if (pct > 0) return '#3B82F6';
        return '#6B7280';
    },

    _inicialsUsuari(nom) {
        return nom.split(' ').map(p => p[0]).join('').substring(0, 2).toUpperCase();
    },

    // --- FOTOS D'USUARI ---

    async _carregarFoto(nom) {
        if (this._fotosCache[nom] !== undefined) return this._fotosCache[nom];
        try {
            const resp = await fetch(`/api/foto/${encodeURIComponent(nom)}`);
            if (resp.ok) {
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                this._fotosCache[nom] = url;
                return url;
            }
        } catch (e) { /* ignora */ }
        this._fotosCache[nom] = null;
        return null;
    },

    async _carregarTotesFotos() {
        if (!this.usuaris.length) return;
        const promises = this.usuaris.map(u => this._carregarFoto(u));
        await Promise.all(promises);
    },

    _renderAvatarHTML(nom, mida, extraClasses) {
        const fotoUrl = this._fotosCache[nom];
        const inicials = this._inicialsUsuari(nom);
        const color = this._colorPerUsuari(nom);
        const sz = mida || 28;
        const cls = extraClasses || '';
        if (fotoUrl) {
            return `<img src="${fotoUrl}" class="avatar-foto ${cls}" style="width:${sz}px;height:${sz}px;border-radius:50%;object-fit:cover" title="${this._esc(nom)}">`;
        }
        return `<span class="projecte-avatar ${cls}" style="background:${color};width:${sz}px;height:${sz}px;font-size:${sz * 0.4}px" title="${this._esc(nom)}">${inicials}</span>`;
    },

    // --- ARXIVATS ---

    toggleArxivats() {
        this.mostrarArxivats = !this.mostrarArxivats;
        const btn = document.getElementById('btn-arxivats');
        btn.classList.toggle('active', this.mostrarArxivats);
        document.getElementById('panel-title-text').textContent = this.mostrarArxivats ? 'ARXIVATS' : 'PROJECTES';
        this.carregarProjectes();
    },

    // --- PROJECTES ---

    async carregarProjectes() {
        let url = '/api/projectes';
        const params = [];
        if (this.filtrePersona) params.push(`persona=${encodeURIComponent(this.filtrePersona)}`);
        if (this.cercaText) params.push(`cerca=${encodeURIComponent(this.cercaText)}`);
        if (this.mostrarArxivats) params.push('arxivats=1');
        if (params.length) url += '?' + params.join('&');

        const resp = await API.get(url);
        if (!resp) return;

        // Resposta ara es objecte: {projectes, usuaris, resum}
        const projectes = resp.projectes || [];
        this._projectesData = projectes;
        this.usuaris = resp.usuaris || this.usuaris;
        this._resumUsuaris = resp.resum || [];

        this._renderProjectes(projectes);
        this._renderBarraInferior();

        // Carregar fotos en background si no estan cached
        if (this.usuaris.length && !this._fotosLoaded) {
            this._fotosLoaded = true;
            this._carregarTotesFotos().then(() => {
                // Re-render amb fotos un cop carregades
                this._renderProjectes(this._projectesData);
                this._renderFilterAvatars(this.usuaris);
            });
        }

        // Render filter avatars si tenim usuaris
        if (this.usuaris.length) {
            this._renderFilterAvatars(this.usuaris);
        }
    },

    _renderProjectes(projectes) {
        const container = document.getElementById('projectes-llista');
        if (!projectes.length) {
            container.innerHTML = '<div class="empty-state">Cap projecte trobat.</div>';
            return;
        }

        container.innerHTML = projectes.map(p => {
            const seleccionat = this.projecteActual === p.nom_carpeta ? 'selected' : '';
            const prioritari = p.prioritari
                ? `<button class="badge-prioritari" onclick="event.stopPropagation();App.togglePrioritat('${this._esc(p.nom_carpeta)}',false)" title="Treure prioritat">!</button>`
                : `<button class="badge-prioritari-off" onclick="event.stopPropagation();App.togglePrioritat('${this._esc(p.nom_carpeta)}',true)" title="Marcar prioritari">!</button>`;
            const pct = p.percentatge;
            const colorBarra = this._colorPerPercentatge(pct);
            const colorPct = pct >= 100 ? '#10B981' : '#374151';

            // Avatars dels usuaris implicats
            let avatarsHTML = '';
            if (p.usuaris_implicats && p.usuaris_implicats.length) {
                avatarsHTML = '<div class="projecte-avatars">';
                for (const u of p.usuaris_implicats) {
                    const esPropi = u === CONFIG.usuariActual;
                    const tePendents = (p.usuaris_pendents || []).includes(u);
                    let classes = '';
                    if (!esPropi) classes += ' inactiu';
                    if (tePendents) classes += ' te-pendents';
                    avatarsHTML += this._renderAvatarHTML(u, 24, classes.trim());
                }
                avatarsHTML += '</div>';
            }

            return `
                <div class="projecte-item ${seleccionat}" data-nom="${this._esc(p.nom_carpeta)}"
                     onclick="App.seleccionarProjecte('${this._esc(p.nom_carpeta)}')">
                    <div class="projecte-item-top">
                        ${prioritari}
                        <span class="projecte-nom">${this._esc(p.codi)} ${this._esc(p.descripcio)}</span>
                    </div>
                    <div class="barra-progres">
                        <div class="barra-progres-fill" style="width:${pct}%;background:${colorBarra}"></div>
                    </div>
                    <div class="projecte-item-bottom">
                        <span class="projecte-stats">${p.tasques_completades}/${p.total_tasques}</span>
                        <span class="projecte-pct" style="color:${colorPct}">${pct}%</span>
                        ${avatarsHTML}
                    </div>
                </div>`;
        }).join('');
    },

    async seleccionarProjecte(nom) {
        this.projecteActual = nom;
        document.getElementById('panel-detall').classList.add('active');
        // Carregar detall i actualitzar llista en paral·lel
        await Promise.all([
            this._carregarDetall(nom),
            this.carregarProjectes(),
        ]);
    },

    async _carregarDetall(nom) {
        const proj = await API.get(`/api/projectes/${encodeURIComponent(nom)}`);
        if (!proj) return;

        this.usuaris = proj.usuaris || [];
        this._resumUsuaris = proj.resum || this._resumUsuaris;

        // Header
        document.getElementById('detall-header').classList.remove('hidden');
        document.getElementById('titol-projecte').textContent = `${proj.codi} ${proj.descripcio}`;
        const progresEl = document.getElementById('progres-projecte');
        progresEl.textContent = `${proj.tasques_completades}/${proj.total_tasques} completades (${proj.percentatge}%)`;
        progresEl.style.color = proj.percentatge >= 100 ? '#10B981' : '#374151';

        // Overview (cercles de tasques)
        this._renderOverview(proj.tasques);

        // Filtrar: no mostrar completades a la llista
        let tasques = proj.tasques.filter(t => t.estat !== CONFIG.COMPLETADA);

        // Ordenar: primer les propies
        tasques.sort((a, b) => {
            const aPropi = a.assignat === CONFIG.usuariActual ? 0 : 1;
            const bPropi = b.assignat === CONFIG.usuariActual ? 0 : 1;
            return aPropi - bPropi;
        });

        // Filtre per persona
        if (this.filtrePersona) {
            tasques = tasques.filter(t => t.assignat === this.filtrePersona);
        }

        this._renderTasques(tasques, nom);

        // Actualitzar filter avatars i barra inferior
        this._renderFilterAvatars(proj.usuaris);
        this._renderBarraInferior();
    },

    _renderOverview(tasques) {
        const container = document.getElementById('overview-tasques');
        if (!tasques.length) {
            container.innerHTML = '';
            return;
        }

        // Filtrar per persona si cal
        let tasquesFiltrades = tasques;
        if (this.filtrePersona) {
            tasquesFiltrades = tasques.filter(t => t.assignat === this.filtrePersona);
        }
        if (!tasquesFiltrades.length) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = tasquesFiltrades.map(t => {
            const color = CONFIG.colors[t.estat] || '#9CA3AF';
            const completada = t.estat === CONFIG.COMPLETADA;
            const textColor = completada ? '#1F2937' : '#6B7280';
            const fontWeight = completada ? ' completada' : '';
            const docClick = completada && t.document
                ? `onclick="App.obrirDocument('${this._esc(t.document)}')"` : '';
            const cursorStyle = completada && t.document ? 'cursor:pointer;' : '';

            // Avatar petit gris amb vora del color de l'estat (identic al desktop)
            let avatarHTML = '';
            if (t.assignat) {
                const fotoUrl = this._fotosCache[t.assignat];
                if (fotoUrl) {
                    avatarHTML = `<img src="${fotoUrl}" class="overview-avatar" style="border:2px solid ${color}">`;
                } else {
                    const inicials = this._inicialsUsuari(t.assignat);
                    const bgColor = this._colorPerUsuari(t.assignat);
                    avatarHTML = `<span class="overview-avatar-inicials" style="background:${bgColor};border:2px solid ${color}">${inicials}</span>`;
                }
            }

            return `<div class="overview-item">
                <span class="overview-dot-circle" style="color:${color}">●</span>
                <span class="overview-nom${fontWeight}" style="color:${textColor};${cursorStyle}" ${docClick} title="${this._esc(t.nom)}">${this._esc(t.nom)}</span>
                ${avatarHTML}
            </div>`;
        }).join('');
    },

    _renderTasques(tasques, nomProjecte) {
        const container = document.getElementById('tasques-llista');
        if (!tasques.length) {
            container.innerHTML = '<div class="empty-state">Totes les tasques estan completades!</div>';
            return;
        }

        container.innerHTML = tasques.map(t => this._renderFilaTasca(t, nomProjecte)).join('');
    },

    _renderFilaTasca(t, nomProjecte) {
        const esPropi = t.assignat === CONFIG.usuariActual;
        const classPropi = esPropi ? ' propia' : '';
        const assignatHTML = this._renderAssignacio(t, nomProjecte);
        const estatsHTML = this._renderBotonsEstat(t, nomProjecte);
        const docInlineHTML = t.document ? this._renderDocumentInline(t, nomProjecte) : '';
        const obsHTML = this._renderObservacions(t, nomProjecte);

        // Layout identic al desktop: 2 files
        // Fila 1: nom tasca + avatars assignacio
        // Fila 2: botons estat (pills) + enviar + document (pill verd) + x eliminar
        return `
            <div class="fila-tasca${classPropi}">
                <div class="fila-tasca-row1">
                    <span class="tasca-nom">${this._esc(t.nom)}</span>
                    <div class="tasca-avatars">${assignatHTML}</div>
                </div>
                <div class="fila-tasca-row2">
                    <div class="tasca-estats">${estatsHTML}</div>
                    <div class="tasca-row2-right">
                        ${docInlineHTML}
                        <button class="btn-eliminar-tasca" onclick="App.confirmarEliminarTasca('${this._esc(nomProjecte)}','${this._esc(t.nom)}')" title="Eliminar">&times;</button>
                    </div>
                </div>
                ${obsHTML}
            </div>`;
    },

    _renderAssignacio(t, nomProjecte) {
        return this.usuaris.map((u, i) => {
            const actiu = t.assignat === u;
            const inicials = this._inicialsUsuari(u);
            const color = this.COLORS_USUARIS[i % this.COLORS_USUARIS.length];
            const opacitat = actiu ? '1' : '0.3';
            const fotoUrl = this._fotosCache[u];
            if (fotoUrl) {
                return `<button class="avatar-btn" style="padding:0;background:transparent;opacity:${opacitat}"
                            onclick="App.assignarTasca('${this._esc(nomProjecte)}','${this._esc(t.nom)}','${actiu ? '' : this._esc(u)}')"
                            title="${this._esc(u)}">
                            <img src="${fotoUrl}" style="width:28px;height:28px;border-radius:50%;object-fit:cover">
                        </button>`;
            }
            return `<button class="avatar-btn" style="background:${color};opacity:${opacitat}"
                        onclick="App.assignarTasca('${this._esc(nomProjecte)}','${this._esc(t.nom)}','${actiu ? '' : this._esc(u)}')"
                        title="${this._esc(u)}">${inicials}</button>`;
        }).join('');
    },

    _renderBotonsEstat(t, nomProjecte) {
        // Boto "Enviar" rapid (visible nomes si Pendent + te assignat)
        let enviarHTML = '';
        if (t.estat === CONFIG.PENDENT && t.assignat) {
            enviarHTML = `<button class="btn-enviar-rapid"
                onclick="App.canviarEstat('${this._esc(nomProjecte)}','${this._esc(t.nom)}','enviat')">Enviar</button>`;
        }

        const botons = CONFIG.estats.map(estat => {
            const actiu = t.estat === estat;
            const etiqueta = CONFIG.etiquetes[estat];
            const color = actiu ? CONFIG.colorsActiuText[estat] : '#6B7280';
            const fons = actiu ? CONFIG.colorsActiuFons[estat] : '#E5E7EB';
            const classActiu = actiu ? ' actiu' : '';
            return `<button class="btn-estat${classActiu}" style="color:${color};background:${fons}"
                        onclick="App.canviarEstat('${this._esc(nomProjecte)}','${this._esc(t.nom)}','${estat}')"
                    >${etiqueta}</button>`;
        }).join('');

        return enviarHTML + botons;
    },

    _renderDocumentInline(t, nomProjecte) {
        // Pill verd inline a la fila 2 (identic al desktop)
        const nomFitxer = t.document.split('/').pop().split('\\').pop();
        return `<button class="btn-document" onclick="App.obrirDocument('${this._esc(t.document)}')" title="${this._esc(t.document)}">
                    &#128196; ${this._esc(nomFitxer)}
                </button>
                <button class="btn-eliminar-doc" onclick="App.eliminarDocument('${this._esc(nomProjecte)}','${this._esc(t.nom)}')" title="Desvincular">&times;</button>`;
    },

    async obrirDocument(rutaDocument) {
        try {
            // Normalitzar backslashes i codificar cada segment (NO les barres!)
            const ruta = rutaDocument.replace(/\\/g, '/');
            const encodedPath = ruta.split('/').map(s => encodeURIComponent(s)).join('/');
            const resp = await API.get(`/api/obrir-document/${encodedPath}`);
            if (resp && resp.url) {
                window.open(resp.url, '_blank');
            } else {
                alert('No s\'ha pogut obtenir el link del document.');
            }
        } catch (e) {
            console.error('Error obrint document:', e);
            alert('Error obrint el document. Comprova que existeix a OneDrive.');
        }
    },

    _renderObservacions(t, nomProjecte) {
        const obs = t.observacions || '';
        return `<div class="tasca-observacions">
            ${obs ? `<div class="obs-label">Observacions:</div><div class="obs-historial">${this._formatObs(obs)}</div>` : ''}
            <div class="obs-input-row">
                <input type="text" class="obs-input" placeholder="Afegir observacio..."
                       id="obs-${this._esc(t.nom)}"
                       onkeydown="if(event.key==='Enter')App.enviarObservacio('${this._esc(nomProjecte)}','${this._esc(t.nom)}')">
                <button class="btn-enviar-obs" onclick="App.enviarObservacio('${this._esc(nomProjecte)}','${this._esc(t.nom)}')">&#10148;</button>
            </div>
        </div>`;
    },

    _formatObs(text) {
        return text.split('\n').filter(l => l.trim()).map(l => {
            if (l.startsWith('@')) {
                return `<div class="obs-line obs-author">${this._esc(l)}</div>`;
            }
            return `<div class="obs-line">${this._esc(l)}</div>`;
        }).join('');
    },

    // --- BARRA INFERIOR (RESUM) — FORMAT IDENTIC AL DESKTOP ---

    _renderBarraInferior() {
        const container = document.getElementById('bottom-resum');
        const syncEl = document.getElementById('bottom-sync');
        if (!container) return;

        if (!this._resumUsuaris || !this._resumUsuaris.length) {
            container.innerHTML = '';
            if (syncEl) syncEl.textContent = '';
            return;
        }

        // Format desktop: "Nom: X env. / Y en curs / Z per rev. / W fetes"
        // Separador: "   |   "
        const parts = this._resumUsuaris.map(u => {
            return `<strong>${this._esc(u.nom)}</strong>: ${u.enviades} env. / ${u.en_curs} en curs / ${u.per_revisar} per rev. / ${u.fetes} fetes`;
        });

        container.innerHTML = `<span class="bottom-text">${parts.join('&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;')}</span>`;

        if (syncEl) {
            const ara = new Date();
            syncEl.textContent = `Sincronitzat: ${ara.toLocaleTimeString('ca-ES', {hour:'2-digit',minute:'2-digit',second:'2-digit'})}`;
        }
    },

    // --- PRIORITAT ---

    async togglePrioritat(nomProjecte, prioritari) {
        await API.patch(`/api/projectes/${encodeURIComponent(nomProjecte)}`, { prioritari });
        await this.carregarProjectes();
    },

    // --- ACCIONS ---

    async canviarEstat(nomProjecte, nomTasca, nouEstat) {
        if (nouEstat === CONFIG.PER_REVISAR) {
            this.mostrarDialogRevisor(nomProjecte, nomTasca);
            return;
        }
        if (nouEstat === CONFIG.COMPLETADA) {
            this.mostrarDialogDocument(nomProjecte, nomTasca, 'completada');
            return;
        }
        await API.patch(
            `/api/projectes/${encodeURIComponent(nomProjecte)}/tasques/${encodeURIComponent(nomTasca)}`,
            { estat: nouEstat }
        );
        await this._carregarDetall(nomProjecte);
        this.carregarProjectes();
    },

    async assignarTasca(nomProjecte, nomTasca, usuari) {
        await API.patch(
            `/api/projectes/${encodeURIComponent(nomProjecte)}/tasques/${encodeURIComponent(nomTasca)}`,
            { assignat: usuari }
        );
        await this._carregarDetall(nomProjecte);
        this.carregarProjectes();
    },

    async enviarObservacio(nomProjecte, nomTasca) {
        const input = document.getElementById(`obs-${nomTasca}`);
        if (!input) return;
        const text = input.value.trim();
        if (!text) return;

        const proj = await API.get(`/api/projectes/${encodeURIComponent(nomProjecte)}`);
        const tasca = proj.tasques.find(t => t.nom === nomTasca);
        const obsActual = tasca ? tasca.observacions : '';
        const novaObs = obsActual
            ? `${obsActual}\n@${CONFIG.usuariActual}:\n${text}`
            : `@${CONFIG.usuariActual}:\n${text}`;

        await API.patch(
            `/api/projectes/${encodeURIComponent(nomProjecte)}/tasques/${encodeURIComponent(nomTasca)}`,
            { observacions: novaObs }
        );
        input.value = '';
        await this._carregarDetall(nomProjecte);
    },

    async eliminarDocument(nomProjecte, nomTasca) {
        await API.patch(
            `/api/projectes/${encodeURIComponent(nomProjecte)}/tasques/${encodeURIComponent(nomTasca)}`,
            { document: '' }
        );
        await this._carregarDetall(nomProjecte);
    },

    // --- DIALOGS ---

    mostrarDialog(html) {
        const dialog = document.getElementById('dialog');
        const overlay = document.getElementById('overlay');
        dialog.innerHTML = html;
        dialog.classList.remove('hidden');
        overlay.classList.remove('hidden');
    },

    tancarDialog() {
        document.getElementById('dialog').classList.add('hidden');
        document.getElementById('overlay').classList.add('hidden');
    },

    async mostrarDialogAfegirProjecte() {
        const carpetes = await API.get('/api/carpetes-onedrive');
        if (!carpetes) return;

        const disponibles = carpetes.filter(c => !c.ja_afegit);
        if (!disponibles.length) {
            this.mostrarDialog(`
                <div class="dialog-header"><h3>Afegir projecte</h3></div>
                <div class="dialog-body"><p>No hi ha carpetes de projecte noves a OneDrive.</p></div>
                <div class="dialog-footer"><button class="btn" onclick="App.tancarDialog()">Tancar</button></div>
            `);
            return;
        }

        const llista = disponibles.map(c =>
            `<button class="carpeta-item" onclick="App._afegirProjecte('${this._esc(c.nom)}')">${this._esc(c.nom)}</button>`
        ).join('');

        this.mostrarDialog(`
            <div class="dialog-header"><h3>Afegir projecte</h3></div>
            <div class="dialog-body dialog-scroll">${llista}</div>
            <div class="dialog-footer"><button class="btn" onclick="App.tancarDialog()">Cancel&middot;lar</button></div>
        `);
    },

    async _afegirProjecte(nom) {
        await API.post('/api/projectes', { nom_carpeta: nom });
        this.tancarDialog();
        await this.carregarProjectes();
        this.seleccionarProjecte(nom);
    },

    async mostrarDialogAfegirTasques() {
        if (!this.projecteActual) return;
        const plantilles = await API.get('/api/plantilles');
        if (!plantilles) return;

        let html = '<div class="dialog-header"><h3>Afegir tasques</h3></div><div class="dialog-body dialog-scroll">';

        html += '<div class="assignar-row"><span>Assignar a:</span>';
        html += this.usuaris.map((u, i) => {
            const inicials = this._inicialsUsuari(u);
            return `<button class="avatar-btn avatar-selectable" data-usuari="${this._esc(u)}"
                        style="background:${this.COLORS_USUARIS[i % this.COLORS_USUARIS.length]}"
                        onclick="App._toggleAssignar(this)">${inicials}</button>`;
        }).join('');
        html += '<span id="assignar-nom" class="assignar-nom">Sense assignar</span></div>';

        for (const [cat, docs] of Object.entries(plantilles)) {
            html += `<div class="cat-header">${this._esc(cat)}</div>`;
            docs.forEach(doc => {
                const id = `cb-${doc.replace(/\s/g, '_')}`;
                html += `<label class="checkbox-item"><input type="checkbox" id="${id}" value="${this._esc(doc)}"> ${this._esc(doc)}</label>`;
            });
        }

        html += `<div class="cat-header">Personalitzada</div>
                 <input type="text" id="tasca-custom" class="input-full" placeholder="Nom de la tasca...">`;

        html += '</div>';
        html += `<div class="dialog-footer">
            <button class="btn" onclick="App.tancarDialog()">Cancel&middot;lar</button>
            <button class="btn btn-primary" onclick="App._confirmarAfegirTasques()">Afegir</button>
        </div>`;

        this.mostrarDialog(html);
    },

    _selectedAssignar: '',

    _toggleAssignar(btn) {
        const nom = btn.dataset.usuari;
        document.querySelectorAll('.avatar-selectable').forEach(b => b.classList.remove('selected'));
        if (this._selectedAssignar === nom) {
            this._selectedAssignar = '';
            document.getElementById('assignar-nom').textContent = 'Sense assignar';
        } else {
            this._selectedAssignar = nom;
            btn.classList.add('selected');
            document.getElementById('assignar-nom').textContent = nom;
        }
    },

    async _confirmarAfegirTasques() {
        const checkboxes = document.querySelectorAll('#dialog .checkbox-item input:checked');
        const noms = Array.from(checkboxes).map(cb => cb.value);
        const custom = document.getElementById('tasca-custom')?.value.trim();
        if (custom) noms.push(custom);
        if (!noms.length) return;

        await API.post(`/api/projectes/${encodeURIComponent(this.projecteActual)}/tasques`, {
            noms: noms,
            assignat: this._selectedAssignar,
        });
        this._selectedAssignar = '';
        this.tancarDialog();
        await this._carregarDetall(this.projecteActual);
        this.carregarProjectes();
    },

    mostrarDialogRevisor(nomProjecte, nomTasca) {
        const avatars = this.usuaris.map((u, i) => {
            const inicials = this._inicialsUsuari(u);
            const fotoUrl = this._fotosCache[u];
            const color = this.COLORS_USUARIS[i % this.COLORS_USUARIS.length];
            let contingut;
            if (fotoUrl) {
                contingut = `<img src="${fotoUrl}" style="width:56px;height:56px;border-radius:50%;object-fit:cover">
                    <span class="avatar-nom">${this._esc(u)}</span>`;
            } else {
                contingut = `<span class="avatar-inicials">${inicials}</span>
                    <span class="avatar-nom">${this._esc(u)}</span>`;
            }
            return `<button class="avatar-btn-gran" style="background:${fotoUrl ? 'transparent' : color}"
                        onclick="App._seleccionarRevisor('${this._esc(nomProjecte)}','${this._esc(nomTasca)}','${this._esc(u)}')">
                        ${contingut}
                    </button>`;
        }).join('');

        this.mostrarDialog(`
            <div class="dialog-header"><h3>Qui ha de revisar?</h3></div>
            <div class="dialog-body"><div class="revisor-grid">${avatars}</div></div>
            <div class="dialog-footer"><button class="btn" onclick="App.tancarDialog()">Cancel&middot;lar</button></div>
        `);
    },

    async _seleccionarRevisor(nomProjecte, nomTasca, revisor) {
        this.tancarDialog();
        this.mostrarDialogDocument(nomProjecte, nomTasca, 'per_revisar', revisor);
    },

    _currentDocCallback: null,

    mostrarDialogDocument(nomProjecte, nomTasca, accio, revisor = '') {
        this._currentDocCallback = { nomProjecte, nomTasca, accio, revisor };
        this._navegarFitxers(nomProjecte, '');
    },

    async _navegarFitxers(nomProjecte, subcarpeta) {
        const fitxers = await API.get(
            `/api/fitxers/${encodeURIComponent(nomProjecte)}` +
            (subcarpeta ? `?subcarpeta=${encodeURIComponent(subcarpeta)}` : '')
        );
        if (!fitxers) return;

        let html = '<div class="dialog-header"><h3>Selecciona un document</h3>';
        if (subcarpeta) {
            const parts = subcarpeta.split('/');
            parts.pop();
            const parentPath = parts.join('/');
            html += `<button class="btn btn-small" onclick="App._navegarFitxers('${this._esc(nomProjecte)}','${this._esc(parentPath)}')">&larr; Enrere</button>`;
        }
        html += '</div><div class="dialog-body dialog-scroll">';

        if (!fitxers.length) {
            html += '<div class="empty-state">Carpeta buida</div>';
        }

        fitxers.forEach(f => {
            const fullPath = subcarpeta ? `${subcarpeta}/${f.nom}` : f.nom;
            if (f.es_carpeta) {
                html += `<button class="fitxer-item fitxer-carpeta" onclick="App._navegarFitxers('${this._esc(nomProjecte)}','${this._esc(fullPath)}')">
                    &#128193; ${this._esc(f.nom)}
                </button>`;
            } else {
                html += `<button class="fitxer-item fitxer-document" onclick="App._seleccionarFitxer('${this._esc(fullPath)}')">
                    &#128196; ${this._esc(f.nom)}
                </button>`;
            }
        });

        html += '</div><div class="dialog-footer">';
        html += `<button class="btn" onclick="App._saltarDocument()">Sense document</button>`;
        html += '</div>';

        this.mostrarDialog(html);
    },

    async _seleccionarFitxer(rutaRelativa) {
        const cb = this._currentDocCallback;
        if (!cb) return;
        this.tancarDialog();

        const docPath = `${cb.nomProjecte}/${rutaRelativa}`;
        const data = { document: docPath };

        if (cb.accio === 'per_revisar') {
            data.estat = CONFIG.PER_REVISAR;
            if (cb.revisor) data.revisor = cb.revisor;
        } else if (cb.accio === 'completada') {
            data.estat = CONFIG.COMPLETADA;
        }

        await API.patch(
            `/api/projectes/${encodeURIComponent(cb.nomProjecte)}/tasques/${encodeURIComponent(cb.nomTasca)}`,
            data
        );
        this._currentDocCallback = null;
        await this._carregarDetall(cb.nomProjecte);
        this.carregarProjectes();
    },

    async _saltarDocument() {
        const cb = this._currentDocCallback;
        if (!cb) return;
        this.tancarDialog();

        const data = {};
        if (cb.accio === 'per_revisar') {
            data.estat = CONFIG.PER_REVISAR;
            if (cb.revisor) data.revisor = cb.revisor;
        } else if (cb.accio === 'completada') {
            data.estat = CONFIG.COMPLETADA;
        }

        await API.patch(
            `/api/projectes/${encodeURIComponent(cb.nomProjecte)}/tasques/${encodeURIComponent(cb.nomTasca)}`,
            data
        );
        this._currentDocCallback = null;
        await this._carregarDetall(cb.nomProjecte);
        this.carregarProjectes();
    },

    confirmarEliminarTasca(nomProjecte, nomTasca) {
        this.mostrarDialog(`
            <div class="dialog-header"><h3>Eliminar tasca</h3></div>
            <div class="dialog-body"><p>Segur que vols eliminar "${this._esc(nomTasca)}"?</p></div>
            <div class="dialog-footer">
                <button class="btn" onclick="App.tancarDialog()">Cancel&middot;lar</button>
                <button class="btn btn-danger" onclick="App._eliminarTasca('${this._esc(nomProjecte)}','${this._esc(nomTasca)}')">Eliminar</button>
            </div>
        `);
    },

    async _eliminarTasca(nomProjecte, nomTasca) {
        await API.del(`/api/projectes/${encodeURIComponent(nomProjecte)}/tasques/${encodeURIComponent(nomTasca)}`);
        this.tancarDialog();
        await this._carregarDetall(nomProjecte);
        this.carregarProjectes();
    },

    confirmarEliminarProjecte(nom) {
        this.mostrarDialog(`
            <div class="dialog-header"><h3>Eliminar projecte</h3></div>
            <div class="dialog-body"><p>Segur que vols eliminar "${this._esc(nom)}"?</p></div>
            <div class="dialog-footer">
                <button class="btn" onclick="App.tancarDialog()">Cancel&middot;lar</button>
                <button class="btn btn-danger" onclick="App._eliminarProjecte('${this._esc(nom)}')">Eliminar</button>
            </div>
        `);
    },

    async _eliminarProjecte(nom) {
        await API.del(`/api/projectes/${encodeURIComponent(nom)}`);
        this.tancarDialog();
        if (this.projecteActual === nom) {
            this.projecteActual = null;
            document.getElementById('detall-header').classList.add('hidden');
            document.getElementById('tasques-llista').innerHTML = '<div class="empty-state">Selecciona un projecte.</div>';
        }
        await this.carregarProjectes();
    },

    // --- FILTRE I CERCA ---

    _renderFilterAvatars(usuaris) {
        const container = document.getElementById('filter-avatars');

        let html = `<button class="filter-btn ${!this.filtrePersona ? 'active' : ''}" onclick="App.filtrar('')">Tots</button>`;
        usuaris.forEach((u, i) => {
            const inicials = this._inicialsUsuari(u);
            const actiu = this.filtrePersona === u ? 'active' : '';
            const fotoUrl = this._fotosCache[u];
            if (fotoUrl) {
                html += `<button class="avatar-btn filter-avatar ${actiu}" style="padding:0;background:transparent"
                            onclick="App.filtrar('${this._esc(u)}')" title="${this._esc(u)}">
                            <img src="${fotoUrl}" style="width:28px;height:28px;border-radius:50%;object-fit:cover">
                        </button>`;
            } else {
                html += `<button class="avatar-btn filter-avatar ${actiu}" style="background:${this.COLORS_USUARIS[i % this.COLORS_USUARIS.length]}"
                            onclick="App.filtrar('${this._esc(u)}')" title="${this._esc(u)}">${inicials}</button>`;
            }
        });
        container.innerHTML = html;
    },

    async filtrar(persona) {
        this.filtrePersona = persona;
        if (this.projecteActual) {
            await this._carregarDetall(this.projecteActual);
        }
        await this.carregarProjectes();
    },

    _onCerca(text) {
        clearTimeout(this._cercaTimer);
        this._cercaTimer = setTimeout(() => {
            this.cercaText = text;
            this.carregarProjectes();
        }, 300);
    },

    // --- NOTIFICACIONS ---

    async _carregarNotificacions() {
        const notifs = await API.get('/api/notificacions');
        if (!notifs) return;

        const btn = document.getElementById('btn-notif');
        btn.dataset.count = notifs.length;
        btn.classList.toggle('has-notifs', notifs.length > 0);
    },

    async toggleNotificacions() {
        const popup = document.getElementById('notif-popup');
        if (!popup.classList.contains('hidden')) {
            popup.classList.add('hidden');
            return;
        }

        const notifs = await API.get('/api/notificacions');
        if (!notifs || !notifs.length) {
            popup.innerHTML = '<div class="notif-empty">Cap notificacio nova</div>';
        } else {
            let html = `<div class="notif-header">
                <span>Notificacions (${notifs.length})</span>
                <button class="btn btn-small" onclick="App._marcarTotesLlegides()">Llegir totes</button>
            </div>`;
            notifs.forEach(n => {
                const accioText = CONFIG.etiquetes[n.accio] || n.accio;
                html += `<div class="notif-item">
                    <div class="notif-text"><strong>${this._esc(n.de)}</strong> ha marcat <em>${this._esc(n.tasca)}</em> com a ${accioText}</div>
                    <div class="notif-meta">${this._esc(n.projecte)}</div>
                    <button class="btn-icon" onclick="App._marcarLlegida('${n.id}',this.closest('.notif-item'))">&#10003;</button>
                </div>`;
            });
            popup.innerHTML = html;
        }
        popup.classList.remove('hidden');
    },

    async _marcarLlegida(id, element) {
        await API.post(`/api/notificacions/${id}/llegida`);
        if (element) element.remove();
        this._carregarNotificacions();
    },

    async _marcarTotesLlegides() {
        await API.post('/api/notificacions/totes-llegides');
        document.getElementById('notif-popup').classList.add('hidden');
        this._carregarNotificacions();
    },

    // --- RESPONSIVE: TORNAR ---

    tornarALlista() {
        document.getElementById('panel-detall').classList.remove('active');
    },

    // --- POLLING ---

    _iniciarPolling() {
        this._pollTimer = setInterval(async () => {
            try {
                const resp = await API.get('/api/ha-canviat');
                if (resp && resp.canviat) {
                    await this.carregarProjectes();
                    if (this.projecteActual) {
                        await this._carregarDetall(this.projecteActual);
                    }
                    this._carregarNotificacions();
                }
            } catch (e) { /* ignora errors de polling */ }
        }, 15000);
    },

    // --- UTILS ---

    _esc(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    },
};

// Iniciar quan el DOM estigui llest
document.addEventListener('DOMContentLoaded', () => App.init());
