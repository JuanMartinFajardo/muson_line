// ==========================================
// MÓDULO DE AUTENTICACIÓN (auth.js)
// ------------------------------------------
// Se carga DESPUÉS de app.js y comparte con él, vía el ámbito global de scripts
// clásicos, estas referencias: miUsernameLogueado, cerrarModales(), t(),
// modalOverlay, modalLogin, modalSignup.
// ==========================================

let temporalRegistrationData = null; // Datos del registro hasta introducir el código
let resetEmail = null;               // Email en proceso de recuperación

// Traducción con respaldo por si t() aún no estuviera disponible
function _t(clave) {
    return (typeof t === 'function') ? t(clave) : clave;
}

// --- Utilidad para mostrar un modal concreto ocultando los demás ---
function mostrarModalAuth(id) {
    const overlay = document.getElementById('modal-overlay');
    overlay.style.display = 'flex';
    overlay.classList.remove('hidden');

    ['modal-login', 'modal-signup', 'modal-verify', 'modal-forgot', 'modal-reset', 'modal-leaderboard', 'modal-privacy']
        .forEach(m => {
            const el = document.getElementById(m);
            if (el) el.classList.add('hidden');
        });

    const objetivo = document.getElementById(id);
    if (objetivo) objetivo.classList.remove('hidden');
}

function setMsg(id, texto, ok = false) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.color = ok ? "#a3be8c" : "#bf616a";
    el.innerText = texto;
}

// ==========================================
// 1. Comprobar sesión activa al cargar
// ------------------------------------------
// La interfaz SIEMPRE se deriva de esta respuesta, nunca se deja como estaba: si
// solo pintáramos el caso "logueado", una pantalla vieja (pestaña restaurada,
// vuelta atrás del navegador) seguiría enseñando al usuario dentro después de
// haber cerrado sesión. Y va con cache:'no-store' porque algunos navegadores
// reutilizaban la respuesta anterior de /auth/sesion, que es justo lo que hacía
// que al entrar siguieras apareciendo fuera hasta recargar a mano.
// ==========================================

let usuarioActual = null;   // Perfil de la sesión (lo lee settings.js)

function comprobarSesion() {
    return fetch('/auth/sesion', { cache: 'no-store', credentials: 'same-origin' })
        .then(res => res.json())
        .then(datos => {
            if (datos.exito) {
                usuarioActual = datos.usuario;
                miUsernameLogueado = datos.usuario.username;
                actualizarInterfazLogueado(datos.usuario);
            } else {
                usuarioActual = null;
                miUsernameLogueado = null;
                actualizarInterfazDeslogueado();
            }
            return datos;
        })
        .catch(() => ({ exito: false }));
}

comprobarSesion();

// Al volver con el botón "atrás" el navegador restaura la página tal cual estaba
// (bfcache) sin ejecutar nada: revisamos la sesión otra vez para que lo que se ve
// coincida con lo que hay.
window.addEventListener('pageshow', (e) => {
    if (e.persisted) comprobarSesion();
});

function actualizarInterfazLogueado(usuario) {
    document.getElementById('user-buttons').classList.add('hidden');
    document.getElementById('user-info-logged').classList.remove('hidden');
    document.getElementById('txt-user-stats').innerText = _t('txt_hola') + `, ${usuario.username}`;

    let inNombre = document.getElementById('nombre-jugador');
    if (inNombre) {
        inNombre.value = usuario.username;
        inNombre.disabled = true;
        inNombre.style.backgroundColor = '#3b4252';
        inNombre.style.color = '#a3be8c';
    }
    if (typeof refrescarAjustes === 'function') refrescarAjustes();
    cerrarModales(); // Definida en app.js
}

function actualizarInterfazDeslogueado() {
    document.getElementById('user-buttons').classList.remove('hidden');
    document.getElementById('user-info-logged').classList.add('hidden');
    document.getElementById('txt-user-stats').innerText = '';

    let inNombre = document.getElementById('nombre-jugador');
    if (inNombre && inNombre.disabled) {
        inNombre.value = localStorage.getItem('callmus_nombre') || '';
        inNombre.disabled = false;
        inNombre.style.backgroundColor = '';
        inNombre.style.color = '';
    }
    if (typeof refrescarAjustes === 'function') refrescarAjustes();
}

