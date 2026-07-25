// ==========================================================================
// SOPORTE Y AVISOS DEL ADMINISTRADOR (soporte.js) — Roadmap #13
// --------------------------------------------------------------------------
// Dos cosas, ambas del lado del jugador:
//   1. El buzón de soporte que vive dentro de la ventana de Ajustes: abrir una
//      incidencia y mantener la conversación con el administrador hasta que
//      alguno la dé por resuelta.
//   2. Los avisos que manda el administrador: los `pin` se pintan fijados en el
//      menú y las `notificacion` salen una vez en un popup.
//
// Se carga DESPUÉS de app.js, social.js y settings.js y comparte con ellos por
// el ámbito global: t(), t_dinamico(), aplicarTraduccion(), usuarioActual,
// refrescarAjustes(), socket. Todo el texto que viene del servidor se pinta con
// textContent: un mensaje de soporte o un aviso nunca debe poder inyectar HTML.
// ==========================================================================

(function () {
    const $ = (id) => document.getElementById(id);

    function _t(k) { return (typeof t === 'function') ? t(k) : k; }
    function _td(k, v) { return (typeof t_dinamico === 'function') ? t_dinamico(k, v) : k; }

    function pedir(url, metodo, cuerpo) {
        return fetch(url, {
            method: metodo || 'GET',
            headers: cuerpo ? { 'Content-Type': 'application/json' } : {},
            cache: 'no-store',
            credentials: 'same-origin',
            body: cuerpo ? JSON.stringify(cuerpo) : undefined
        }).then(r => r.json()).catch(() => ({ exito: false, mensaje: 'err_red' }));
    }

    // Errores que devuelve el servidor de soporte, traducidos.
    const ERRORES = {
        vacio: 'soporte_vacio',
        demasiado_largo: 'soporte_largo',
        rate_limit: 'soporte_rate_limit',
        no_auth: 'err_sin_sesion',
        err_red: 'err_red'
    };

    function mensajePanel(texto, ok) {
        const p = document.querySelector('#soporte-panel .settings-msg');
        if (!p) return;
        p.textContent = texto;
        p.classList.toggle('ok', !!ok);
    }

    function estaLogueado() {
        return typeof usuarioActual !== 'undefined' && !!usuarioActual;
    }

    function fechaCorta(iso) {
        if (!iso) return '';
        const d = new Date(iso);
        return isNaN(d) ? '' : d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
    }

    // ======================================================================
    // 1. Buzón de soporte (dentro de Ajustes)
    // ======================================================================

    let hiloActual = null;

    async function cargarMisIncidencias() {
        const lista = $('soporte-lista');
        if (!lista) return;
        const d = await pedir('/api/soporte');
        lista.replaceChildren();
        if (!d.exito) return;

        const titulo = document.createElement('h4');
        titulo.textContent = _t('soporte_mis_incidencias');
        lista.appendChild(titulo);

        if (!d.tickets.length) {
            const p = document.createElement('p');
            p.className = 'settings-nota';
            p.textContent = _t('soporte_sin_incidencias');
            lista.appendChild(p);
            return;
        }

        d.tickets.forEach(ticket => {
            const fila = document.createElement('button');
            fila.className = 'soporte-fila';
            fila.type = 'button';

            const asunto = document.createElement('span');
            asunto.className = 'soporte-asunto';
            asunto.textContent = ticket.asunto;

            const estado = document.createElement('span');
            estado.className = 'soporte-estado ' + ticket.estado;
            estado.textContent = _t('soporte_estado_' + ticket.estado);

            fila.append(asunto, estado);
            if (!ticket.leido_user) {
                const punto = document.createElement('span');
                punto.className = 'soporte-punto';
                fila.appendChild(punto);
            }
            fila.addEventListener('click', () => abrirHilo(ticket.id));
            lista.appendChild(fila);
        });
    }

    async function abrirHilo(id) {
        const d = await pedir('/api/soporte/' + id);
        if (!d.exito) { mensajePanel(_t(ERRORES[d.mensaje] || 'err_red'), false); return; }
        hiloActual = d.ticket;

        $('soporte-hilo-titulo').textContent = d.ticket.asunto;
        const caja = $('soporte-hilo-mensajes');
        caja.replaceChildren();
        d.mensajes.forEach(m => {
            const burbuja = document.createElement('div');
            burbuja.className = 'soporte-burbuja ' + m.autor;
            const meta = document.createElement('span');
            meta.className = 'soporte-meta';
            meta.textContent = (m.autor === 'admin' ? _t('soporte_autor_admin') : _t('soporte_autor_yo'))
                + ' · ' + fechaCorta(m.created_at);
            burbuja.appendChild(meta);
            // textContent: el cuerpo lo escribe una persona, nunca se interpreta como HTML.
            burbuja.appendChild(document.createTextNode(m.body));
            caja.appendChild(burbuja);
        });
        caja.scrollTop = caja.scrollHeight;

        $('soporte-hilo-respuesta').value = '';
        $('soporte-hilo').classList.remove('hidden');
        $('soporte-lista').classList.add('hidden');
        $('soporte-nuevo').classList.add('hidden');
        mensajePanel('', true);
        refrescarBadgeSoporte();
    }

    function cerrarHilo() {
        hiloActual = null;
        $('soporte-hilo').classList.add('hidden');
        $('soporte-lista').classList.remove('hidden');
        $('soporte-nuevo').classList.remove('hidden');
        cargarMisIncidencias();
    }

    async function enviarIncidencia() {
        const asunto = $('soporte-asunto').value.trim();
        const cuerpo = $('soporte-cuerpo').value.trim();
        if (!asunto || !cuerpo) { mensajePanel(_t('soporte_vacio'), false); return; }

        const d = await pedir('/api/soporte', 'POST', {
            tipo: $('soporte-tipo').value, asunto: asunto, cuerpo: cuerpo
        });
        if (!d.exito) { mensajePanel(_t(ERRORES[d.mensaje] || 'err_red'), false); return; }

        $('soporte-asunto').value = '';
        $('soporte-cuerpo').value = '';
        $('soporte-nuevo').removeAttribute('open');
        mensajePanel(_t('soporte_enviado'), true);
        cargarMisIncidencias();
    }

    async function responderHilo() {
        if (!hiloActual) return;
        const body = $('soporte-hilo-respuesta').value.trim();
        if (!body) return;
        const d = await pedir('/api/soporte/' + hiloActual.id, 'POST', { body: body });
        if (!d.exito) { mensajePanel(_t(ERRORES[d.mensaje] || 'err_red'), false); return; }
        abrirHilo(hiloActual.id);
    }

    async function resolverHilo() {
        if (!hiloActual) return;
        await pedir('/api/soporte/' + hiloActual.id + '/cerrar', 'POST', {});
        cerrarHilo();
    }

    // Acciones del panel (el listener de settings.js ignora estas claves).
    document.getElementById('modal-settings')?.addEventListener('click', (e) => {
        const boton = e.target.closest('[data-accion]');
        if (!boton) return;
        const accion = boton.getAttribute('data-accion');
        if (accion === 'soporte-enviar') return enviarIncidencia();
        if (accion === 'soporte-responder') return responderHilo();
        if (accion === 'soporte-resolver') return resolverHilo();
        if (accion === 'soporte-volver') return cerrarHilo();
    });

    // Al desplegar la sección se cargan los hilos (no antes: es una petición más).
    $('seccion-soporte')?.addEventListener('toggle', (e) => {
        if (e.target.open && estaLogueado()) cargarMisIncidencias();
    });

    // ======================================================================
    // 2. Pintar la sección según haya cuenta o no + acceso al panel de admin
    // ----------------------------------------------------------------------
    // settings.js llama a refrescarAjustes() cada vez que cambia la sesión o el
    // idioma; lo envolvemos para engancharnos a ese mismo momento en vez de
    // duplicar la lógica de "¿hay usuario?".
    // ======================================================================

    const refrescarAjustesOriginal = window.refrescarAjustes;
    window.refrescarAjustes = function () {
        if (typeof refrescarAjustesOriginal === 'function') refrescarAjustesOriginal();
        pintarSoporte();
    };

    function pintarSoporte() {
        const logueado = estaLogueado();
        $('soporte-invitado')?.classList.toggle('hidden', logueado);
        $('soporte-logueado')?.classList.toggle('hidden', !logueado);

        const filaAdmin = $('settings-fila-admin');
        if (filaAdmin) {
            const esAdmin = logueado && !!usuarioActual.is_admin;
            filaAdmin.classList.toggle('hidden', !esAdmin);
        }
        if (logueado && $('seccion-soporte')?.open) cargarMisIncidencias();
    }

    // ======================================================================
    // 3. Contador de respuestas sin leer, sobre el botón de Ajustes
    // ======================================================================

    function refrescarBadgeSoporte() {
        if (!estaLogueado()) { pintarBadgeSoporte(0); return; }
        pedir('/api/soporte').then(d => pintarBadgeSoporte(d.exito ? d.no_leidos : 0));
    }

    function pintarBadgeSoporte(n) {
        const boton = $('btn-settings');
        if (!boton) return;
        let punto = $('settings-badge');
        if (!n) { if (punto) punto.remove(); return; }
        if (!punto) {
            boton.style.position = 'relative';
            punto = document.createElement('span');
            punto.id = 'settings-badge';
            boton.appendChild(punto);
        }
        punto.textContent = n;
    }

    // ======================================================================
    // 4. Avisos del administrador
    // ======================================================================

    const colaAvisos = [];
    let avisoEnPantalla = null;

    async function cargarAnuncios() {
        const d = await pedir('/api/anuncios');
        if (!d.exito) return;
        pintarFijados(d.pins || [], d.mantenimiento);
        (d.notificaciones || []).forEach(encolarAviso);
        siguienteAviso();
    }

    function pintarFijados(pins, mantenimiento) {
        const caja = $('anuncios-fijados');
        if (!caja) return;
        caja.replaceChildren();

        // El cartel de mantenimiento va primero y con su propio estilo: es lo
        // único que puede cambiar la decisión de ponerse a jugar ahora mismo.
        if (mantenimiento) {
            caja.appendChild(tarjetaFijada(_t('mantenimiento_titulo'), mantenimiento, true));
        }
        pins.forEach(p => caja.appendChild(tarjetaFijada(p.titulo, p.cuerpo, false)));
    }

    function tarjetaFijada(titulo, cuerpo, esMantenimiento) {
        const div = document.createElement('div');
        div.className = 'anuncio-fijado' + (esMantenimiento ? ' mantenimiento' : '');
        if (titulo) {
            const h = document.createElement('h4');
            h.textContent = titulo;
            div.appendChild(h);
        }
        const p = document.createElement('p');
        p.textContent = cuerpo;
        div.appendChild(p);
        return div;
    }

    function encolarAviso(aviso) {
        if (colaAvisos.some(a => a.id === aviso.id) || (avisoEnPantalla && avisoEnPantalla.id === aviso.id)) return;
        colaAvisos.push(aviso);
    }

    function siguienteAviso() {
        if (avisoEnPantalla || !colaAvisos.length) return;
        const popup = $('anuncio-popup');
        if (!popup) return;
        avisoEnPantalla = colaAvisos.shift();
        $('anuncio-popup-titulo').textContent = avisoEnPantalla.titulo || _t('toast_anuncio');
        $('anuncio-popup-cuerpo').textContent = avisoEnPantalla.cuerpo || '';
        popup.classList.remove('hidden');
    }

    $('anuncio-popup-ok')?.addEventListener('click', () => {
        const popup = $('anuncio-popup');
        popup.classList.add('hidden');
        if (avisoEnPantalla && avisoEnPantalla.id) {
            // Marcarlo leído es lo que impide que vuelva a salir en el próximo arranque.
            pedir('/api/anuncios/' + avisoEnPantalla.id + '/leido', 'POST', {});
        }
        avisoEnPantalla = null;
        siguienteAviso();
    });

    // ======================================================================
    // 5. Tiempo real
    // ======================================================================

    if (typeof socket !== 'undefined') {
        // social.js tiene su propio 'notificacion'; los listeners se acumulan y
        // cada uno ignora los tipos que no son suyos.
        socket.on('notificacion', (n) => {
            if (n.tipo === 'anuncio') {
                if (n.tipo_anuncio === 'pin') { cargarAnuncios(); return; }
                encolarAviso({ id: n.id, titulo: n.titulo, cuerpo: n.cuerpo });
                siguienteAviso();
                cargarAnuncios();          // por si además va fijado
            } else if (n.tipo === 'soporte_respuesta') {
                refrescarBadgeSoporte();
                if (hiloActual && hiloActual.id === n.ticket_id) abrirHilo(n.ticket_id);
            }
        });

        socket.on('anuncio_retirado', () => cargarAnuncios());

        // Baneo en caliente: el servidor cierra el socket, así que lo único útil
        // es recargar para que la web vuelva al estado de invitado.
        socket.on('sesion_cerrada', () => {
            setTimeout(() => window.location.reload(), 500);
        });
    }

    // ======================================================================
    // Arranque
    // ======================================================================
    cargarAnuncios();
    // auth.js resuelve /auth/sesion de forma asíncrona: esperamos a que
    // usuarioActual esté puesto antes de decidir qué enseñar.
    setTimeout(() => { pintarSoporte(); refrescarBadgeSoporte(); cargarAnuncios(); }, 1500);
})();
