// menu.js — Menú principal y ventana de Jugar (#modal-play).
//
// Se carga al final: reutiliza los globales de app.js (`socket`, `dict`, `t`,
// `t_dinamico`, `aplicarTraduccion`, `cerrarModales`, `modalOverlay`) y los de
// app4.js (`renderSeatPicker4`).
//
// Reparto de responsabilidades: este archivo NO crea ni se une a partidas. Los
// campos y los botones conservan los ids de siempre (#nombre-jugador, #in-mejor-de,
// #btn-crear, #btn-jugar-bot, #btn-crear-sala-4, #in-codigo…), así que quien
// emite sigue siendo app.js / app4.js. Aquí sólo se decide qué se ve, cuándo, y
// se avisa de lo que todavía no está disponible.

(function () {
    'use strict';

    const $ = (id) => document.getElementById(id);

    // ======================================================================
    // 1. i18n — se añade al diccionario existente, no se duplica
    // ======================================================================
    Object.assign(dict.es, {
        // Menú
        menu_play: 'Jugar',
        menu_play_sub: '1 contra 1, 2 contra 2 o contra la IA',
        menu_tutorial: 'Cómo se juega',
        menu_decks: 'Mis barajas',
        menu_leaderboard: 'Clasificación',
        menu_kofi: 'Ko-fi',
        kofi_tooltip: 'Invítame un café en Ko-fi',
        menu_about: 'Acerca de CallMus',
        tag_soon: 'Pronto',
        fullscreen_tooltip: 'Pantalla completa',
        btn_amigos_tooltip: 'Amigos y grupos',
        share_copy: 'Copiar el enlace de invitación',
        share_copy_code: 'Copiar el código',
        share_more: 'Compartir…',

        // Ventana de Jugar
        play_title: 'Jugar',
        play_sub: 'Monta la partida en tres pasos',
        play_sub_espera: 'Comparte el código con quien quieras que juegue',
        play_your_name: 'Tu nombre en la mesa',
        play_como: 'Jugarás como <b>{nombre}</b>.',
        play_step_mesa: 'La mesa',
        play_step_rivales: 'Los rivales',
        play_step_ajustes: 'Los detalles',
        play_1v1: '1 contra 1',
        play_1v1_sub: 'Tú y un rival',
        play_2v2: '2 contra 2',
        play_2v2_sub: 'Por parejas, cuatro jugadores',
        play_vs_human: 'Contra personas',
        play_vs_human_sub: 'Creas la sala y compartes el código',
        play_vs_bot: 'Contra la IA',
        play_vs_bot_sub: 'Empiezas al momento, sin esperar',
        play_4_humanos: 'Cuatro personas',
        play_4_humanos_sub: 'Tu pareja y la pareja rival',
        play_4_bots: 'Con bots',
        play_4_bots_sub: 'Rellenar los asientos con la IA',
        play_4_mixto: 'Mesa mixta',
        play_4_mixto_sub: 'Personas y bots en la misma mesa',
        play_best_of: 'Al mejor de',
        play_public: 'Partida pública',
        play_public_sub: 'Cualquiera puede verla en la lista y unirse',
        play_senas: 'Con señas',
        play_senas_sub: 'Avisar a tu pareja de lo que llevas',
        play_seat_note: 'Los asientos 0 y 2 son el equipo A; el 1 y el 3, el equipo B. Tu pareja se sienta enfrente de ti.',
        play_create: 'Crear la partida',
        play_start_bot: 'Empezar contra la IA',
        play_join_title: '…o únete a una partida',
        play_join_btn: 'Unirse',
        play_live_title: 'Abiertas ahora mismo',
        play_live_loading: 'Buscando partidas…',

        // Resumen bajo el botón de crear
        sum_vs_bot: 'contra la IA',
        sum_vs_human: 'contra otra persona',
        sum_vs_humans: 'entre cuatro personas',
        sum_vs_bots_4: 'con la mesa llena de bots',
        sum_vs_mixto_4: 'con personas y bots',
        sum_best_of: 'al mejor de <b>{n}</b>',
        sum_publica: 'pública',
        sum_privada: 'privada',

        // Listas en vivo
        live_mejor_de: 'Al mejor de {n}',
        live_asientos: '{n} de 4 asientos',

        // Avisos del menú que antes estaban escritos a mano en app.js
        msg_creando_sala: 'Creando la sala…',
        msg_escribe_codigo: 'Escribe primero un código de sala.',
        msg_conectando: 'Conectando…',
        msg_reconectando: 'Reconectando a tu partida automáticamente…',

        // Avisos de "todavía no"
        pronto_barajas: 'El menú de barajas aún no está disponible: llegará con las barajas personalizadas.',
        pronto_generico: 'Esta función todavía no está disponible.',

        // Clasificación
        lb_title: 'Clasificación',
        lb_sub: 'Toca un nombre para ver su código de jugador',
        lb_player: 'Jugador',
        lb_elo: 'ELO',
        lb_wins: 'Victorias',
        lb_winrate: '%',
        lb_vacia: 'Todavía no hay jugadores clasificados.',
    });

    Object.assign(dict.en, {
        menu_play: 'Play',
        menu_play_sub: '1 vs 1, 2 vs 2 or against the AI',
        menu_tutorial: 'How to play',
        menu_decks: 'My decks',
        menu_leaderboard: 'Leaderboard',
        menu_kofi: 'Ko-fi',
        kofi_tooltip: 'Buy me a coffee on Ko-fi',
        menu_about: 'About CallMus',
        tag_soon: 'Soon',
        fullscreen_tooltip: 'Fullscreen',
        btn_amigos_tooltip: 'Friends and groups',
        share_copy: 'Copy the invite link',
        share_copy_code: 'Copy the code',
        share_more: 'Share…',

        play_title: 'Play',
        play_sub: 'Set up your game in three steps',
        play_sub_espera: 'Share the code with whoever you want to play with',
        play_your_name: 'Your name at the table',
        play_como: 'You will play as <b>{nombre}</b>.',
        play_step_mesa: 'The table',
        play_step_rivales: 'The opponents',
        play_step_ajustes: 'The details',
        play_1v1: '1 vs 1',
        play_1v1_sub: 'You and one opponent',
        play_2v2: '2 vs 2',
        play_2v2_sub: 'Partners, four players',
        play_vs_human: 'Against people',
        play_vs_human_sub: 'You create the room and share the code',
        play_vs_bot: 'Against the AI',
        play_vs_bot_sub: 'Start right away, no waiting',
        play_4_humanos: 'Four people',
        play_4_humanos_sub: 'Your partner and the rival pair',
        play_4_bots: 'With bots',
        play_4_bots_sub: 'Fill the empty seats with the AI',
        play_4_mixto: 'Mixed table',
        play_4_mixto_sub: 'People and bots at the same table',
        play_best_of: 'Best of',
        play_public: 'Public game',
        play_public_sub: 'Anyone can see it in the list and join',
        play_senas: 'With signs',
        play_senas_sub: 'Signal your partner what you are holding',
        play_seat_note: 'Seats 0 and 2 are team A; seats 1 and 3, team B. Your partner sits across the table.',
        play_create: 'Create the game',
        play_start_bot: 'Start against the AI',
        play_join_title: '…or join a game',
        play_join_btn: 'Join',
        play_live_title: 'Open right now',
        play_live_loading: 'Looking for games…',

        sum_vs_bot: 'against the AI',
        sum_vs_human: 'against another person',
        sum_vs_humans: 'between four people',
        sum_vs_bots_4: 'with a table full of bots',
        sum_vs_mixto_4: 'with people and bots',
        sum_best_of: 'best of <b>{n}</b>',
        sum_publica: 'public',
        sum_privada: 'private',

        live_mejor_de: 'Best of {n}',
        live_asientos: '{n} of 4 seats',

        msg_creando_sala: 'Creating the room…',
        msg_escribe_codigo: 'Type a room code first.',
        msg_conectando: 'Connecting…',
        msg_reconectando: 'Reconnecting you to your game automatically…',

        pronto_barajas: 'The deck menu is not available yet: it will arrive with the custom decks.',
        pronto_generico: 'This feature is not available yet.',

        lb_title: 'Leaderboard',
        lb_sub: 'Tap a name to reveal that player’s code',
        lb_player: 'Player',
        lb_elo: 'ELO',
        lb_wins: 'Wins',
        lb_winrate: '%',
        lb_vacia: 'No ranked players yet.',
    });

    // ======================================================================
    // 2. Aviso flotante para lo que aún no existe
    // ======================================================================
    let toastEl = null;
    let toastTimer = null;

    function avisar(clave) {
        if (!toastEl) {
            toastEl = document.createElement('div');
            toastEl.className = 'cm-toast';
            document.body.appendChild(toastEl);
        }
        toastEl.textContent = t(clave);
        // Reiniciamos la animación aunque ya estuviera visible.
        toastEl.classList.remove('is-on');
        void toastEl.offsetWidth;
        toastEl.classList.add('is-on');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toastEl.classList.remove('is-on'), 4200);
    }
    window.avisarNoDisponible = avisar;

    // Cualquier elemento marcado con data-soon explica por qué no se puede usar.
    // «Mis barajas» ya existe (Roadmap #5); lo abre decks.js. Aquí sólo queda
    // el mecanismo, para lo próximo que se anuncie antes de estar terminado.
    const MOTIVOS = {};
    document.addEventListener('click', (e) => {
        const soon = e.target.closest('[data-soon]');
        if (!soon) return;
        e.preventDefault();
        e.stopPropagation();
        avisar(MOTIVOS[soon.id] || MOTIVOS[soon.dataset.rival] || 'pronto_generico');
    }, true);

    // ======================================================================
    // 3. Estado de la ventana de Jugar
    // ======================================================================
    const modalPlay = $('modal-play');
    const panelSetup = $('play-setup');

    let modo = 2;              // 2 = 1v1, 4 = 2v2
    let rival2 = 'humano';     // en 1v1: 'humano' | 'bot'
    let rival4 = 'humano';     // en 2v2: 'humano' | 'bots' | 'mixto'
    let esperandoSala = false;  // ya hay sala creada, se ve el código

    // app4.js necesita saber qué eligió el jugador para montar el payload de
    // `crear_sala_4` (qué asientos van con bot).
    window.modoRivales4 = () => rival4;

    function estaAbierta() {
        return modalPlay && !modalPlay.classList.contains('hidden');
    }

    /** Mientras se espera a que llegue gente, el subtítulo deja de explicar los
     *  pasos y pasa a decir qué hacer con el código. Lo llaman app.js y app4.js. */
    function marcarEspera(valor) {
        esperandoSala = !!valor;
        const sub = document.querySelector('#modal-play .cm-win-sub');
        if (sub) sub.innerText = t(esperandoSala ? 'play_sub_espera' : 'play_sub');
    }
    window.marcarEsperaPlay = marcarEspera;

    /** Muestra u oculta según el modo y los rivales elegidos. */
    function pintarPlay() {
        const es4 = modo === 4;
        const contraBot = !es4 && rival2 === 'bot';
        // Mesa entera de bots: empieza al momento, así que no hay nada que
        // anunciar en la lista pública (igual que el 1v1 contra la IA).
        const mesaDeBots = es4 && rival4 === 'bots';
        const conBots = es4 && rival4 !== 'humano';

        document.querySelectorAll('.cm-mode').forEach(b => {
            b.classList.toggle('is-on', +b.dataset.modo === modo);
        });
        document.querySelectorAll('#play-rivals-2 .cm-opt').forEach(b => {
            b.classList.toggle('is-on', b.dataset.rival === rival2);
        });
        document.querySelectorAll('#play-rivals-4 .cm-opt').forEach(b => {
            b.classList.toggle('is-on', b.dataset.rival === rival4);
        });

        // Bloques por modo
        alternar('play-rivals-2', !es4);
        alternar('play-rivals-4', es4);
        alternar('set-mejor-2', !es4);
        alternar('set-mejor-4', es4);
        alternar('set-publico-2', !es4 && !contraBot);
        alternar('set-publico-4', es4 && !mesaDeBots);
        alternar('set-senas', es4);          // las señas son cosa del 2v2
        alternar('set-asiento', es4);
        alternar('set-bots-4', conBots);
        alternar('join-2', !es4);
        alternar('join-4', es4);
        alternar('live-2', !es4);
        alternar('live-4', es4);

        // Sólo se ve el botón que corresponde
        alternar('btn-crear', !es4 && !contraBot);
        alternar('btn-jugar-bot', contraBot);
        alternar('btn-crear-sala-4', es4);

        if (es4 && typeof renderSeatPicker4 === 'function') renderSeatPicker4();
        if (conBots && typeof renderBotPicker4 === 'function') renderBotPicker4(rival4);
        pintarResumen();
        pedirPublicas();
    }

    function alternar(id, visible) {
        const el = $(id);
        if (el) el.classList.toggle('hidden', !visible);
    }

    /** Línea de resumen: "1 contra 1 · contra la IA · al mejor de 3 · pública". */
    function pintarResumen() {
        const out = $('play-summary');
        if (!out) return;
        const es4 = modo === 4;
        const contraBot = !es4 && rival2 === 'bot';
        const campo = $(es4 ? 'in-mejor-de-4' : 'in-mejor-de');
        const publico = $(es4 ? 'in-publico-4' : 'in-publico');

        let rivales;
        if (contraBot) rivales = t('sum_vs_bot');
        else if (es4 && rival4 === 'bots') rivales = t('sum_vs_bots_4');
        else if (es4 && rival4 === 'mixto') rivales = t('sum_vs_mixto_4');
        else rivales = t(es4 ? 'sum_vs_humans' : 'sum_vs_human');

        const partes = [
            t(es4 ? 'play_2v2' : 'play_1v1'),
            rivales,
            t_dinamico('sum_best_of', { n: (campo && campo.value) || 3 }),
        ];
        if (!contraBot && !(es4 && rival4 === 'bots') && publico) {
            partes.push(t(publico.checked ? 'sum_publica' : 'sum_privada'));
        }
        // Las señas cambian tanto la mesa que merecen salir en el resumen.
        const senas = $('in-senas');
        if (es4 && senas && senas.checked) partes.push(t('play_senas_on'));
        out.innerHTML = partes.join(' · ');
    }

    /** El nombre sólo se pide a los invitados; con sesión se usa el usuario. */
    function pintarIdentidad() {
        const usuario = (typeof usuarioActual !== 'undefined') ? usuarioActual : null;
        const bloque = $('play-nombre');
        const como = $('play-como');
        if (bloque) bloque.classList.toggle('hidden', !!usuario);
        if (como) {
            como.classList.toggle('hidden', !usuario);
            if (usuario) como.innerHTML = t_dinamico('play_como', { nombre: usuario.username });
        }
    }
    window.pintarIdentidadPlay = pintarIdentidad;

    // ======================================================================
    // 4. Abrir y cerrar
    // ======================================================================
    function abrirPlay(codigo) {
        cerrarModales();
        modalOverlay.style.display = 'flex';
        modalOverlay.classList.remove('hidden');
        modalPlay.classList.remove('hidden');

        // Si hay una sala esperando (creada antes de cerrar la ventana), se
        // vuelve a ver tal cual; si no, el formulario.
        const esperando1v1 = !$('codigo-creado').classList.contains('hidden');
        const esperando2v2 = !$('panel-4-espera').classList.contains('hidden');
        panelSetup.classList.toggle('hidden', esperando1v1 || esperando2v2);
        marcarEspera(esperando1v1 || esperando2v2);

        $('play-msg').innerText = '';
        pintarIdentidad();
        const nombre = $('nombre-jugador');
        if (nombre && !nombre.value) nombre.value = localStorage.getItem('callmus_nombre') || '';
        if (codigo) {
            modo = 2;
            const campo = $('in-codigo');
            if (campo) campo.value = codigo;
        }
        pintarPlay();
        arrancarSondeo();
    }
    window.abrirPlay = abrirPlay;

    const btnPlay = $('btn-play');
    if (btnPlay) btnPlay.addEventListener('click', () => abrirPlay());

    // ======================================================================
    // 5. Elecciones del jugador
    // ======================================================================
    document.querySelectorAll('.cm-mode').forEach(btn => {
        btn.addEventListener('click', () => {
            modo = +btn.dataset.modo;
            pintarPlay();
        });
    });

    document.querySelectorAll('#play-rivals-2 .cm-opt').forEach(btn => {
        btn.addEventListener('click', () => {
            rival2 = btn.dataset.rival;
            pintarPlay();
        });
    });

    document.querySelectorAll('#play-rivals-4 .cm-opt').forEach(btn => {
        btn.addEventListener('click', () => {
            rival4 = btn.dataset.rival;
            pintarPlay();
        });
    });

    // Los "+/−" del contador de partidas: siempre impares, entre 1 y 21.
    document.querySelectorAll('.cm-step-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const campo = $(btn.dataset.campo);
            if (!campo) return;
            const paso = +btn.dataset.paso;
            let v = (parseInt(campo.value, 10) || 3) + paso;
            if (v % 2 === 0) v += paso > 0 ? 1 : -1;   // por si alguien teclea un par
            campo.value = Math.min(21, Math.max(1, v));
            pintarResumen();
        });
    });
    ['in-mejor-de', 'in-mejor-de-4'].forEach(id => {
        const campo = $(id);
        if (campo) campo.addEventListener('input', pintarResumen);
    });
    ['in-publico', 'in-publico-4', 'in-senas'].forEach(id => {
        const campo = $(id);
        if (campo) campo.addEventListener('change', pintarResumen);
    });

    // El código de sala siempre en mayúsculas mientras se escribe.
    ['in-codigo', 'in-codigo-4'].forEach(id => {
        const campo = $(id);
        if (!campo) return;
        campo.addEventListener('input', () => {
            campo.value = campo.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
        });
        campo.addEventListener('keydown', (e) => {
            if (e.key !== 'Enter') return;
            const boton = $(id === 'in-codigo' ? 'btn-unirse' : 'btn-unirse-4');
            if (boton) boton.click();
        });
    });

    // ======================================================================
    // 6. Listas en vivo: sólo se sondea con la ventana abierta
    // ======================================================================
    let sondeo = null;

    function pedirPublicas() {
        if (!estaAbierta()) return;
        socket.emit(modo === 4 ? 'pedir_publicas_4' : 'pedir_publicas');
    }

    function arrancarSondeo() {
        clearInterval(sondeo);
        pedirPublicas();
        sondeo = setInterval(() => {
            if (!estaAbierta()) { clearInterval(sondeo); sondeo = null; return; }
            pedirPublicas();
        }, 4000);
    }

    // ======================================================================
    // 7. Volver al menú desde la sala de espera 1v1
    // ======================================================================
    const btnCancelar = $('btn-cancelar-1v1');
    if (btnCancelar) {
        btnCancelar.addEventListener('click', () => {
            socket.emit('abandonar_sala_limpiamente');
            localStorage.removeItem('callmus_sala');
            localStorage.removeItem('callmus_token');
            setTimeout(() => window.location.reload(), 100);
        });
    }

    // ======================================================================
    // 8. Arranque
    // ======================================================================
    // Al cambiar de idioma hay que repintar lo que se genera desde JS.
    const btnLang = $('btn-lang');
    if (btnLang) {
        btnLang.addEventListener('click', () => {
            pintarIdentidad();
            pintarResumen();
            marcarEspera(esperandoSala);   // aplicarTraduccion() ha repuesto el subtítulo
            if (modo === 4 && typeof renderSeatPicker4 === 'function') renderSeatPicker4();
            if (modo === 4 && rival4 !== 'humano' && typeof renderBotPicker4 === 'function') {
                renderBotPicker4(rival4);
            }
        });
    }

    // Invitación por enlace (?room=XXXX): app.js guarda el código y se encarga de
    // unirse o de pedir el nombre; aquí sólo abrimos la ventana para que se vea.
    if (window.__cmSalaInvitacion) {
        setTimeout(() => abrirPlay(window.__cmSalaInvitacion), 250);
    }

    aplicarTraduccion();
    pintarPlay();
})();