// Si Google nos devuelve con error en la URL, lo mostramos
(function comprobarErrorGoogle() {
    const params = new URLSearchParams(window.location.search);
    const error = params.get('auth_error');
    if (!error) return;
    // Limpiamos la query para que no reaparezca al recargar
    window.history.replaceState({}, document.title, window.location.pathname);

    if (error === 'google_sin_cuenta') {
        // Pulsó "Entrar con Google" sin tener cuenta: antes se le creaba una sin
        // avisar. Ahora se le manda al registro.
        alert(_t('google_sin_cuenta'));
        document.getElementById('btn-show-signup')?.click();   // abre el modal de registro
    } else if (error === 'google') {
        alert(_t('google_error'));
    }
})();

// ==========================================
// 2. Registro — Paso 1: solicitar código al correo
// ==========================================
document.getElementById('btn-submit-signup')?.addEventListener('click', () => {
    const user = document.getElementById('signup-user').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const pass = document.getElementById('signup-pass').value;
    const country = document.getElementById('signup-country').value.trim();
    const birth = document.getElementById('signup-birth').value;

    // Validación de cliente (el servidor la repite)
    if (!user || !email || !pass || !country || !birth) {
        setMsg('msg-signup', _t('fill_all_fields'));
        return;
    }
    if (!/^[A-Za-z0-9_]{3,20}$/.test(user)) {
        setMsg('msg-signup', _t('invalid_username'));
        return;
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        setMsg('msg-signup', _t('invalid_email'));
        return;
    }
    if (pass.length < 6) {
        setMsg('msg-signup', _t('invalid_password'));
        return;
    }

    setMsg('msg-signup', _t('sending_code') + '...', true);
    temporalRegistrationData = { username: user, email: email, password: pass, country: country, birthdate: birth };

    fetch('/auth/solicitar_codigo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, email: email, password: pass })
    }).then(res => res.json()).then(datos => {
        if (datos.exito) {
            setMsg('msg-signup', datos.mensaje || _t('code_sent'), true);
            setTimeout(() => {
                mostrarModalAuth('modal-verify');
                setMsg('msg-verify', '');
                document.getElementById('verify-code').value = '';
                document.getElementById('verify-code').focus();
            }, 800);
        } else {
            setMsg('msg-signup', datos.mensaje);
        }
    }).catch(() => setMsg('msg-signup', _t('network_error')));
});

// ==========================================
// 3. Registro — Paso 2: verificar código y crear cuenta
// ==========================================
document.getElementById('btn-submit-verify')?.addEventListener('click', () => {
    const code = document.getElementById('verify-code').value.trim();

    if (!code || code.length < 6) {
        setMsg('msg-verify', _t('enter_full_code'));
        return;
    }
    if (!temporalRegistrationData) {
        setMsg('msg-verify', _t('session_expired'));
        return;
    }

    setMsg('msg-verify', _t('verifying') + '...', true);
    temporalRegistrationData.code = code;

    fetch('/auth/registro', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(temporalRegistrationData)
    }).then(res => res.json()).then(datos => {
        if (datos.exito) {
            setMsg('msg-verify', _t('account_created'), true);
            setTimeout(() => window.location.reload(), 1200); // Recargar loguea automáticamente
        } else {
            setMsg('msg-verify', datos.mensaje);
        }
    }).catch(() => setMsg('msg-verify', _t('network_error')));
});

// ==========================================
// 4. Inicio de sesión (usuario o correo)
// ==========================================
document.getElementById('btn-submit-login')?.addEventListener('click', () => {
    const user = document.getElementById('login-user').value.trim();
    const pass = document.getElementById('login-pass').value;
    const remember = document.getElementById('login-remember').checked;

    if (!user || !pass) {
        setMsg('msg-login', _t('enter_user_pass'));
        return;
    }

    setMsg('msg-login', _t('checking') + '...', true);

    fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pass, remember: remember })
    }).then(res => res.json()).then(datos => {
        if (datos.exito) {
            window.location.reload();
        } else {
            setMsg('msg-login', datos.mensaje);
        }
    }).catch(() => setMsg('msg-login', _t('network_error')));
});

