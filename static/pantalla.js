// pantalla.js — Pantalla completa y «modo mesa».
//
// Se carga el último: reutiliza los globales de app.js (`dict`, `t`,
// `aplicarTraduccion`) y sólo mira el DOM, no habla con el servidor.
//
// De qué va. En el móvil, deslizar el dedo sobre la mesa es un MANDO del juego
// (las señas del 2v2 giran la cabeza con el deslizamiento). El navegador, sin
// embargo, entiende ese mismo gesto como suyo: mueve la página, rebota o tira
// para recargar. A pantalla completa eso no pasa, y de ahí venía el «con
// fullscreen se juega bien». Aquí se arregla por los dos lados:
//
//   1. MODO MESA — mientras se ve un tapete (#game-screen o #game-screen-4) el
//      documento se congela (body fijo, sin desbordamiento, sin rebote) y se
//      cancela cualquier deslizamiento que no caiga dentro de algo que de
//      verdad se pueda desplazar. Se juega igual de bien SIN pantalla completa.
//   2. PANTALLA COMPLETA — un único sitio con la API y sus prefijos, entrada
//      automática al empezar la partida (si el administrador la deja puesta con
//      `pantalla_completa_auto`) y salida siempre a mano con el botón ⛶.
//
// El iPhone es el caso raro: Safari NO tiene la API de pantalla completa fuera
// de los vídeos, así que ahí el botón no puede funcionar por mucho que se
// insista. Lo único que da pantalla completa de verdad es añadir la web a la
// pantalla de inicio, y eso es lo que explica la ventanita de ayuda.

