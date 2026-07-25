// ==========================================
// VENTANA DE AJUSTES (settings.js) — Roadmap #22
// ------------------------------------------
// Se carga DESPUÉS de app.js y auth.js, y comparte con ellos por el ámbito
// global: usuarioActual, miUsernameLogueado, comprobarSesion(), cerrarModales(),
// aplicarTraduccion(), t(), t_dinamico(), modalOverlay.
//
// El idioma está siempre disponible (con cuenta o sin ella); el bloque de cuenta
// solo aparece con la sesión iniciada. Ninguna operación manda a quién afecta:
// el servidor la saca de la sesión.
// ==========================================

const modalSettings = document.getElementById('modal-settings');
const btnSettings = document.getElementById('btn-settings');

// --- Utilidades ---

function _tt(clave) {
    return (typeof t === 'function') ? t(clave) : clave;
}

// Traduce la respuesta del servidor. `codigo` es la clave del diccionario y el
// resto del objeto sirve para rellenar sus huecos ({dias}, {email}…). Si la clave
// no existiera todavía, cae al mensaje en castellano que manda el propio servidor.
function _traducir(datos) {
    if (!datos || !datos.codigo) return (datos && datos.mensaje) || '';
    const texto = (typeof t_dinamico === 'function') ? t_dinamico(datos.codigo, datos) : datos.codigo;
    return (texto === datos.codigo) ? (datos.mensaje || datos.codigo) : texto;
}

function _post(url, cuerpo) {
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        cache: 'no-store',
        credentials: 'same-origin',
        body: JSON.stringify(cuerpo)
    }).then(res => res.json()).catch(() => ({ exito: false, codigo: 'err_red' }));
}

function _mensaje(panel, datos) {
    const p = panel.querySelector('.settings-msg');
    if (!p) return;
    p.innerText = _traducir(datos);
    p.classList.toggle('ok', !!(datos && datos.exito));
}

function _esperando(panel, clave) {
    const p = panel.querySelector('.settings-msg');
    if (!p) return;
    p.innerText = _tt(clave);
    p.classList.add('ok');
}

// ==========================================
// 1. Credencial de las operaciones sensibles
// ------------------------------------------
// Cada panel lleva su propio bloque: contraseña actual o, para quien entró con
// Google y no tiene ninguna, un código de un solo uso enviado a su correo.
// ==========================================

function _construirCredenciales() {
    document.querySelectorAll('#modal-settings .credencial').forEach(div => {
        if (div.dataset.listo) return;
        div.dataset.listo = '1';
        div.innerHTML =
            '<input type="password" class="cred-pass" data-i18n="ajustes_password_actual" placeholder="Contraseña actual">' +
            '<span class="credencial-link" data-i18n="ajustes_sin_password_link">Entré con Google o no tengo contraseña</span>' +
            '<input type="text" class="cred-code hidden" inputmode="numeric" maxlength="6" data-i18n="ajustes_codigo_placeholder" placeholder="Código de 6 dígitos">';

        div.querySelector('.credencial-link').addEventListener('click', () => _pedirCodigo(div));
    });
    if (typeof aplicarTraduccion === 'function') aplicarTraduccion();
}

function _pedirCodigo(div) {
    const panel = div.closest('.settings-panel');
    _esperando(panel, 'ajustes_enviando');
    _post('/auth/cuenta/codigo', {}).then(datos => {
        if (datos.exito) {
            div.querySelector('.cred-pass').classList.add('hidden');
            div.querySelector('.credencial-link').classList.add('hidden');
            div.querySelector('.cred-code').classList.remove('hidden');
            _mensaje(panel, {
                exito: true,
                codigo: 'ajustes_codigo_enviado_a',
                email: datos.email_oculto || '',
                mensaje: datos.mensaje
            });
        } else {
            _mensaje(panel, datos);
        }
    });
}

// Devuelve {password: …} o {code: …} según lo que haya rellenado el usuario.
function _credencial(panel) {
    const div = panel.querySelector('.credencial');
    if (!div) return {};
    const pass = div.querySelector('.cred-pass');
    const code = div.querySelector('.cred-code');
    if (code && !code.classList.contains('hidden') && code.value.trim()) {
        return { code: code.value.trim() };
    }
    return { password: pass ? pass.value : '' };
}

function _limpiarCredencial(panel) {
    const div = panel.querySelector('.credencial');
    if (!div) return;
    div.querySelectorAll('input').forEach(i => { i.value = ''; });
}