// Enter para enviar el login rápido
document.getElementById('login-pass')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') document.getElementById('btn-submit-login').click();
});

// ==========================================
// 5. Cerrar sesión
// ==========================================
document.getElementById('btn-logout')?.addEventListener('click', () => {
    fetch('/auth/logout', { method: 'POST', cache: 'no-store', credentials: 'same-origin' })
        .then(() => {
            // Pintamos la salida ANTES de recargar: si la recarga tarda (o falla),
            // en ningún momento se ve una pantalla que dice que sigues dentro.
            usuarioActual = null;
            miUsernameLogueado = null;
            actualizarInterfazDeslogueado();
            localStorage.removeItem('callmus_sala');
            localStorage.removeItem('callmus_token');
            window.location.reload();
        })
        .catch(() => setMsg('msg-login', _t('err_red')));
});

// ==========================================
// 6. Recuperación de contraseña
// ==========================================
document.getElementById('link-forgot')?.addEventListener('click', (e) => {
    e.preventDefault();
    mostrarModalAuth('modal-forgot');
    setMsg('msg-forgot', '');
    document.getElementById('forgot-email').value = document.getElementById('login-user').value.trim();
});

// Paso 1: pedir el código
document.getElementById('btn-submit-forgot')?.addEventListener('click', () => {
    const email = document.getElementById('forgot-email').value.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        setMsg('msg-forgot', _t('invalid_email'));
        return;
    }

    setMsg('msg-forgot', _t('sending_code') + '...', true);
    fetch('/auth/solicitar_reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
    }).then(res => res.json()).then(datos => {
        if (datos.exito) {
            resetEmail = email;
            setMsg('msg-forgot', datos.mensaje, true);
            setTimeout(() => {
                mostrarModalAuth('modal-reset');
                setMsg('msg-reset', '');
                document.getElementById('reset-code').value = '';
                document.getElementById('reset-pass').value = '';
                document.getElementById('reset-code').focus();
            }, 1000);
        } else {
            setMsg('msg-forgot', datos.mensaje);
        }
    }).catch(() => setMsg('msg-forgot', _t('network_error')));
});

// Paso 2: código + nueva contraseña
document.getElementById('btn-submit-reset')?.addEventListener('click', () => {
    const code = document.getElementById('reset-code').value.trim();
    const pass = document.getElementById('reset-pass').value;

    if (!code || code.length < 6) {
        setMsg('msg-reset', _t('enter_full_code'));
        return;
    }
    if (pass.length < 6) {
        setMsg('msg-reset', _t('invalid_password'));
        return;
    }

    setMsg('msg-reset', _t('saving') + '...', true);
    fetch('/auth/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: resetEmail, code: code, password: pass })
    }).then(res => res.json()).then(datos => {
        if (datos.exito) {
            setMsg('msg-reset', datos.mensaje, true);
            setTimeout(() => {
                mostrarModalAuth('modal-login');
                setMsg('msg-login', _t('password_changed'), true);
                document.getElementById('login-user').value = resetEmail;
            }, 1500);
        } else {
            setMsg('msg-reset', datos.mensaje);
        }
    }).catch(() => setMsg('msg-reset', _t('network_error')));
});

// ==========================================
// 7. Botones de Google (OAuth) — la lógica ocurre en el backend
// ==========================================
// El botón de registrarse es el ÚNICO que puede crear una cuenta nueva; el de entrar
// solo inicia sesión (si no hay cuenta, el servidor devuelve auth_error=google_sin_cuenta).
document.getElementById('btn-google-signup')?.addEventListener('click', () => {
    window.location.href = '/auth/google/login?intent=signup';
});
document.getElementById('btn-google-login')?.addEventListener('click', () => {
    window.location.href = '/auth/google/login?intent=login';
});
