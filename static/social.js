// ==========================================================================
// MÓDULO SOCIAL (social.js) — amigos, mensajería, grupos y clasificación
// --------------------------------------------------------------------------
// Se carga DESPUÉS de app.js y auth.js. Comparte con ellos, vía el ámbito
// global de scripts clásicos, estas referencias: socket, t(), t_dinamico(),
// miUsernameLogueado, cerrarModales(), modalOverlay.
//
// Toda la lógica es aditiva y está pensada para usuarios registrados. Los
// invitados nunca ven el botón (vive dentro de #user-info-logged).
// ==========================================================================

(function () {
    'use strict';

    // ----- Estado -----
    let tabActual = 'amigos';       // 'amigos' | 'grupos'
    let chatTipo = null;            // 'dm' | 'grupo' | null
    let chatIdActual = null;        // friend_id (DM) o group_id (grupo)
    let chatNombreActual = '';
    let unreadDM = 0;
    let numSolicitudes = 0;
    let unreadGrupos = 0;

    const $ = (id) => document.getElementById(id);

    // Escape imprescindible: los mensajes son el único texto de usuario que
    // renderizamos. NUNCA usar innerHTML con texto sin escapar (XSS).
    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function _t(k) { return (typeof t === 'function') ? t(k) : k; }
    function _td(k, v) { return (typeof t_dinamico === 'function') ? t_dinamico(k, v) : k; }

    // Traduce un código de error del servidor a un mensaje localizado.
    function msgError(codigo) {
        const map = {
            self: 'err_self', no_existe: 'err_no_existe', already_friends: 'err_ya_amigos',
            already_pending: 'err_already_pending', blocked: 'err_blocked', limite: 'err_limite',
            rate_limit: 'err_rate_limit', offline: 'err_offline', no_amigo: 'err_no_amigo',
            nombre: 'err_nombre_grupo', ya_miembro: 'err_ya_miembro', permiso: 'err_generico',
            invalido: 'err_generico'
        };
        return _t(map[codigo] || 'err_generico');
    }

    // ----- Toast flotante -----
    let toastTimer = null;
    function mostrarToast(texto) {
        const el = $('social-toast');
        if (!el) return;
        el.textContent = texto;
        el.classList.remove('hidden');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => el.classList.add('hidden'), 4000);
    }

    // ======================================================================
    // Insignia (badge) de no leídos
    // ======================================================================
    function pintarBadge() {
        const badge = $('amigos-badge');
        if (!badge) return;
        const total = unreadDM + numSolicitudes + unreadGrupos;
        if (total > 0) {
            badge.textContent = total > 99 ? '99+' : total;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }

    async function refrescarBadge() {
        try {
            const r = await fetch('/api/friends');
            if (r.status === 401) return;              // invitado: no hay social
            const d = await r.json();
            if (d.exito) {
                unreadDM = d.total_no_leidos || 0;
                numSolicitudes = (d.solicitudes || []).length;
            }
            const rg = await fetch('/api/groups');
            const dg = await rg.json();
            if (dg.exito) {
                unreadGrupos = (dg.grupos || []).reduce((s, g) => s + (g.no_leidos || 0), 0);
            }
            pintarBadge();
        } catch (e) { /* silencioso */ }
    }

    // ======================================================================
    // Apertura del panel + pestañas
    // ======================================================================
    function abrirSocial() {
        modalOverlay.style.display = 'flex';
        modalOverlay.classList.remove('hidden');
        ['modal-login', 'modal-signup', 'modal-leaderboard', 'modal-privacy',
         'modal-verify', 'modal-forgot', 'modal-reset', 'modal-play'].forEach(id => {
            const el = $(id); if (el) el.classList.add('hidden');
        });
        $('modal-social').classList.remove('hidden');
        chatTipo = null; chatIdActual = null;
        setTab(tabActual);
    }

    function setTab(tab) {
        tabActual = tab;
        chatTipo = null; chatIdActual = null;
        const bA = $('tab-amigos'), bG = $('tab-grupos');
        const activo = { background: '#5e81ac', color: '#eceff4' };
        const inactivo = { background: '#3b4252', color: '#d8dee9' };
        Object.assign(bA.style, tab === 'amigos' ? activo : inactivo);
        Object.assign(bG.style, tab === 'grupos' ? activo : inactivo);
        if (tab === 'amigos') cargarAmigos(); else cargarGrupos();
    }

    // ======================================================================
    // AMIGOS
    // ======================================================================
    async function cargarAmigos() {
        const body = $('social-body');
        body.innerHTML = `<p style="opacity:.7; text-align:center;">${esc(_t('cargando_social'))}</p>`;
        try {
            const r = await fetch('/api/friends');
            const d = await r.json();
            if (!d.exito) { body.innerHTML = ''; return; }
            unreadDM = d.total_no_leidos || 0;
            numSolicitudes = (d.solicitudes || []).length;
            pintarBadge();
            renderAmigos(d.amigos || [], d.solicitudes || []);
        } catch (e) {
            body.innerHTML = `<p style="color:#bf616a; text-align:center;">${esc(_t('err_generico'))}</p>`;
        }
    }

    function renderAmigos(amigos, solicitudes) {
        const body = $('social-body');
        let html = '';

        // Añadir amigo
        html += `<div style="display:flex; gap:6px; margin-bottom:14px;">
            <input id="in-add-friend" placeholder="${esc(_t('add_friend_ph'))}"
                style="flex:1; padding:8px; background:#3b4252; color:#fff; border:1px solid #4c566a; border-radius:4px;">
            <button id="btn-add-friend" style="background:#a3be8c; color:#2e3440; border:none; padding:8px 14px; border-radius:4px; font-weight:bold; cursor:pointer;">${esc(_t('btn_add_friend'))}</button>
        </div>`;

        // Solicitudes entrantes
        if (solicitudes.length) {
            html += `<h3 style="color:#ebcb8b; font-size:1em; margin:8px 0;">${esc(_t('friend_requests'))} (${solicitudes.length})</h3>`;
            solicitudes.forEach(s => {
                html += `<div style="display:flex; align-items:center; justify-content:space-between; background:#3b4252; padding:8px 10px; border-radius:6px; margin-bottom:6px;">
                    <span style="font-weight:bold; color:#eceff4;">${esc(s.username)}</span>
                    <span>
                        <button class="btn-req-ok" data-id="${s.id}" style="background:#a3be8c; color:#2e3440; border:none; padding:5px 10px; border-radius:4px; font-weight:bold; cursor:pointer; margin-right:5px;">${esc(_t('btn_aceptar'))}</button>
                        <button class="btn-req-no" data-id="${s.id}" style="background:#bf616a; color:#fff; border:none; padding:5px 10px; border-radius:4px; font-weight:bold; cursor:pointer;">${esc(_t('btn_rechazar'))}</button>
                    </span>
                </div>`;
            });
            html += `<hr style="border:none; border-top:1px solid #4c566a; margin:12px 0;">`;
        }

        // Lista de amigos
        if (!amigos.length) {
            html += `<p style="opacity:.7; text-align:center; margin-top:20px;">${esc(_t('sin_amigos'))}</p>`;
        } else {
            amigos.forEach(a => {
                const dot = a.online ? '#a3be8c' : '#4c566a';
                const estado = a.online ? _t('estado_online') : _t('estado_offline');
                const badge = a.no_leidos ? `<span style="background:#bf616a; color:#fff; border-radius:50%; padding:0 6px; font-size:.75em; margin-left:6px;">${a.no_leidos}</span>` : '';
                html += `<div style="display:flex; align-items:center; justify-content:space-between; background:#3b4252; padding:8px 10px; border-radius:6px; margin-bottom:6px;">
                    <div style="display:flex; align-items:center; gap:8px; min-width:0;">
                        <span title="${esc(estado)}" style="width:10px; height:10px; border-radius:50%; background:${dot}; flex:none;"></span>
                        <span style="font-weight:bold; color:#ebcb8b; overflow:hidden; text-overflow:ellipsis;">${esc(a.username)}</span>
                        <span style="opacity:.6; font-size:.85em;">${a.elo}</span>${badge}
                    </div>
                    <div style="flex:none;">
                        <button class="btn-fr-chat" data-id="${a.id}" data-name="${esc(a.username)}" style="background:#5e81ac; color:#fff; border:none; padding:5px 8px; border-radius:4px; cursor:pointer; margin-right:4px;" title="${esc(_t('btn_chat'))}">💬</button>
                        <button class="btn-fr-invite" data-id="${a.id}" data-name="${esc(a.username)}" style="background:#b48ead; color:#fff; border:none; padding:5px 8px; border-radius:4px; cursor:pointer; margin-right:4px;" title="${esc(_t('btn_invitar_juego'))}">🎮</button>
                        <button class="btn-fr-del" data-id="${a.id}" data-name="${esc(a.username)}" style="background:transparent; color:#bf616a; border:1px solid #bf616a; padding:5px 8px; border-radius:4px; cursor:pointer;" title="${esc(_t('btn_eliminar_amigo'))}">✕</button>
                    </div>
                </div>`;
            });
        }

        body.innerHTML = html;

        // Listeners
        const addBtn = $('btn-add-friend'), addIn = $('in-add-friend');
        if (addBtn) addBtn.onclick = () => enviarSolicitud(addIn.value.trim());
        if (addIn) addIn.onkeydown = (e) => { if (e.key === 'Enter') enviarSolicitud(addIn.value.trim()); };

        body.querySelectorAll('.btn-req-ok').forEach(b => b.onclick = () => responder(+b.dataset.id, true));
        body.querySelectorAll('.btn-req-no').forEach(b => b.onclick = () => responder(+b.dataset.id, false));
        body.querySelectorAll('.btn-fr-chat').forEach(b => b.onclick = () => abrirChatDM(+b.dataset.id, b.dataset.name));
        body.querySelectorAll('.btn-fr-invite').forEach(b => b.onclick = () => invitarPartida(+b.dataset.id, b.dataset.name));
        body.querySelectorAll('.btn-fr-del').forEach(b => b.onclick = () => eliminarAmigo(+b.dataset.id, b.dataset.name));
    }

    async function enviarSolicitud(username) {
        if (!username) return;
        const r = await fetch('/api/friends/request', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        const d = await r.json();
        mostrarToast(d.exito ? _t('solicitud_enviada') : msgError(d.mensaje));
        if (d.exito) cargarAmigos();
    }

    async function responder(userId, accept) {
        const r = await fetch('/api/friends/respond', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, accept })
        });
        const d = await r.json();
        if (d.exito) cargarAmigos();
    }

    async function eliminarAmigo(userId, nombre) {
        if (!confirm(_td('confirm_eliminar_amigo', { nombre }))) return;
        await fetch('/api/friends/' + userId, { method: 'DELETE' });
        cargarAmigos();
    }

    function invitarPartida(friendId, nombre) {
        const mejorDe = parseInt(($('in-mejor-de') || {}).value, 10) || 3;
        socket.emit('invitar_amigo', { friend_id: friendId, al_mejor_de: mejorDe });
        cerrarModales();
        const menuMsg = $('menu-msg');
        if (menuMsg) { menuMsg.style.color = '#a3be8c'; menuMsg.innerText = _td('invitacion_de', { nombre, n: mejorDe }); }
    }

    // ======================================================================
    // CHAT (DM y grupo comparten el mismo componente)
    // ======================================================================
    function renderChatShell(titulo) {
        const body = $('social-body');
        body.innerHTML = `
        <div style="display:flex; flex-direction:column; height:100%;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                <button id="chat-back" style="background:#4c566a; color:#fff; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">${esc(_t('btn_volver'))}</button>
                <strong style="color:#88c0d0; overflow:hidden; text-overflow:ellipsis;">${esc(titulo)}</strong>
            </div>
            <div id="chat-mensajes" style="flex:1; overflow-y:auto; background:#262b36; border:1px solid #3b4252; border-radius:6px; padding:10px; min-height:0;"></div>
            <div style="display:flex; gap:6px; margin-top:8px;">
                <input id="chat-input" maxlength="500" placeholder="${esc(_t('chat_ph'))}" style="flex:1; padding:8px; background:#3b4252; color:#fff; border:1px solid #4c566a; border-radius:4px;">
                <button id="chat-send" style="background:#a3be8c; color:#2e3440; border:none; padding:8px 14px; border-radius:4px; font-weight:bold; cursor:pointer;">${esc(_t('btn_enviar'))}</button>
            </div>
        </div>`;
        $('chat-back').onclick = () => setTab(tabActual);
        const input = $('chat-input');
        input.onkeydown = (e) => { if (e.key === 'Enter') $('chat-send').click(); };
        setTimeout(() => input.focus(), 50);
    }

    function burbuja(texto, esMio, autor) {
        const div = document.createElement('div');
        div.style.cssText = `max-width:78%; margin:4px 0; padding:7px 10px; border-radius:10px; word-wrap:break-word; ${esMio ? 'margin-left:auto; background:#5e81ac; color:#fff;' : 'background:#3b4252; color:#eceff4;'}`;
        if (autor && !esMio) {
            const a = document.createElement('div');
            a.style.cssText = 'font-size:.75em; font-weight:bold; color:#ebcb8b; margin-bottom:2px;';
            a.textContent = autor;
            div.appendChild(a);
        }
        const t = document.createElement('div');
        t.textContent = texto;          // textContent → sin XSS
        div.appendChild(t);
        return div;
    }

    function pintarMensajes(mensajes, esGrupo) {
        const cont = $('chat-mensajes');
        if (!cont) return;
        cont.innerHTML = '';
        if (!mensajes.length) {
            cont.innerHTML = `<p style="opacity:.6; text-align:center; margin-top:20px;">${esc(_t('sin_mensajes'))}</p>`;
            return;
        }
        mensajes.forEach(m => {
            const esMio = esGrupo ? (m.sender_name === miUsernameLogueado) : (m.sender_id !== chatIdActual);
            cont.appendChild(burbuja(m.body, esMio, esGrupo ? m.sender_name : null));
        });
        cont.scrollTop = cont.scrollHeight;
    }

    function appendMensaje(m, esMio, esGrupo) {
        const cont = $('chat-mensajes');
        if (!cont) return;
        const vacio = cont.querySelector('p');
        if (vacio) cont.innerHTML = '';
        cont.appendChild(burbuja(m.body, esMio, esGrupo ? m.sender_name : null));
        cont.scrollTop = cont.scrollHeight;
    }

    // ----- DM -----
    async function abrirChatDM(friendId, nombre) {
        chatTipo = 'dm'; chatIdActual = friendId; chatNombreActual = nombre;
        renderChatShell(nombre);
        $('chat-send').onclick = enviarDM;
        const r = await fetch('/api/messages/' + friendId);
        const d = await r.json();
        if (d.exito) pintarMensajes(d.mensajes || [], false);
        // al abrir, se marcaron leídos en el servidor → refrescamos badge
        refrescarBadge();
    }

    async function enviarDM() {
        const input = $('chat-input');
        const body = input.value.trim();
        if (!body) return;
        input.value = '';
        const r = await fetch('/api/messages/' + chatIdActual, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ body })
        });
        const d = await r.json();
        if (d.exito) appendMensaje(d.mensaje, true, false);
        else mostrarToast(msgError(d.mensaje));
    }

    // ----- Grupo -----
    async function abrirChatGrupo(groupId, nombre) {
        chatTipo = 'grupo'; chatIdActual = groupId; chatNombreActual = nombre;
        renderChatShell(nombre);
        $('chat-send').onclick = enviarGrupoMsg;
        const r = await fetch('/api/groups/' + groupId + '/messages');
        const d = await r.json();
        if (d.exito) pintarMensajes(d.mensajes || [], true);
        refrescarBadge();
    }

    async function enviarGrupoMsg() {
        const input = $('chat-input');
        const body = input.value.trim();
        if (!body) return;
        input.value = '';
        const r = await fetch('/api/groups/' + chatIdActual + '/messages', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ body })
        });
        const d = await r.json();
        if (d.exito) appendMensaje(d.mensaje, true, true);
        else mostrarToast(msgError(d.mensaje));
    }

    // ======================================================================
    // GRUPOS
    // ======================================================================
    async function cargarGrupos() {
        const body = $('social-body');
        body.innerHTML = `<p style="opacity:.7; text-align:center;">${esc(_t('cargando_social'))}</p>`;
        try {
            const r = await fetch('/api/groups');
            const d = await r.json();
            if (!d.exito) { body.innerHTML = ''; return; }
            unreadGrupos = (d.grupos || []).reduce((s, g) => s + (g.no_leidos || 0), 0);
            pintarBadge();
            renderGrupos(d.grupos || []);
        } catch (e) {
            body.innerHTML = `<p style="color:#bf616a; text-align:center;">${esc(_t('err_generico'))}</p>`;
        }
    }

    function renderGrupos(grupos) {
        const body = $('social-body');
        let html = `<div style="display:flex; gap:6px; margin-bottom:14px;">
            <input id="in-crear-grupo" maxlength="40" placeholder="${esc(_t('crear_grupo_ph'))}"
                style="flex:1; padding:8px; background:#3b4252; color:#fff; border:1px solid #4c566a; border-radius:4px;">
            <button id="btn-crear-grupo" style="background:#a3be8c; color:#2e3440; border:none; padding:8px 14px; border-radius:4px; font-weight:bold; cursor:pointer;">${esc(_t('btn_crear_grupo'))}</button>
        </div>`;

        if (!grupos.length) {
            html += `<p style="opacity:.7; text-align:center; margin-top:20px;">${esc(_t('sin_grupos'))}</p>`;
        } else {
            grupos.forEach(g => {
                const badge = g.no_leidos ? `<span style="background:#bf616a; color:#fff; border-radius:50%; padding:0 6px; font-size:.75em; margin-left:6px;">${g.no_leidos}</span>` : '';
                html += `<div class="grupo-row" data-id="${g.id}" data-name="${esc(g.name)}" style="display:flex; align-items:center; justify-content:space-between; background:#3b4252; padding:10px; border-radius:6px; margin-bottom:6px; cursor:pointer;">
                    <span style="font-weight:bold; color:#ebcb8b;">${esc(g.name)}${badge}</span>
                    <span style="opacity:.6; font-size:.85em;">${g.miembros} 👤</span>
                </div>`;
            });
        }
        body.innerHTML = html;

        const cIn = $('in-crear-grupo'), cBtn = $('btn-crear-grupo');
        cBtn.onclick = () => crearGrupo(cIn.value.trim());
        cIn.onkeydown = (e) => { if (e.key === 'Enter') crearGrupo(cIn.value.trim()); };
        body.querySelectorAll('.grupo-row').forEach(row =>
            row.onclick = () => abrirGrupo(+row.dataset.id, row.dataset.name));
    }

    async function crearGrupo(name) {
        if (!name) return;
        const r = await fetch('/api/groups', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const d = await r.json();
        mostrarToast(d.exito ? _t('grupo_creado') : msgError(d.mensaje));
        if (d.exito) cargarGrupos();
    }

    // Estado del grupo abierto, para poder alternar vistas sin re-pedir al servidor.
    let grupoActual = null;     // {id, name, invite_policy, owner_id, miembros, miRol}
    let lbVisible = false;

    async function abrirGrupo(groupId) {
        const body = $('social-body');
        body.innerHTML = `<p style="opacity:.7; text-align:center;">${esc(_t('cargando_social'))}</p>`;
        const r = await fetch('/api/groups/' + groupId);
        const d = await r.json();
        if (!d.exito) { cargarGrupos(); return; }
        grupoActual = {
            id: d.grupo.id, name: d.grupo.name, owner_id: d.grupo.owner_id,
            invite_policy: d.grupo.invite_policy || 'admins',
            miembros: d.miembros || [], miRol: d.mi_rol
        };
        lbVisible = false;
        renderGrupoDetalle();
    }

    function renderGrupoDetalle() {
        const g = grupoActual;
        const body = $('social-body');
        const puedeAdmin = (g.miRol === 'owner' || g.miRol === 'admin');
        const puedeInvitar = puedeAdmin || g.invite_policy === 'all';

        let html = `<div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
            <button id="grupo-back" style="background:#4c566a; color:#fff; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">${esc(_t('btn_volver'))}</button>
            <strong style="color:#88c0d0; font-size:1.1em;">${esc(g.name)}</strong>
        </div>`;

        html += `<div style="display:flex; gap:6px; margin-bottom:12px;">
            <button id="grupo-chat" style="flex:1; background:#5e81ac; color:#fff; border:none; padding:8px; border-radius:4px; font-weight:bold; cursor:pointer;">${esc(_t('group_chat'))}</button>
            <button id="grupo-lb" style="flex:1; border:none; padding:8px; border-radius:4px; font-weight:bold; cursor:pointer; ${lbVisible ? 'background:#d08770; color:#2e3440;' : 'background:#ebcb8b; color:#2e3440;'}">${esc(_t('group_leaderboard'))}</button>
        </div>`;

        if (puedeInvitar) {
            html += `<div style="display:flex; gap:6px; margin-bottom:12px;">
                <input id="in-invitar-grupo" placeholder="${esc(_t('group_invite_ph'))}"
                    style="flex:1; padding:7px; background:#3b4252; color:#fff; border:1px solid #4c566a; border-radius:4px;">
                <button id="btn-invitar-grupo" style="background:#a3be8c; color:#2e3440; border:none; padding:7px 12px; border-radius:4px; font-weight:bold; cursor:pointer;">${esc(_t('btn_group_invite'))}</button>
            </div>`;
        }

        // Menú de permisos (solo admins/owner): quién puede añadir miembros.
        if (puedeAdmin) {
            html += `<div style="display:flex; align-items:center; gap:8px; margin-bottom:12px; background:#2b313c; border:1px solid #3b4252; border-radius:6px; padding:8px 10px;">
                <label for="sel-invite-policy" style="font-size:.85em; opacity:.85;">${esc(_t('who_can_add'))}</label>
                <select id="sel-invite-policy" style="flex:1; padding:5px; background:#3b4252; color:#fff; border:1px solid #4c566a; border-radius:4px;">
                    <option value="admins" ${g.invite_policy === 'admins' ? 'selected' : ''}>${esc(_t('policy_admins'))}</option>
                    <option value="all" ${g.invite_policy === 'all' ? 'selected' : ''}>${esc(_t('policy_all'))}</option>
                </select>
            </div>`;
        }

        html += `<h3 id="grupo-contenido-titulo" style="color:#ebcb8b; font-size:1em; margin:8px 0;">${esc(_t('group_members'))} (${g.miembros.length})</h3>`;
        html += `<div id="grupo-contenido"></div>`;
        html += `<button id="btn-salir-grupo" style="width:100%; margin-top:14px; background:transparent; color:#bf616a; border:1px solid #bf616a; padding:8px; border-radius:6px; cursor:pointer;">${esc(_t('btn_salir_grupo'))}</button>`;

        body.innerHTML = html;

        $('grupo-back').onclick = () => cargarGrupos();
        $('grupo-chat').onclick = () => abrirChatGrupo(g.id, g.name);
        $('grupo-lb').onclick = () => toggleLeaderboard();
        $('btn-salir-grupo').onclick = () => salirGrupo(g.id);
        if (puedeInvitar) {
            const iIn = $('in-invitar-grupo');
            $('btn-invitar-grupo').onclick = () => invitarAGrupo(g.id, iIn.value.trim());
            iIn.onkeydown = (e) => { if (e.key === 'Enter') invitarAGrupo(g.id, iIn.value.trim()); };
        }
        if (puedeAdmin) {
            $('sel-invite-policy').onchange = (e) => cambiarPolitica(g.id, e.target.value);
        }

        if (lbVisible) pintarLeaderboardGrupo(); else pintarMiembros();
    }

    function toggleLeaderboard() {
        lbVisible = !lbVisible;
        // Actualizamos estilo del botón y título de la sección + contenido.
        const btn = $('grupo-lb');
        if (btn) Object.assign(btn.style, lbVisible
            ? { background: '#d08770', color: '#2e3440' }
            : { background: '#ebcb8b', color: '#2e3440' });
        const titulo = $('grupo-contenido-titulo');
        if (lbVisible) {
            if (titulo) titulo.innerHTML = '';
            pintarLeaderboardGrupo();
        } else {
            if (titulo) titulo.textContent = `${_t('group_members')} (${grupoActual.miembros.length})`;
            pintarMiembros();
        }
    }

    // ----- Vista: lista de miembros (con gestión si soy admin/owner) -----
    function pintarMiembros() {
        const g = grupoActual;
        const cont = $('grupo-contenido');
        if (!cont) return;
        const puedeAdmin = (g.miRol === 'owner' || g.miRol === 'admin');
        const rolTxt = { owner: _t('rol_owner'), admin: _t('rol_admin'), member: _t('rol_member') };
        let html = '';
        g.miembros.forEach(m => {
            const esOwner = m.id === g.owner_id;
            const soyYo = m.username === miUsernameLogueado;
            let acciones = '';
            if (puedeAdmin && !esOwner && !soyYo) {
                if (m.role === 'admin') {
                    acciones += `<button class="btn-m-demote" data-id="${m.id}" title="${esc(_t('btn_quitar_admin'))}" style="background:#4c566a; color:#fff; border:none; padding:4px 7px; border-radius:4px; cursor:pointer; margin-right:4px; font-size:.8em;">${esc(_t('btn_quitar_admin'))}</button>`;
                } else {
                    acciones += `<button class="btn-m-promote" data-id="${m.id}" title="${esc(_t('btn_hacer_admin'))}" style="background:#5e81ac; color:#fff; border:none; padding:4px 7px; border-radius:4px; cursor:pointer; margin-right:4px; font-size:.8em;">${esc(_t('btn_hacer_admin'))}</button>`;
                }
                acciones += `<button class="btn-m-kick" data-id="${m.id}" data-name="${esc(m.username)}" title="${esc(_t('btn_expulsar'))}" style="background:transparent; color:#bf616a; border:1px solid #bf616a; padding:4px 7px; border-radius:4px; cursor:pointer; font-size:.8em;">${esc(_t('btn_expulsar'))}</button>`;
            }
            html += `<div style="display:flex; align-items:center; justify-content:space-between; background:#3b4252; padding:7px 10px; border-radius:6px; margin-bottom:5px;">
                <span style="font-weight:bold; color:#eceff4; overflow:hidden; text-overflow:ellipsis;">${esc(m.username)}
                    <span style="opacity:.6; font-size:.8em; font-weight:normal;">· ${esc(rolTxt[m.role] || m.role)}</span>
                </span>
                <span style="flex:none;">${acciones}</span>
            </div>`;
        });
        cont.innerHTML = html;
        cont.querySelectorAll('.btn-m-promote').forEach(b => b.onclick = () => cambiarRol(g.id, +b.dataset.id, 'admin'));
        cont.querySelectorAll('.btn-m-demote').forEach(b => b.onclick = () => cambiarRol(g.id, +b.dataset.id, 'member'));
        cont.querySelectorAll('.btn-m-kick').forEach(b => b.onclick = () => expulsar(g.id, +b.dataset.id, b.dataset.name));
    }

    // ----- Vista: clasificación propia del grupo (+ botón de info) -----
    async function pintarLeaderboardGrupo() {
        const cont = $('grupo-contenido');
        if (!cont) return;
        cont.innerHTML = `<p style="opacity:.6; text-align:center;">${esc(_t('cargando_social'))}</p>`;
        const r = await fetch('/api/groups/' + grupoActual.id + '/leaderboard');
        const d = await r.json();
        if (!d.exito) { cont.innerHTML = ''; return; }
        const rows = d.leaderboard || [];

        // Cabecera con el botón sutil de información y su tooltip ligero.
        let html = `<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
            <span style="color:#ebcb8b; font-weight:bold; font-size:.95em;">${esc(_t('group_leaderboard'))}</span>
            <span id="lb-info-wrap" style="position:relative;">
                <button id="lb-info-btn" aria-label="info" style="background:transparent; border:1px solid #4c566a; color:#88c0d0; width:20px; height:20px; border-radius:50%; font-size:.75em; cursor:pointer; line-height:1; padding:0;">ⓘ</button>
                <span id="lb-info-tip" class="hidden" style="position:absolute; right:0; top:26px; width:230px; background:#232833; color:#d8dee9; border:1px solid #4c566a; border-radius:6px; padding:9px 11px; font-size:.78em; line-height:1.45; font-weight:normal; text-align:left; box-shadow:0 6px 16px rgba(0,0,0,.6); z-index:10;">${esc(_t('group_info_expl'))}</span>
            </span>
        </div>`;

        if (!rows.length) {
            html += `<p style="opacity:.6; text-align:center;">${esc(_t('sin_miembros_leaderboard'))}</p>`;
        } else {
            html += `<table style="width:100%; border-collapse:collapse; text-align:center; font-size:.9em; color:#eceff4;">
                <thead><tr style="background:#3b4252;">
                    <th style="padding:6px;">#</th>
                    <th style="padding:6px; text-align:left;">${esc(_t('user_colname') || 'Jugador')}</th>
                    <th style="padding:6px; color:#a3be8c;">ELO</th>
                    <th style="padding:6px;">%</th>
                </tr></thead><tbody>`;
            rows.forEach((j, i) => {
                let medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : (i + 1);
                html += `<tr>
                    <td style="padding:6px; border-bottom:1px solid #3b4252;">${medal}</td>
                    <td style="padding:6px; border-bottom:1px solid #3b4252; text-align:left; color:#ebcb8b; font-weight:bold;">${esc(j.username)}</td>
                    <td style="padding:6px; border-bottom:1px solid #3b4252; color:#81a1c1; font-weight:bold;">${j.elo}</td>
                    <td style="padding:6px; border-bottom:1px solid #3b4252;">${j.winrate}%</td>
                </tr>`;
            });
            html += `</tbody></table>`;
        }
        cont.innerHTML = html;

        // Tooltip: en escritorio aparece al pasar el ratón y se va al salir;
        // en móvil (sin hover) el clic lo alterna, y vuelve a ocultarse al reclicar.
        const btn = $('lb-info-btn'), tip = $('lb-info-tip');
        if (btn && tip) {
            btn.addEventListener('mouseenter', () => tip.classList.remove('hidden'));
            btn.addEventListener('mouseleave', () => tip.classList.add('hidden'));
            btn.addEventListener('click', (e) => { e.stopPropagation(); tip.classList.toggle('hidden'); });
        }
    }

    async function invitarAGrupo(groupId, username) {
        if (!username) return;
        const r = await fetch('/api/groups/' + groupId + '/invite', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        const d = await r.json();
        mostrarToast(d.exito ? _t('miembro_anadido') : msgError(d.mensaje));
        if (d.exito) abrirGrupo(groupId);
    }

    async function cambiarRol(groupId, userId, role) {
        const r = await fetch(`/api/groups/${groupId}/members/${userId}/role`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role })
        });
        const d = await r.json();
        if (d.exito) abrirGrupo(groupId); else mostrarToast(msgError(d.mensaje));
    }

    async function expulsar(groupId, userId, nombre) {
        if (!confirm(_td('confirm_expulsar', { nombre }))) return;
        const r = await fetch(`/api/groups/${groupId}/members/${userId}/remove`, { method: 'POST' });
        const d = await r.json();
        if (d.exito) abrirGrupo(groupId); else mostrarToast(msgError(d.mensaje));
    }

    async function cambiarPolitica(groupId, policy) {
        const r = await fetch('/api/groups/' + groupId + '/settings', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ invite_policy: policy })
        });
        const d = await r.json();
        if (d.exito) { grupoActual.invite_policy = policy; renderGrupoDetalle(); }
        else mostrarToast(msgError(d.mensaje));
    }

    async function salirGrupo(groupId) {
        if (!confirm(_t('confirm_salir_grupo'))) return;
        await fetch('/api/groups/' + groupId + '/leave', { method: 'POST' });
        cargarGrupos();
    }

    // ======================================================================
    // Invitaciones de partida entrantes (popup)
    // ======================================================================
    let invitePendiente = null;
    function mostrarInvitacionPartida(n) {
        invitePendiente = n;
        $('invite-popup-text').textContent = _td('invitacion_de', { nombre: n.de, n: n.al_mejor_de });
        $('invite-popup').classList.remove('hidden');
    }

    function aceptarInvitacion() {
        if (!invitePendiente) return;
        const cod = invitePendiente.codigo;
        const nombre = miUsernameLogueado || (($('nombre-jugador') || {}).value || '').trim() || 'Jugador';
        localStorage.setItem('callmus_nombre', nombre);
        localStorage.setItem('callmus_sala', cod);
        socket.emit('unirse_sala', { nombre, codigo: cod });
        $('invite-popup').classList.add('hidden');
        invitePendiente = null;
    }

    function rechazarInvitacion() {
        $('invite-popup').classList.add('hidden');
        invitePendiente = null;
    }

    // ======================================================================
    // Notificaciones en tiempo real
    // ======================================================================
    if (typeof socket !== 'undefined') {
        socket.on('notificacion', (n) => {
            switch (n.tipo) {
                case 'mensaje':
                    if (chatTipo === 'dm' && chatIdActual === n.sender_id) {
                        appendMensaje(n, false, false);
                        // marcamos leído reabriendo silenciosamente el mark-read
                        fetch('/api/messages/' + n.sender_id);
                    } else {
                        unreadDM += 1; pintarBadge();
                        mostrarToast(_td('toast_mensaje_nuevo', { nombre: n.de }));
                    }
                    break;
                case 'mensaje_grupo':
                    if (chatTipo === 'grupo' && chatIdActual === n.group_id) {
                        appendMensaje(n, n.sender_name === miUsernameLogueado, true);
                    } else {
                        unreadGrupos += 1; pintarBadge();
                        mostrarToast(_td('toast_mensaje_nuevo', { nombre: n.sender_name }));
                    }
                    break;
                case 'solicitud_amistad':
                    numSolicitudes += 1; pintarBadge();
                    mostrarToast(_td('toast_nueva_solicitud', { nombre: n.de }));
                    if (esPanelAbierto() && tabActual === 'amigos' && !chatTipo) cargarAmigos();
                    break;
                case 'amistad_aceptada':
                    mostrarToast(_td('toast_amistad_aceptada', { nombre: n.de }));
                    if (esPanelAbierto() && tabActual === 'amigos' && !chatTipo) cargarAmigos();
                    break;
                case 'presencia':
                    if (esPanelAbierto() && tabActual === 'amigos' && !chatTipo) cargarAmigos();
                    break;
                case 'invitacion_grupo':
                    unreadGrupos += 1; pintarBadge();
                    mostrarToast(_td('toast_invitacion_grupo', { nombre: n.de, grupo: n.nombre }));
                    break;
                case 'rol_grupo':
                    mostrarToast(_td('toast_rol_grupo', { grupo: n.nombre }));
                    if (esPanelAbierto() && tabActual === 'grupos' && grupoActual && grupoActual.id === n.group_id) abrirGrupo(n.group_id);
                    break;
                case 'expulsado_grupo':
                    mostrarToast(_td('toast_expulsado', { grupo: n.nombre }));
                    if (esPanelAbierto() && tabActual === 'grupos') cargarGrupos();
                    break;
                case 'invitacion_partida':
                    mostrarInvitacionPartida(n);
                    break;
            }
        });

        socket.on('error_invitacion', (d) => mostrarToast(msgError(d.mensaje)));
    }

    function esPanelAbierto() {
        const m = $('modal-social');
        return m && !m.classList.contains('hidden');
    }

    // ======================================================================
    // Enganche de botones + arranque
    // ======================================================================
    const btnAmigos = $('btn-amigos');
    if (btnAmigos) btnAmigos.addEventListener('click', abrirSocial);
    $('tab-amigos').addEventListener('click', () => setTab('amigos'));
    $('tab-grupos').addEventListener('click', () => setTab('grupos'));
    $('invite-accept').addEventListener('click', aceptarInvitacion);
    $('invite-decline').addEventListener('click', rechazarInvitacion);

    // Badge inicial cuando ya se conoce la sesión (auth.js hace el fetch de sesión).
    setTimeout(refrescarBadge, 1500);
})();