// ==========================================
// 2. Pintar la ventana según haya cuenta o no
// ==========================================

function refrescarAjustes() {
    if (!modalSettings) return;
    _construirCredenciales();

    const usuario = (typeof usuarioActual !== 'undefined') ? usuarioActual : null;
    const bloqueInvitado = document.getElementById('settings-invitado');
    const bloqueCuenta = document.getElementById('settings-cuenta');

    bloqueInvitado.classList.toggle('hidden', !!usuario);
    bloqueCuenta.classList.toggle('hidden', !usuario);

    if (!usuario) {
        // El nombre del menú manda si ya lo ha escrito ahí: sólo se guarda en
        // localStorage al crear o unirse a una partida, no al teclearlo.
        const campo = document.getElementById('settings-nombre-invitado');
        const campoMenu = document.getElementById('nombre-jugador');
        if (campo) {
            campo.value = (campoMenu && campoMenu.value.trim())
                || localStorage.getItem('callmus_nombre') || '';
        }
        return;
    }

    document.getElementById('settings-username').innerText = usuario.username;
    document.getElementById('settings-email').innerText = usuario.email || '';

    const spanCodigo = document.getElementById('settings-codigo');
    if (spanCodigo) spanCodigo.innerText = usuario.codigo ? '#' + usuario.codigo : '';

    // Periodo de espera entre cambios de nombre.
    const aviso = document.getElementById('aviso-cooldown-username');
    const dias = usuario.dias_para_cambiar_username || 0;
    aviso.classList.toggle('hidden', dias <= 0);
    if (dias > 0) aviso.innerText = t_dinamico('ajustes_espera_username', { dias: dias });
    const btnUsername = document.querySelector('[data-accion="username"]');
    if (btnUsername) btnUsername.disabled = dias > 0;

    // Cuentas de Google: no hay contraseña que cambiar, hay una que crear.
    const summaryPass = document.getElementById('summary-password');
    if (summaryPass) {
        summaryPass.setAttribute('data-i18n', usuario.tiene_password ? 'ajustes_cambiar_password' : 'ajustes_crear_password');
        summaryPass.innerText = _tt(summaryPass.getAttribute('data-i18n'));
    }
    // …y su credencial solo puede ser el código del correo.
    document.querySelectorAll('#modal-settings .credencial').forEach(div => {
        const pass = div.querySelector('.cred-pass');
        const enlace = div.querySelector('.credencial-link');
        const soloCodigo = !usuario.tiene_password;
        if (pass && !div.querySelector('.cred-code').classList.contains('hidden')) return; // ya pidió código
        if (pass) pass.classList.toggle('hidden', soloCodigo);
        if (enlace) enlace.innerText = soloCodigo ? _tt('ajustes_enviar_codigo') : _tt('ajustes_sin_password_link');
    });
}

// ==========================================
// 3. Abrir / cerrar
// ==========================================

if (btnSettings) {
    btnSettings.addEventListener('click', () => {
        cerrarModales();
        refrescarAjustes();
        modalOverlay.style.display = 'flex';
        modalOverlay.classList.remove('hidden');
        modalSettings.classList.remove('hidden');
    });
}

// Copiar el código público al portapapeles de un click.
document.getElementById('settings-codigo')?.addEventListener('click', (e) => {
    const codigo = e.currentTarget.innerText.trim();
    if (!codigo || !navigator.clipboard) return;
    navigator.clipboard.writeText(codigo).then(() => {
        const original = e.currentTarget.innerText;
        e.currentTarget.innerText = _tt('ajustes_codigo_copiado');
        setTimeout(() => { e.currentTarget.innerText = original; }, 1200);
    }).catch(() => {});
});

// El botón de idioma vive dentro de esta ventana pero lo gestiona app.js (y
// tutorial.js escucha el mismo click): aquí solo repintamos lo que rellenamos a
// mano y no lleva data-i18n.
const btnLangSettings = document.getElementById('btn-lang');
if (btnLangSettings) btnLangSettings.addEventListener('click', () => refrescarAjustes());

// Invitados: el nombre de la mesa, sincronizado con el campo del menú.
const campoNombreInvitado = document.getElementById('settings-nombre-invitado');
if (campoNombreInvitado) {
    campoNombreInvitado.addEventListener('input', () => {
        const nombre = campoNombreInvitado.value.trim();
        localStorage.setItem('callmus_nombre', nombre);
        const campoMenu = document.getElementById('nombre-jugador');
        if (campoMenu && !campoMenu.disabled) campoMenu.value = nombre;
    });
}