(function () {
    'use strict';

    // ======================================================================
    // 1. i18n
    // ======================================================================
    Object.assign(dict.es, {
        fullscreen_salir_tooltip: 'Salir de pantalla completa',
        fs_ios_titulo: 'Pantalla completa en el iPhone',
        fs_ios_sub: 'Safari no deja a ninguna web ponerse a pantalla completa.',
        fs_ios_paso_t: 'Añade CallMus a la pantalla de inicio',
        fs_ios_paso_p: 'Toca <em>Compartir</em> en la barra de abajo → <em>Añadir a pantalla de inicio</em> → <em>Añadir</em>. Se abrirá desde su propio icono, sin la barra del navegador y con toda la pantalla para la mesa.',
        fs_ios_ya_t: 'Mientras tanto, puedes jugar igual',
        fs_ios_ya_p: 'La mesa ya está preparada para el dedo: deslizar sobre ella mueve la mirada y no la página, y no se recarga por tirar hacia abajo.',
        fs_ios_ok: 'Entendido',
    });
    Object.assign(dict.en, {
        fullscreen_salir_tooltip: 'Leave fullscreen',
        fs_ios_titulo: 'Fullscreen on the iPhone',
        fs_ios_sub: 'Safari does not let any website go fullscreen.',
        fs_ios_paso_t: 'Add CallMus to your home screen',
        fs_ios_paso_p: 'Tap <em>Share</em> in the bottom bar → <em>Add to Home Screen</em> → <em>Add</em>. It then opens from its own icon, with no browser bar and the whole screen for the table.',
        fs_ios_ya_t: 'You can play just fine meanwhile',
        fs_ios_ya_p: 'The table is already built for the finger: swiping on it moves your gaze, not the page, and pulling down no longer reloads.',
        fs_ios_ok: 'Got it',
    });
    Object.assign(dict.eu, {
        fullscreen_salir_tooltip: 'Pantaila osotik irten',
        fs_ios_titulo: 'Pantaila osoa iPhonean',
        fs_ios_sub: 'Safarik ez dio inolako webguneri pantaila osoan jartzen uzten.',
        fs_ios_paso_t: 'Gehitu CallMus hasierako pantailara',
        fs_ios_paso_p: 'Ukitu <em>Partekatu</em> beheko barran → <em>Gehitu hasierako pantailara</em> → <em>Gehitu</em>. Bere ikono propiotik irekiko da, nabigatzailearen barrarik gabe eta pantaila osoa mahaiarentzat.',
        fs_ios_ya_t: 'Bitartean, berdin jokatu dezakezu',
        fs_ios_ya_p: 'Mahaia hatzarentzat prestatuta dago: gainean irristatzeak begirada mugitzen du, ez orria, eta ez da birkargatzen behera tiratzeagatik.',
        fs_ios_ok: 'Ulertuta',
    });
    aplicarTraduccion();

    const raiz = document.documentElement;
    const PANTALLAS = ['game-screen', 'game-screen-4'];

    // ======================================================================
    // 2. La API de pantalla completa (con sus prefijos)
    // ======================================================================
    const pedirFS = raiz.requestFullscreen || raiz.webkitRequestFullscreen ||
                    raiz.mozRequestFullScreen || raiz.msRequestFullscreen;
    const salirFS = document.exitFullscreen || document.webkitExitFullscreen ||
                    document.mozCancelFullScreen || document.msExitFullscreen;

    const soporta = () => !!pedirFS;
    const activa = () => !!(document.fullscreenElement || document.webkitFullscreenElement ||
                            document.mozFullScreenElement || document.msFullscreenElement);

    /** Añadida a la pantalla de inicio: ya se ve a pantalla completa y el botón
     *  sobra. `navigator.standalone` es lo de Safari; el resto usa display-mode. */
    function enApp() {
        if (window.navigator.standalone === true) return true;
        return ['standalone', 'fullscreen', 'minimal-ui'].some(
            m => window.matchMedia('(display-mode: ' + m + ')').matches);
    }

    /** iPhone/iPad: se detecta por el iPad moderno también, que se anuncia como
     *  un Mac y sólo se delata por tener pantalla táctil. */
    function esIOS() {
        const ua = navigator.userAgent || '';
        if (/iPhone|iPad|iPod/.test(ua)) return true;
        return /Macintosh/.test(ua) && navigator.maxTouchPoints > 1;
    }

    // Ni entrar ni salir son críticos: si el navegador dice que no (porque no
    // hay gesto del usuario detrás, o porque está prohibido), se sigue jugando.
    function entrar() {
        if (!pedirFS || activa()) return;
        try {
            const p = pedirFS.call(raiz);
            if (p && p.catch) p.catch(() => {});
        } catch (e) { /* sin pantalla completa, a jugar igual */ }
    }

    function salir() {
        if (!salirFS || !activa()) return;
        try {
            const p = salirFS.call(document);
            if (p && p.catch) p.catch(() => {});
        } catch (e) { /* nada que hacer */ }
    }

    // ======================================================================
    // 3. Modo mesa: el tapete se comporta como una aplicación
    // ======================================================================
    function enMesa() {
        return PANTALLAS.some(id => {
            const el = document.getElementById(id);
            return el && !el.classList.contains('hidden');
        });
    }

    function repasarModo() {
        raiz.classList.toggle('modo-mesa', enMesa());
    }

    PANTALLAS.forEach(id => {
        const el = document.getElementById(id);
        if (el) new MutationObserver(repasarModo).observe(el, {
            attributes: true, attributeFilter: ['class'],
        });
    });
    repasarModo();

    /** ¿Hay algo bajo el dedo que de verdad se pueda desplazar? El recuento del
     *  1v1, la chuleta de señas o una ventana larga sí; la mesa no. Sólo en el
     *  primer caso se le deja el gesto al navegador. */
    function desplazable(nodo) {
        for (let el = nodo; el && el.nodeType === 1 && el !== document.body; el = el.parentElement) {
            const est = getComputedStyle(el);
            if (/(auto|scroll)/.test(est.overflowY) && el.scrollHeight > el.clientHeight + 1) return true;
            if (/(auto|scroll)/.test(est.overflowX) && el.scrollWidth > el.clientWidth + 1) return true;
        }
        return false;
    }

    // NO pasivo a propósito: es el único modo de poder cancelar el gesto del
    // navegador (mover la página, el rebote de iOS, tirar para recargar).
    document.addEventListener('touchmove', (e) => {
        if (!raiz.classList.contains('modo-mesa')) return;
        if (e.touches.length > 1) return;              // pellizco: se respeta
        if (desplazable(e.target)) return;
        if (e.cancelable) e.preventDefault();
    }, { passive: false });

    // ======================================================================
    // 4. El botón ⛶
    // ======================================================================
    const btn = document.getElementById('btn-fullscreen');

    function pintarBoton() {
        if (!btn) return;
        // Ya abierta desde el icono de la pantalla de inicio: no hay nada que
        // pedir, la barra del navegador ni siquiera existe.
        btn.classList.toggle('hidden', enApp());
        const dentro = activa();
        btn.classList.toggle('activa', dentro);
        btn.setAttribute('aria-pressed', dentro ? 'true' : 'false');
        btn.setAttribute('data-i18n-title', dentro ? 'fullscreen_salir_tooltip' : 'fullscreen_tooltip');
        btn.title = t(dentro ? 'fullscreen_salir_tooltip' : 'fullscreen_tooltip');
    }

    if (btn) {
        btn.addEventListener('click', () => {
            if (enApp()) { pintarBoton(); return; }
            if (!soporta()) { abrirAyudaFS(); return; }   // iPhone
            activa() ? salir() : entrar();
        });
    }

    ['fullscreenchange', 'webkitfullscreenchange'].forEach(ev =>
        document.addEventListener(ev, pintarBoton));
    // El idioma se cambia desde Ajustes: el título del botón lo pone este
    // archivo, así que hay que repasarlo cuando cambie.
    const btnLang = document.getElementById('btn-lang');
    if (btnLang) btnLang.addEventListener('click', () => setTimeout(pintarBoton, 0));
    pintarBoton();

    // ======================================================================
    // 5. Entrada automática al empezar la partida
    // ======================================================================
    // La API exige un gesto del usuario, y la partida no arranca con un clic
    // sino con un aviso del servidor (`iniciar_partida`), que llega mucho
    // después. Así que se pide en el clic que la pone en marcha: crear, unirse
    // o jugar contra la IA. El que crea la sala no vuelve a tocar nada hasta
    // que entra el rival, y por eso su botón también cuenta.
    const ARRANQUES = ['#btn-crear', '#btn-jugar-bot', '#btn-unirse',
                       '#btn-crear-sala-4', '#btn-unirse-4',
                       '.btn-unirse-publica', '.btn-unirse-publica-4'].join(',');

    // El administrador la puede apagar (`pantalla_completa_auto`). Si la
    // plantilla no la inyecta —abrir el HTML suelto, por ejemplo—, va puesta.
    const autoPuesta = () => window.CM_AUTO_FULLSCREEN !== false;

    const escrito = (id) => {
        const el = document.getElementById(id);
        return !!(el && el.value && el.value.trim());
    };

    /** Antes de pedirla hay que estar razonablemente seguro de que la partida va
     *  a arrancar: si falta el nombre o el código, el clic sólo saca un aviso y
     *  se queda en el menú, y verlo a pantalla completa parecería una avería. */
    function arranqueValido(b) {
        const bloque = document.getElementById('play-nombre');   // sólo invitados
        if (bloque && !bloque.classList.contains('hidden') && !escrito('nombre-jugador')) return false;
        if (b.id === 'btn-unirse') return escrito('in-codigo');
        if (b.id === 'btn-unirse-4') return escrito('in-codigo-4');
        return true;
    }

    document.addEventListener('click', (e) => {
        if (!autoPuesta() || !soporta() || activa() || enApp()) return;
        const b = e.target && e.target.closest && e.target.closest(ARRANQUES);
        if (!b || b.disabled || !arranqueValido(b)) return;
        entrar();
    }, true);

    // ======================================================================
    // 6. La ayuda del iPhone
    // ======================================================================
    let ayudaEl = null, ayudaVelo = null;

    function montarAyudaFS() {
        if (ayudaEl) return;
        ayudaVelo = document.createElement('div');
        ayudaVelo.className = 'cm-ayuda-velo';
        ayudaVelo.addEventListener('click', cerrarAyudaFS);
        document.body.appendChild(ayudaVelo);

        ayudaEl = document.createElement('div');
        ayudaEl.className = 'cm-ayuda';
        ayudaEl.setAttribute('role', 'dialog');
        document.body.appendChild(ayudaEl);
    }

    function pintarAyudaFS() {
        // Sin data-i18n: se repinta entera cada vez que se abre, que es cuando
        // se sabe el idioma de ese momento (mismo apaño que la ayuda de señas).
        ayudaEl.innerHTML = `
            <h3>${t('fs_ios_titulo')}</h3>
            <p class="cm-ayuda-sub">${t('fs_ios_sub')}</p>
            <div class="cm-ayuda-bloque">
                <b>${t('fs_ios_paso_t')}</b>
                <p>${t('fs_ios_paso_p')}</p>
            </div>
            <div class="cm-ayuda-bloque">
                <b>${t('fs_ios_ya_t')}</b>
                <p>${t('fs_ios_ya_p')}</p>
            </div>
            <div class="cm-ayuda-pie">
                <button type="button" class="cm-ayuda-mas cm-fs-ok">${t('fs_ios_ok')}</button>
            </div>`;
        ayudaEl.querySelector('.cm-fs-ok').addEventListener('click', cerrarAyudaFS);
    }

    function abrirAyudaFS() {
        montarAyudaFS();
        pintarAyudaFS();
        ayudaEl.classList.add('abierta');
        ayudaVelo.classList.add('abierto');
    }

    function cerrarAyudaFS() {
        if (ayudaEl) ayudaEl.classList.remove('abierta');
        if (ayudaVelo) ayudaVelo.classList.remove('abierto');
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && ayudaEl && ayudaEl.classList.contains('abierta')) cerrarAyudaFS();
    });

    // `ayuda` la abre el botón ⛶ donde no hay API; queda expuesta para poder
    // enseñarla desde cualquier otro sitio (y para verla en el escritorio).
    window.Pantalla = { entrar, salir, activa, soporta, enApp, esIOS, ayuda: abrirAyudaFS };
})();
