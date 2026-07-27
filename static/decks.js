// ==========================================================================
// decks.js — Barajas temáticas y ventana «Mis barajas» (Roadmap #5)
// --------------------------------------------------------------------------
// La piel de las cartas es cosa del cliente. El servidor sigue mandando la
// identidad lógica de cada carta (`valor`, `palo`) y su `img` de siempre; aquí
// se traduce a la imagen del tema que el jugador haya puesto en ese hueco de
// palo. Si algo falla — todavía no ha llegado el catálogo, el tema ya no
// existe, no hay red — se devuelve la `img` del servidor y se juega igual.
//
// La piel la elige el DUEÑO de la carta: tú ves las del rival con la baraja del
// rival y él ve las tuyas con la tuya. Por eso la elección sí viaja: se anuncia
// con `mi_baraja` y el servidor la devuelve en el estado de la mesa (2p:
// `baraja_rival`; 2v2: `seats[].baraja`). Las funciones de ruta aceptan esa
// configuración ajena como segundo argumento; sin ella pintan con la propia.
//
// Se carga después de app.js (usa `dict`, `t`, `aplicarTraduccion`,
// `abrirModal`, `cerrarModales`, `socket`) y antes de menu.js.
// ==========================================================================

(function () {
    'use strict';

    const $ = (id) => document.getElementById(id);

    // ======================================================================
    // 1. i18n
    // ======================================================================
    Object.assign(dict.es, {
        decks_titulo: 'Mis barajas',
        decks_sub: 'Elige un tema para cada palo. En el mus el palo no puntúa, así que puedes mezclarlos.',
        decks_hueco_coins: 'Oros',
        decks_hueco_cups: 'Copas',
        decks_hueco_swords: 'Espadas',
        decks_hueco_clubs: 'Bastos',
        decks_hueco_dorso: 'Dorso',
        decks_elige: 'Tema para <b>{hueco}</b>',
        decks_todos_palos: 'Poner en los cuatro palos',
        decks_restablecer: 'Volver a la baraja clásica',
        decks_bloqueo_cuenta: 'Necesitas una cuenta',
        decks_bloqueo_restringido: 'Todavía no lo tienes',
        decks_guardado: 'Baraja guardada.',
        decks_guardado_local: 'Guardada en este navegador. Crea una cuenta para llevártela a otros dispositivos.',
        decks_error: 'No se ha podido guardar la baraja.',
        decks_vacio: 'Todavía no hay temas disponibles.',
        decks_desbloqueada: 'Nueva baraja disponible: {nombre}',
        decks_clasica: 'Clásica',
    });
    Object.assign(dict.en, {
        decks_titulo: 'My decks',
        decks_sub: 'Pick a theme for each suit. Suits don\'t score in mus, so you can mix them freely.',
        decks_hueco_coins: 'Coins',
        decks_hueco_cups: 'Cups',
        decks_hueco_swords: 'Swords',
        decks_hueco_clubs: 'Clubs',
        decks_hueco_dorso: 'Card back',
        decks_elige: 'Theme for <b>{hueco}</b>',
        decks_todos_palos: 'Use for all four suits',
        decks_restablecer: 'Back to the classic deck',
        decks_bloqueo_cuenta: 'You need an account',
        decks_bloqueo_restringido: 'You don\'t have this one yet',
        decks_guardado: 'Deck saved.',
        decks_guardado_local: 'Saved in this browser. Create an account to take it to other devices.',
        decks_error: 'The deck could not be saved.',
        decks_vacio: 'No themes available yet.',
        decks_desbloqueada: 'New deck available: {nombre}',
        decks_clasica: 'Classic',
    });
    Object.assign(dict.eu, {
        decks_titulo: 'Nire karta-sortak',
        decks_sub: 'Aukeratu gai bat palo bakoitzarentzat. Musean paloak ez du punturik ematen, beraz nahas ditzakezu.',
        decks_hueco_coins: 'Urreak',
        decks_hueco_cups: 'Kopak',
        decks_hueco_swords: 'Ezpatak',
        decks_hueco_clubs: 'Bastoiak',
        decks_hueco_dorso: 'Atzealdea',
        decks_elige: '<b>{hueco}</b> palorako gaia',
        decks_todos_palos: 'Lau paloetan jarri',
        decks_restablecer: 'Karta-sorta klasikora itzuli',
        decks_bloqueo_cuenta: 'Kontu bat behar duzu',
        decks_bloqueo_restringido: 'Oraindik ez daukazu',
        decks_guardado: 'Karta-sorta gordeta.',
        decks_guardado_local: 'Nabigatzaile honetan gordeta. Sortu kontu bat beste gailu batzuetara eramateko.',
        decks_error: 'Ezin izan da karta-sorta gorde.',
        decks_vacio: 'Oraindik ez dago gairik eskuragarri.',
        decks_desbloqueada: 'Karta-sorta berria eskuragarri: {nombre}',
        decks_clasica: 'Klasikoa',
    });

    // ======================================================================
    // 2. Estado
    // ======================================================================

    // El palo viaja en castellano desde el servidor; los huecos son claves
    // estables en inglés porque son también nombres de carpeta.
    const HUECO_DE_PALO = {
        'Oros': 'coins', 'Copas': 'cups', 'Espadas': 'swords', 'Bastos': 'clubs',
        'coins': 'coins', 'cups': 'cups', 'swords': 'swords', 'clubs': 'clubs',
    };
    const HUECOS = ['coins', 'cups', 'swords', 'clubs'];
    const CLAVES = HUECOS.concat(['dorso']);
    const DEFECTO = { coins: 'coins', cups: 'cups', swords: 'swords', clubs: 'clubs', dorso: 'coins' };
    const LLAVE_LOCAL = 'callmus_baraja';

    let temas = [];                 // catálogo tal cual lo manda el servidor
    let porSlug = {};
    let config = Object.assign({}, DEFECTO);
    let logueado = false;
    let huecoEditando = 'coins';
    let cargado = false;

    function leerLocal() {
        try {
            const bruto = JSON.parse(localStorage.getItem(LLAVE_LOCAL) || 'null');
            return (bruto && typeof bruto === 'object') ? bruto : null;
        } catch (e) { return null; }
    }

    function guardarLocal() {
        try { localStorage.setItem(LLAVE_LOCAL, JSON.stringify(config)); } catch (e) { /* modo privado */ }
    }

    /** Deja la configuración en algo pintable: sólo huecos conocidos y sólo
     *  temas que existan y que este jugador pueda usar. Espejo de
     *  `decks.normalizar_config` en el servidor, que es quien manda. */
    function normalizar(bruto) {
        const limpia = Object.assign({}, DEFECTO);
        if (!bruto || typeof bruto !== 'object') return limpia;
        CLAVES.forEach(hueco => {
            const slug = bruto[hueco];
            const tema = porSlug[slug];
            if (tema && !tema.bloqueado) limpia[hueco] = slug;
        });
        return limpia;
    }

    // ======================================================================
    // 3. Resolución de rutas — lo que usa la mesa
    // ======================================================================

    function dosDigitos(valor) {
        const n = parseInt(valor, 10);
        return (n < 10 ? '0' : '') + n;
    }

    // Una baraja ajena ya viene validada por el servidor contra los temas que su
    // dueño puede usar, así que aquí no se mira `bloqueado`: que tú no tengas un
    // tema no quita que el rival lo tenga y sea con el que juega.
    const CLASICO = '/static/img/card_back.webp';

    /** Imagen de la cara de una carta. `carta` es el objeto del servidor;
     *  `ajena`, la configuración de su dueño si la carta no es tuya. */
    function rutaCarta(carta, ajena) {
        if (!carta) return CLASICO;
        const cual = ajena || config;
        const tema = porSlug[cual[HUECO_DE_PALO[carta.palo]] || ''];
        if (!tema || (!ajena && tema.bloqueado)) return carta.img || CLASICO;
        return tema.cartas[dosDigitos(carta.valor)] || carta.img || CLASICO;
    }

    /** Imagen del dorso. Es una sola para toda la baraja. */
    function rutaDorso(ajena) {
        const cual = ajena || config;
        const tema = porSlug[cual.dorso];
        if (!tema || (!ajena && tema.bloqueado)) return CLASICO;
        return tema.dorso || CLASICO;
    }

    /** Baja en segundo plano las 41 imágenes de una baraja.
     *
     *  La propia se baja entera y ya: se ve en cuanto reparten. De una ajena
     *  corre prisa sólo el dorso, que está en la mesa toda la mano; las caras
     *  no se ven hasta el recuento, así que se dejan para cuando el navegador
     *  no tenga nada mejor que hacer (con tres rivales serían 120 imágenes
     *  compitiendo con la partida). */
    function precargarBaraja(cual, ajena) {
        const dorso = new Image();
        dorso.src = rutaDorso(ajena ? cual : undefined);

        const caras = [];
        HUECOS.forEach(hueco => {
            const tema = porSlug[(cual || {})[hueco]];
            if (tema) Object.values(tema.cartas).forEach(r => caras.push(r));
        });
        const bajar = () => caras.forEach(ruta => { const img = new Image(); img.src = ruta; });

        if (!ajena) { bajar(); return; }
        if (window.requestIdleCallback) requestIdleCallback(bajar, { timeout: 8000 });
        else setTimeout(bajar, 5000);
    }

    /** La propia. Se llama al cargar el catálogo y al cambiar de baraja. */
    function precargar() {
        precargarBaraja(config, false);
    }

    /** La de otro jugador, según llega en el estado de la mesa. Sin catálogo no
     *  hay nada que bajar: se pinta la clásica y ya se precargará al llegar.
     *
     *  La baraja ajena viene en CADA estado de la mesa (y en el 2v2, una por
     *  rival), así que se lleva cuenta de las ya pedidas: si no, cada envite
     *  encolaría otras 120 imágenes. */
    const ajenasPedidas = new Set();

    function precargarAjena(cual) {
        if (!cual || !cargado) return;
        const firma = CLAVES.map(hueco => cual[hueco] || '').join('|');
        if (ajenasPedidas.has(firma)) return;
        ajenasPedidas.add(firma);
        precargarBaraja(cual, true);
    }

    // ======================================================================
    // 3 bis. Anunciar la propia
    // ----------------------------------------------------------------------
    // El servidor la necesita para poder enseñársela a los demás, y no le vale
    // con mirar la base de datos: un invitado sólo la tiene en su navegador.
    // Se manda al cargar el catálogo, al guardar y en cada reconexión (el
    // registro del servidor va por socket y un socket nuevo empieza en blanco).
    // ======================================================================

    function anunciar() {
        if (typeof socket === 'undefined' || !socket.emit) return;
        socket.emit('mi_baraja', { config: config });
    }

    // ======================================================================
    // 4. Catálogo
    // ======================================================================

    async function cargar() {
        let datos = null;
        try {
            // El catálogo sólo tiene nombre en castellano y en inglés (dos
            // columnas en la base de datos): en euskera se piden en castellano
            // hasta que los temas tengan su propio nombre.
            const idioma = (typeof langActual !== 'undefined' && langActual === 'en') ? 'en' : 'es';
            const res = await fetch('/api/decks?lang=' + idioma,
                                    { credentials: 'same-origin', cache: 'no-store' });
            datos = await res.json();
        } catch (e) { /* sin red: nos quedamos con la baraja clásica */ }

        if (!datos || !datos.exito) { cargado = true; return; }

        temas = datos.temas || [];
        porSlug = {};
        temas.forEach(tema => { porSlug[tema.slug] = tema; });
        logueado = !!datos.logueado;

        // Con cuenta manda lo guardado en el servidor (y así la baraja te sigue
        // de un dispositivo a otro); sin ella, lo que haya en este navegador.
        config = normalizar(logueado ? datos.config : leerLocal());
        cargado = true;
        precargar();
        anunciar();
        if (estaAbierto()) pintar();
    }

    // ======================================================================
    // 5. Guardar
    // ======================================================================

    let avisoTimer = null;

    function mensaje(texto, malo) {
        const caja = $('decks-msg');
        if (!caja) return;
        caja.textContent = texto;
        caja.classList.toggle('is-mal', !!malo);
        clearTimeout(avisoTimer);
        avisoTimer = setTimeout(() => { caja.textContent = ''; }, 4000);
    }

    async function guardar() {
        guardarLocal();          // siempre, también con cuenta: sirve de caché
        precargar();
        anunciar();              // si estás jugando, la mesa lo ve al momento
        if (!logueado) { mensaje(t('decks_guardado_local')); return; }
        try {
            const res = await fetch('/api/deck', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ config: config })
            });
            const datos = await res.json();
            if (datos && datos.exito) {
                config = normalizar(datos.config);   // el servidor tiene la última palabra
                mensaje(t('decks_guardado'));
                pintar();
            } else {
                mensaje(t('decks_error'), true);
            }
        } catch (e) {
            mensaje(t('decks_error'), true);
        }
    }

    // ======================================================================
    // 6. La ventana
    // ======================================================================

    function estaAbierto() {
        const m = $('modal-decks');
        return m && !m.classList.contains('hidden');
    }

    function nombreHueco(hueco) {
        return t('decks_hueco_' + hueco);
    }

    /** El catálogo trae los dos nombres, así que cambiar de idioma con la
     *  ventana abierta no necesita volver a preguntar al servidor. En euskera
     *  se enseña el nombre en castellano: los temas no tienen nombre propio. */
    function nombreTema(tema) {
        if (!tema) return '—';
        return (langActual === 'en' ? tema.nombre_en : tema.nombre_es) || tema.nombre;
    }

    /** Cabecera: la baraja montada, un as por palo más el dorso. Es el único
     *  sitio donde se ve de golpe si la mezcla funciona (DECK_SPEC §7). */
    function pintarResumen() {
        const caja = $('decks-resumen');
        caja.replaceChildren();
        CLAVES.forEach(hueco => {
            const tema = porSlug[config[hueco]];
            const boton = document.createElement('button');
            boton.className = 'deck-slot' + (hueco === huecoEditando ? ' is-on' : '');
            boton.type = 'button';

            const img = document.createElement('img');
            img.src = hueco === 'dorso'
                ? (tema ? tema.dorso : '/static/img/card_back.webp')
                : (tema ? tema.cartas['01'] : '/static/img/card_back.webp');
            img.alt = '';
            img.draggable = false;

            const et = document.createElement('span');
            et.className = 'deck-slot-et';
            et.textContent = nombreHueco(hueco);

            const sub = document.createElement('small');
            sub.textContent = nombreTema(tema);

            boton.append(img, et, sub);
            boton.addEventListener('click', () => { huecoEditando = hueco; pintar(); });
            caja.appendChild(boton);
        });
    }

    /** Rejilla de temas para el hueco que se está editando. */
    function pintarCatalogo() {
        const caja = $('decks-catalogo');
        caja.replaceChildren();
        if (!temas.length) {
            const p = document.createElement('p');
            p.className = 'cm-msg';
            p.textContent = t('decks_vacio');
            caja.appendChild(p);
            return;
        }
        temas.forEach(tema => {
            const boton = document.createElement('button');
            boton.type = 'button';
            boton.className = 'deck-opt'
                + (config[huecoEditando] === tema.slug ? ' is-on' : '')
                + (tema.bloqueado ? ' is-lock' : '');

            const img = document.createElement('img');
            img.src = huecoEditando === 'dorso' ? tema.dorso : tema.thumb;
            img.alt = ''; img.loading = 'lazy'; img.draggable = false;

            const nombre = document.createElement('b');
            nombre.textContent = nombreTema(tema);

            boton.append(img, nombre);

            if (tema.bloqueado) {
                const candado = document.createElement('em');
                candado.className = 'deck-lock';
                candado.textContent = tema.motivo === 'cuenta'
                    ? t('decks_bloqueo_cuenta') : t('decks_bloqueo_restringido');
                boton.appendChild(candado);
            } else if (tema.clasica) {
                const et = document.createElement('em');
                et.className = 'deck-tag';
                et.textContent = t('decks_clasica');
                boton.appendChild(et);
            }

            boton.addEventListener('click', () => {
                if (tema.bloqueado) {
                    mensaje(tema.motivo === 'cuenta'
                        ? t('decks_bloqueo_cuenta') : t('decks_bloqueo_restringido'), true);
                    return;
                }
                config[huecoEditando] = tema.slug;
                pintar();
                guardar();
            });
            caja.appendChild(boton);
        });
    }

    function pintar() {
        if (!$('modal-decks')) return;
        const rotulo = $('decks-elige');
        if (rotulo) rotulo.innerHTML = t('decks_elige').replace('{hueco}', nombreHueco(huecoEditando));
        const btnTodos = $('decks-todos-palos');
        if (btnTodos) btnTodos.classList.toggle('hidden', huecoEditando === 'dorso');
        pintarResumen();
        pintarCatalogo();
    }

    function abrir() {
        abrirModal('modal-decks');
        mensaje('');
        pintar();     // con lo que ya haya, para que la ventana no salga vacía
        cargar();     // y se repinta sola cuando llegue el catálogo fresco
    }

    // ======================================================================
    // 7. Enganches
    // ======================================================================

    document.addEventListener('DOMContentLoaded', () => {
        const btn = $('btn-decks');
        if (btn) btn.addEventListener('click', abrir);

        const btnTodos = $('decks-todos-palos');
        if (btnTodos) btnTodos.addEventListener('click', () => {
            const slug = config[huecoEditando];
            if (huecoEditando === 'dorso' || !porSlug[slug]) return;
            HUECOS.forEach(hueco => { config[hueco] = slug; });
            pintar();
            guardar();
        });

        const btnReset = $('decks-restablecer');
        if (btnReset) btnReset.addEventListener('click', () => {
            config = Object.assign({}, DEFECTO);
            pintar();
            guardar();
        });

        cargar();
    });

    if (typeof socket !== 'undefined' && socket.on) {
        // El registro del servidor va por socket, así que un socket nuevo (o
        // recuperado tras una caída) no sabe con qué baraja juegas: se le dice.
        socket.on('connect', anunciar);

        // Un administrador acaba de darle acceso a un tema: el catálogo se
        // refresca solo, sin que el jugador tenga que recargar la página.
        socket.on('baraja_desbloqueada', (datos) => {
            cargar();
            const caja = $('menu-msg');
            if (caja && datos && datos.nombre) {
                caja.innerText = t('decks_desbloqueada').replace('{nombre}', datos.nombre);
            }
        });
    }

    // ======================================================================
    // 8. API pública — la usan app.js (1v1) y table4.js (2v2)
    // ======================================================================
    window.Barajas = {
        rutaCarta: rutaCarta,          // (carta[, baraja ajena])
        rutaDorso: rutaDorso,          // ([baraja ajena])
        precargar: precargar,
        precargarAjena: precargarAjena,
        recargar: cargar,
        anunciar: anunciar,
        abrir: abrir,
        get config() { return Object.assign({}, config); },
    };
})();