document.getElementById('settings-btn-login')?.addEventListener('click', () => {
    cerrarModales();
    document.getElementById('btn-show-login').click();
});
document.getElementById('settings-btn-signup')?.addEventListener('click', () => {
    cerrarModales();
    document.getElementById('btn-show-signup').click();
});

// ==========================================
// 4. Acciones de la cuenta
// ==========================================

modalSettings?.addEventListener('click', (e) => {
    const boton = e.target.closest('[data-accion]');
    if (!boton) return;
    const panel = boton.closest('.settings-panel');
    const accion = boton.getAttribute('data-accion');

    if (accion === 'username') return _guardarUsername(panel);
    if (accion === 'email-solicitar') return _solicitarEmail(panel);
    if (accion === 'email-confirmar') return _confirmarEmail(panel);
    if (accion === 'password') return _guardarPassword(panel);
    if (accion === 'eliminar') return _eliminarCuenta(panel);
});

function _guardarUsername(panel) {
    const nuevo = document.getElementById('in-nuevo-username').value.trim();
    if (!nuevo) return;

    _esperando(panel, 'ajustes_guardando');
    _post('/auth/cuenta/username', Object.assign({ username: nuevo }, _credencial(panel)))
        .then(datos => {
            _mensaje(panel, datos);
            if (!datos.exito) return;
            _limpiarCredencial(panel);
            // El socket abierto todavía se identifica con el nombre anterior:
            // recargamos para que todo (mesa, amigos, chats) hable del nuevo.
            setTimeout(() => window.location.reload(), 1200);
        });
}

function _solicitarEmail(panel) {
    const email = document.getElementById('in-nuevo-email').value.trim();
    if (!email) return;

    _esperando(panel, 'ajustes_enviando');
    _post('/auth/cuenta/email/solicitar', Object.assign({ email: email }, _credencial(panel)))
        .then(datos => {
            _mensaje(panel, datos);
            if (!datos.exito) return;
            _limpiarCredencial(panel);
            document.getElementById('paso-confirmar-email').classList.remove('hidden');
            document.getElementById('in-codigo-email').focus();
        });
}

function _confirmarEmail(panel) {
    const email = document.getElementById('in-nuevo-email').value.trim();
    const code = document.getElementById('in-codigo-email').value.trim();
    if (!code) return;

    _esperando(panel, 'ajustes_guardando');
    _post('/auth/cuenta/email/confirmar', { email: email, code: code }).then(datos => {
        _mensaje(panel, datos);
        if (!datos.exito) return;
        document.getElementById('paso-confirmar-email').classList.add('hidden');
        document.getElementById('in-nuevo-email').value = '';
        document.getElementById('in-codigo-email').value = '';
        comprobarSesion();
    });
}

function _guardarPassword(panel) {
    const nueva = document.getElementById('in-password-nueva').value;
    const repetida = document.getElementById('in-password-repetir').value;

    if (nueva !== repetida) {
        _mensaje(panel, { exito: false, codigo: 'ajustes_password_no_coincide' });
        return;
    }

    _esperando(panel, 'ajustes_guardando');
    _post('/auth/cuenta/password', Object.assign({ password_nueva: nueva }, _credencial(panel)))
        .then(datos => {
            _mensaje(panel, datos);
            if (!datos.exito) return;
            document.getElementById('in-password-nueva').value = '';
            document.getElementById('in-password-repetir').value = '';
            _limpiarCredencial(panel);
            comprobarSesion();   // ahora la cuenta ya tiene contraseña
        });
}

function _eliminarCuenta(panel) {
    const confirmacion = document.getElementById('in-confirmar-borrado').value.trim();
    if (!confirmacion) return;

    _esperando(panel, 'ajustes_guardando');
    _post('/auth/cuenta/eliminar', Object.assign({ confirmacion: confirmacion }, _credencial(panel)))
        .then(datos => {
            _mensaje(panel, datos);
            if (!datos.exito) return;
            localStorage.removeItem('callmus_sala');
            localStorage.removeItem('callmus_token');
            localStorage.removeItem('callmus_nombre');
            setTimeout(() => window.location.reload(), 1800);
        });
}

// Estado inicial (auth.js volverá a llamarnos cuando resuelva /auth/sesion).
refrescarAjustes();
