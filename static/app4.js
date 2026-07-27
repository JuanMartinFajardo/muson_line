// app4.js — Cliente de Mus a 4 jugadores (2v2). Controlador: eventos de socket,
// menú/sala de espera, botones de acción y cambio de pantalla. La vista de la
// mesa la pinta table4.js (renderMesa4). Reutiliza los globales de app.js:
// `socket`, `dict`, `t`, `t_dinamico`, `langActual`, `aplicarTraduccion`, `cerrarModales`.

// ==========================================
// 1. i18n — extendemos el diccionario existente (no lo duplicamos)
// ==========================================
Object.assign(dict.es, {
    btn_crear_4: '👥 Mus 4 jugadores',
    seat_libre: 'Libre',
    equipo_a: 'Equipo A', equipo_b: 'Equipo B',
    tu_equipo: 'Tu equipo', tu_pareja: 'Tu pareja',
    esperando_jugadores_4: 'Esperando jugadores…',
    elige_asiento: 'Elige un asiento',
    pares_si: 'Pares sí', pares_no: 'Pares no',
    juego_si: 'Juego sí', juego_no: 'Juego no',
    // Pares y juego son de cada uno, no de la pareja: sin ellos no se apuesta.
    sin_pares_aviso_4: 'No tienes pares: en este lance apuesta tu compañero.',
    sin_juego_aviso_4: 'No tienes juego: en este lance apuesta tu compañero.',
    public_games_4: '🌐 Salas 4 jugadores',
    un_ordago: 'un ÓRDAGO',
    msg_baraja_agotada: '¡Se ha acabado la baraja! Se barajan los descartes.',
    rival_desconectado_4: 'Un jugador se ha desconectado. La partida termina.',
    esperando_reconexion_4: 'Un jugador se ha caído. Esperando a que vuelva…',
    jugador_reconectado_4: '¡El jugador ha vuelto! Continúa la partida.',
    seat_pick_n: 'Asiento {n}',
    gana_tu_equipo_partida: '¡Tu equipo gana la partida!',
    gana_rival_partida: 'El equipo rival gana la partida.',
    salir_texto_4: 'Volverás al menú principal. Los demás podrán esperar a que otra persona ocupe tu asiento.',
    abandono_texto_4: '{nombre} ha dejado la partida (asiento {asiento}). ¿Queréis esperar a que otra persona ocupe su sitio o prefieres salir?',
    abandono_texto_4_timeout: '{nombre} (asiento {asiento}) se ha desconectado y no ha vuelto a tiempo. ¿Queréis esperar a que otra persona ocupe su sitio o prefieres salir?',
    espera_reemplazo_texto_4: 'Vuestra partida aparece en la lista como partida en curso: cualquiera puede unirse y ocupar los asientos libres. El marcador se conserva y se repartirá una mano nueva.',
    espera_faltan_4: 'Faltan {n} jugadores por llegar.',
    espera_falta_1_4: 'Falta 1 jugador por llegar.',
    reemplazo_encontrado_4: '{nombre} se une a la partida.',
    sin_reemplazo_4: 'Nadie se ha unido a tiempo. Volviendo al menú principal.',
    leaderboard_nota_4p: 'Nota: el ELO y las victorias de arriba son de las partidas 1 contra 1. En el Mus a 4 jugadores (2v2) se guarda aparte el marcador final de cada partida (p. ej. 2-1), sumando a cada jugador los juegos ganados con su equipo.',
    // Bots (Fase 0 del plan de la IA a 4)
    bots_quien: 'Quién ocupa cada asiento',
    bots_personalidad: 'Cómo juegan los bots',
    bots_nota_mixto: 'Toca un asiento para poner un bot o dejarlo libre para otra persona.',
    bots_nota_todos: 'Los otros tres asientos los ocupan bots: la partida empieza al momento.',
    seat_tu: 'Tú',
    seat_bot: 'Bot',
    seat_persona: 'Persona',
    btn_rellenar_bots: '🤖 Rellenar con bots y empezar',
    pers_equilibrado: 'Equilibrado',
    pers_agresivo: 'Agresivo',
    pers_conservador: 'Conservador',
    pers_musero: 'Musero',
    pers_caotico: 'Caótico',
    bots_no_puntuan: 'Las partidas con bots no cuentan para la clasificación.',
    // Lo que canta cada jugador, tal cual se diría en la mesa.
    acc_mus: 'Mus',
    acc_no_mus: '¡No hay mus!',
    acc_descartar: 'Descarta {n}',
    acc_pasar: 'Paso',
    acc_envidar: 'Envido {n}',
    acc_subir: 'Subo {n}',
    acc_ver: 'Quiero',
    acc_nover: 'No quiero',
    acc_ordago: '¡ÓRDAGO!',
    acc_pedrete: '¡Pedrete!',
    // La vuelta de cantes previa a Pares y a Juego: cada uno dice si la lleva.
    acc_pares_si: '¡Pares sí!',
    acc_pares_no: 'Pares no',
    acc_juego_si: '¡Juego!',
    acc_juego_no: 'Juego no',
    cantes_pares: 'Se cantan los pares…',
    cantes_juego: 'Se canta el juego…',
});
Object.assign(dict.en, {
    btn_crear_4: '👥 4-Player Mus',
    seat_libre: 'Free',
    equipo_a: 'Team A', equipo_b: 'Team B',
    tu_equipo: 'Your team', tu_pareja: 'Your partner',
    esperando_jugadores_4: 'Waiting for players…',
    elige_asiento: 'Pick a seat',
    pares_si: 'Pairs', pares_no: 'No pairs',
    juego_si: 'Game', juego_no: 'No game',
    // Pairs and game are each player's own, not the team's: no play, no bet.
    sin_pares_aviso_4: 'You have no pairs: your partner bets this round.',
    sin_juego_aviso_4: 'You have no game: your partner bets this round.',
    public_games_4: '🌐 4-Player rooms',
    un_ordago: 'an ÓRDAGO',
    msg_baraja_agotada: 'The deck ran out! Reshuffling the discards.',
    rival_desconectado_4: 'A player disconnected. The game is over.',
    esperando_reconexion_4: 'A player dropped. Waiting for them to return…',
    jugador_reconectado_4: 'The player is back! The game continues.',
    seat_pick_n: 'Seat {n}',
    gana_tu_equipo_partida: 'Your team wins the game!',
    gana_rival_partida: 'The opposing team wins the game.',
    salir_texto_4: "You'll go back to the main menu. The others will be able to wait for someone else to take your seat.",
    abandono_texto_4: '{nombre} has left the game (seat {asiento}). Do you want to wait for someone else to take their seat, or leave too?',
    abandono_texto_4_timeout: '{nombre} (seat {asiento}) disconnected and didn\'t come back in time. Do you want to wait for someone else to take their seat, or leave too?',
    espera_reemplazo_texto_4: 'Your game is listed as an ongoing match: anyone can join and take the free seats. The score is kept and a fresh hand will be dealt.',
    espera_faltan_4: '{n} players still to arrive.',
    espera_falta_1_4: '1 player still to arrive.',
    reemplazo_encontrado_4: '{nombre} joins the game.',
    sin_reemplazo_4: 'Nobody joined in time. Going back to the main menu.',
    leaderboard_nota_4p: 'Note: the ELO and wins above are from 1-vs-1 games. In 4-player Mus (2v2) each match\'s final score (e.g. 2-1) is stored separately, adding to every player the games their team won.',
    // Bots (Phase 0 of the 4-player AI plan)
    bots_quien: 'Who sits in each seat',
    bots_personalidad: 'How the bots play',
    bots_nota_mixto: 'Tap a seat to put a bot there, or leave it open for another person.',
    bots_nota_todos: 'Bots take the other three seats: the game starts right away.',
    seat_tu: 'You',
    seat_bot: 'Bot',
    seat_persona: 'Person',
    btn_rellenar_bots: '🤖 Fill with bots and start',
    pers_equilibrado: 'Balanced',
    pers_agresivo: 'Aggressive',
    pers_conservador: 'Conservative',
    pers_musero: 'Musero',
    pers_caotico: 'Chaotic',
    bots_no_puntuan: 'Games with bots do not count towards the leaderboard.',
    // What each player just called, as it would be said at the table.
    acc_mus: 'Mus',
    acc_no_mus: 'No mus!',
    acc_descartar: 'Throws {n}',
    acc_pasar: 'Pass',
    acc_envidar: 'Bets {n}',
    acc_subir: 'Raises {n}',
    acc_ver: "I'm in",
    acc_nover: 'I fold',
    acc_ordago: 'ÓRDAGO!',
    acc_pedrete: 'Pedrete!',
    // The round of calls before Pairs and Game: everyone says if they have it.
    acc_pares_si: 'Pairs!',
    acc_pares_no: 'No pairs',
    acc_juego_si: 'Game!',
    acc_juego_no: 'No game',
    cantes_pares: 'Calling pairs…',
    cantes_juego: 'Calling game…',
});
Object.assign(dict.eu, {
    btn_crear_4: '👥 Mus 4 jokalari',
    seat_libre: 'Libre',
    equipo_a: 'A taldea', equipo_b: 'B taldea',
    tu_equipo: 'Zure taldea', tu_pareja: 'Zure bikotekidea',
    esperando_jugadores_4: 'Jokalarien zain…',
    elige_asiento: 'Aukeratu eserleku bat',
    pares_si: 'Pareak bai', pares_no: 'Pareak ez',
    juego_si: 'Jokoa bai', juego_no: 'Jokoa ez',
    // Pareak eta jokoa norberarenak dira, ez bikotearenak: gabe ez da apustatzen.
    sin_pares_aviso_4: 'Ez duzu parerik: lance honetan zure kideak apustu egingo du.',
    sin_juego_aviso_4: 'Ez duzu jokorik: lance honetan zure kideak apustu egingo du.',
    public_games_4: '🌐 4 jokalarien gelak',
    un_ordago: 'HORDAGO bat',
    msg_baraja_agotada: 'Karta-sorta amaitu da! Botatakoak berriro nahasten dira.',
    rival_desconectado_4: 'Jokalari bat deskonektatu da. Partida amaitu da.',
    esperando_reconexion_4: 'Jokalari bat erori da. Itzuli zain…',
    jugador_reconectado_4: 'Jokalaria itzuli da! Partidak aurrera darrai.',
    seat_pick_n: '{n}. eserlekua',
    gana_tu_equipo_partida: 'Zure taldeak partida irabazi du!',
    gana_rival_partida: 'Aurkako taldeak partida irabazi du.',
    salir_texto_4: 'Menu nagusira itzuliko zara. Besteek beste norbaitek zure eserlekua hartu arte itxaron ahal izango dute.',
    abandono_texto_4: '{nombre}k partida utzi du ({asiento}. eserlekua). Beste norbaitek bere lekua hartu arte itxaron nahi duzue, ala irten nahiago duzu?',
    abandono_texto_4_timeout: '{nombre} ({asiento}. eserlekua) deskonektatu egin da eta ez da garaiz itzuli. Beste norbaitek bere lekua hartu arte itxaron nahi duzue, ala irten nahiago duzu?',
    espera_reemplazo_texto_4: 'Zuen partida abian dauden partiden zerrendan agertzen da: edonor sartu eta eserleku libreak har ditzake. Markagailua gorde egiten da eta esku berri bat banatuko da.',
    espera_faltan_4: '{n} jokalari falta dira iristeko.',
    espera_falta_1_4: 'Jokalari 1 falta da iristeko.',
    reemplazo_encontrado_4: '{nombre} partidara sartu da.',
    sin_reemplazo_4: 'Inor ez da garaiz sartu. Menu nagusira itzultzen.',
    leaderboard_nota_4p: 'Oharra: goiko ELOa eta garaipenak 1 aurka 1 partidenak dira. 4 jokalarien musean (2v2) partida bakoitzaren azken markagailua (adib. 2-1) bereiz gordetzen da, jokalari bakoitzari bere taldearekin irabazitako jokoak batuz.',
    // Botak (4ko IAren planaren 0. fasea)
    bots_quien: 'Nork hartzen du eserleku bakoitza',
    bots_personalidad: 'Botek nola jokatzen duten',
    bots_nota_mixto: 'Ukitu eserleku bat bot bat jartzeko, edo utzi libre beste pertsona batentzat.',
    bots_nota_todos: 'Beste hiru eserlekuak botek hartzen dituzte: partida berehala hasiko da.',
    seat_tu: 'Zu',
    seat_bot: 'Bota',
    seat_persona: 'Pertsona',
    btn_rellenar_bots: '🤖 Botez bete eta hasi',
    pers_equilibrado: 'Orekatua',
    pers_agresivo: 'Erasokorra',
    pers_conservador: 'Kontserbadorea',
    pers_musero: 'Musera',
    pers_caotico: 'Kaotikoa',
    bots_no_puntuan: 'Boten aurkako partidek ez dute sailkapenerako balio.',
    // Jokalari bakoitzak kantatzen duena, mahaian esango litzatekeen bezala.
    acc_mus: 'Mus',
    acc_no_mus: 'Musik ez!',
    acc_descartar: '{n} botatzen ditu',
    acc_pasar: 'Paso',
    acc_envidar: 'Envido {n}',
    acc_subir: '{n} igotzen du',
    acc_ver: 'Kanta',
    acc_nover: 'Ez dut nahi',
    acc_ordago: 'HORDAGO!',
    acc_pedrete: 'Pedrete!',
    // Pareak eta jokoa kantatzeko txanda, apustuen aurretik.
    acc_pares_si: 'Pareak bai!',
    acc_pares_no: 'Pareak ez',
    acc_juego_si: 'Jokoa!',
    acc_juego_no: 'Jokoa ez',
    cantes_pares: 'Pareak kantatzen…',
    cantes_juego: 'Jokoa kantatzen…',
});
aplicarTraduccion();

// ==========================================
// 2. Estado del módulo
// ==========================================
let enPartida4 = false;
let asientoElegido4 = 0;
let miCodigo4 = null;
let miAsiento4 = null;
let miToken4 = localStorage.getItem('callmus4_token') || null;
let prevPayload4 = null;
let estadoActual4 = null;
let timerInterval4 = null;

// El 2v2 ya no tiene ventana propia: vive dentro de la ventana de Jugar
// (#modal-play), que abre y pinta menu.js. Aquí sólo apuntamos a sus paneles.
const modal4 = document.getElementById('modal-play');
const panelSetup4 = document.getElementById('play-setup');
const panelEspera4 = document.getElementById('panel-4-espera');
const msg4 = document.getElementById('play-msg');

/** Nombre visible de un bot: 🤖 + su personalidad, en el idioma activo.
 *  `corto` es el de la mesa, donde el hueco del nombre es estrecho (en el móvil
 *  «🤖 Bot · Agresivo» desbordaba el asiento); el largo, el de la sala de
 *  espera, que se pinta en lista y tiene sitio de sobra. */
function etiquetaBot4(personalidad, corto) {
    const clave = 'pers_' + (personalidad || 'equilibrado');
    const nombre = _resolver(clave) ? t(clave) : t('seat_bot');
    return corto ? `🤖 ${nombre}` : `🤖 ${t('seat_bot')} · ${nombre}`;
}

function nombre4() {
    // Con sesión iniciada, auth.js deja el nombre de usuario en #nombre-jugador.
    let n = (document.getElementById('nombre-jugador') || {}).value;
    if (!n) n = localStorage.getItem('callmus_nombre') || '';
    return (n || '').trim();
}

// ==========================================
// 3. Selector de asiento (dentro de la ventana de Jugar)
// ==========================================

function renderSeatPicker4() {
    const cont = document.getElementById('seat-picker-4');
    if (!cont) return;
    cont.innerHTML = '';
    for (let s = 0; s < 4; s++) {
        const eq = (s === 0 || s === 2) ? 'A' : 'B';
        const btn = document.createElement('button');
        btn.className = 'seat-pick-btn equipo-' + eq + (s === asientoElegido4 ? ' selected' : '');
        btn.innerHTML = `${t_dinamico('seat_pick_n', { n: s })}<small>${t('equipo_' + eq.toLowerCase())}</small>`;
        btn.onclick = () => {
            asientoElegido4 = s;
            botsElegidos4.delete(s);       // en tu propio asiento no va un bot
            renderSeatPicker4();
            renderBotPicker4();
        };
        cont.appendChild(btn);
    }
}

// ==========================================
// 3 bis. Asientos con bot (Fase 0 del plan de la IA a 4)
// ------------------------------------------------------------------
// 'bots'  → los otros tres asientos son bots y la partida arranca sola.
// 'mixto' → eliges cuáles; los que dejes libres esperan a que llegue gente.
// ==========================================
let botsElegidos4 = new Set();

function renderBotPicker4(modoRivales) {
    const cont = document.getElementById('bot-picker-4');
    if (!cont) return;
    const modo = modoRivales || (typeof modoRivales4 === 'function' ? modoRivales4() : 'mixto');
    const todos = (modo === 'bots');

    if (todos) {
        // Sin elección posible: todo lo que no sea tu asiento va con bot.
        botsElegidos4 = new Set([0, 1, 2, 3].filter(s => s !== asientoElegido4));
    }
    const nota = document.getElementById('bots-nota-4');
    if (nota) nota.innerText = t(todos ? 'bots_nota_todos' : 'bots_nota_mixto');

    cont.innerHTML = '';
    for (let s = 0; s < 4; s++) {
        const eq = (s === 0 || s === 2) ? 'A' : 'B';
        const esYo = (s === asientoElegido4);
        const esBot = botsElegidos4.has(s);
        const btn = document.createElement('button');
        btn.className = 'seat-pick-btn equipo-' + eq + (esBot ? ' es-bot' : '') + (esYo ? ' selected' : '');
        btn.disabled = esYo || todos;
        const quien = esYo ? t('seat_tu') : (esBot ? '🤖 ' + t('seat_bot') : t('seat_persona'));
        btn.innerHTML = `${t_dinamico('seat_pick_n', { n: s })}<small>${quien}</small>`;
        btn.onclick = () => {
            if (esBot) botsElegidos4.delete(s); else botsElegidos4.add(s);
            renderBotPicker4(modo);
        };
        cont.appendChild(btn);
    }
}

// ==========================================
// 4. Crear / unirse
// ==========================================
document.getElementById('btn-crear-sala-4').addEventListener('click', () => {
    const nombre = nombre4();
    if (!nombre) { msg4.innerText = t('msg_inserta_nombre'); return; }
    localStorage.setItem('callmus_nombre', nombre);
    const modoRivales = (typeof modoRivales4 === 'function') ? modoRivales4() : 'humano';
    const conBots = modoRivales !== 'humano';
    if (conBots) renderBotPicker4(modoRivales);   // fija los asientos de 'bots'
    const bots = conBots ? [...botsElegidos4].filter(s => s !== asientoElegido4) : [];

    socket.emit('crear_sala_4', {
        nombre,
        al_mejor_de: parseInt(document.getElementById('in-mejor-de-4').value) || 3,
        // Una mesa llena de bots empieza sola: no hay a quién anunciarla.
        publico: (modoRivales !== 'bots') && document.getElementById('in-publico-4').checked,
        asiento: asientoElegido4,
        bots,
        personalidad: personalidadElegida4(),
        // Señas: sólo existen en el 2v2 y se deciden al crear la mesa.
        senas: !!(document.getElementById('in-senas') || {}).checked,
    });
    msg4.innerText = '';
});

function personalidadElegida4() {
    const sel = document.getElementById('in-personalidad-4');
    return (sel && sel.value) || 'equilibrado';
}

// Desde la sala de espera: si no llega nadie, se rellena con bots y a jugar.
document.getElementById('btn-rellenar-bots-4').addEventListener('click', () => {
    socket.emit('rellenar_bots_4', { personalidad: personalidadElegida4() });
});

document.getElementById('btn-unirse-4').addEventListener('click', () => {
    const nombre = nombre4();
    if (!nombre) { msg4.innerText = t('msg_inserta_nombre'); return; }
    const cod = document.getElementById('in-codigo-4').value.trim().toUpperCase();
    if (!cod) { msg4.innerText = t('msg_escribe_codigo'); return; }
    localStorage.setItem('callmus_nombre', nombre);
    socket.emit('unirse_sala_4', { nombre, codigo: cod });
});

socket.on('sala_creada_4', (d) => {
    miCodigo4 = d.codigo;
    miAsiento4 = d.asiento;
    if (d.token) { miToken4 = d.token; localStorage.setItem('callmus4_token', d.token); }
    localStorage.setItem('callmus4_codigo', d.codigo);
    panelSetup4.classList.add('hidden');
    panelEspera4.classList.remove('hidden');
    document.getElementById('txt-codigo-4').innerText = d.codigo;
    if (typeof marcarEsperaPlay === 'function') marcarEsperaPlay(true);
    msg4.innerText = '';
});

socket.on('error_sala_4', (d) => { if (msg4) msg4.innerText = d.mensaje || 'Error'; });

// Lista pública 4p
socket.on('actualizar_publicas_4', (lista) => {
    const tbody = document.getElementById('lista-publicas-4');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!lista.length) {
        tbody.innerHTML = `<tr><td colspan="2" class="cm-live-empty">${t('msg_no_publicas')}</td></tr>`;
        return;
    }
    lista.forEach(p => {
        const tr = document.createElement('tr');

        // Partida EN CURSO con asientos libres: se marca y se muestra el marcador.
        let etiqueta = '';
        let meta = t_dinamico('live_asientos', { n: p.ocupados });
        if (p.en_curso) {
            tr.className = 'fila-en-curso';
            etiqueta = `<span class="badge-en-curso">${t('txt_en_curso')}</span>`;
            if (p.puntos) {
                meta += ` · ${t('txt_marcador')} ${p.puntos.A}-${p.puntos.B}`;
            }
        }

        tr.innerHTML = `
            <td>
                <span class="cm-live-name">${escHtml(p.creador)}</span>${etiqueta}
                <span class="cm-live-meta">${meta}</span>
            </td>
            <td class="cm-live-cell-act">
                <button class="btn-unirse-publica-4 cm-live-join" data-codigo="${p.codigo}">${t('btn_unirse_publica')}</button>
            </td>`;
        tbody.appendChild(tr);
    });
    tbody.querySelectorAll('.btn-unirse-publica-4').forEach(btn => {
        btn.onclick = () => {
            const nombre = nombre4();
            if (!nombre) { msg4.innerText = t('msg_inserta_nombre'); return; }
            localStorage.setItem('callmus_nombre', nombre);
            socket.emit('unirse_sala_4', { nombre, codigo: btn.getAttribute('data-codigo') });
        };
    });
});

// Sala de espera: foto de los asientos
socket.on('estado_espera_4', (d) => {
    if (d.codigo !== miCodigo4) return;
    const cont = document.getElementById('asientos-espera-4');
    if (cont) {
        cont.innerHTML = '';
        d.asientos.forEach(a => {
            const div = document.createElement('div');
            div.className = 'seat-espera equipo-' + a.equipo + (a.ocupado ? ' ocupado' : '') + (a.bot ? ' es-bot' : '');
            const teamCls = a.equipo === 'A' ? 'seat-team-a' : 'seat-team-b';
            const quien = a.bot ? etiquetaBot4(a.personalidad)
                                : (a.ocupado ? escHtml(a.nombre || '—') : t('seat_libre'));
            div.innerHTML = `<span class="${teamCls}">${t_dinamico('seat_pick_n', { n: a.asiento })}</span>
                <small>${quien} · ${t('equipo_' + a.equipo.toLowerCase())}</small>`;
            cont.appendChild(div);
        });
        const ocupados = d.asientos.filter(a => a.ocupado).length;
        const em = document.getElementById('espera-msg-4');
        if (em) em.innerText = t('esperando_jugadores_4').replace('…', ` (${ocupados}/4)…`);
        // Sin asientos libres no hay nada que rellenar.
        const btnBots = document.getElementById('btn-rellenar-bots-4');
        if (btnBots) btnBots.classList.toggle('hidden', ocupados >= 4);
    }
});

// Compartir código
document.getElementById('btn-share-copy-4').addEventListener('click', () => {
    if (miCodigo4) navigator.clipboard && navigator.clipboard.writeText(miCodigo4);
});
document.getElementById('btn-share-wa-4').addEventListener('click', () => {
    if (miCodigo4) window.open(`https://wa.me/?text=${encodeURIComponent('Mus a 4 en CallMus, código: ' + miCodigo4)}`, '_blank');
});
document.getElementById('btn-cancelar-4').addEventListener('click', volverMenu4);

// ==========================================
// 5. Inicio de partida y cambio de pantalla
// ==========================================
socket.on('iniciar_partida_4', (d) => {
    if (d.codigo && d.codigo !== miCodigo4) return;
    entrarPantalla4();
    // Sorteo de la Mano (sorteo.js): telón opaco con la pinta de cada asiento y
    // la ruleta en el centro. Sólo llega al empezar la mesa; quien entra a una
    // partida ya en curso no lo ve.
    if (d.sorteo && typeof SorteoMano !== 'undefined') {
        SorteoMano.jugar4p(d.sorteo, miAsiento4);
    }
});

socket.on('reanudado_4', (d) => {
    miCodigo4 = d.codigo; miAsiento4 = d.asiento;
    entrarPantalla4();
});

function entrarPantalla4() {
    enPartida4 = true;
    if (typeof cerrarModales === 'function') cerrarModales();
    modal4.classList.add('hidden');
    document.getElementById('menu-screen').classList.add('hidden');
    document.getElementById('game-screen').classList.add('hidden');
    document.getElementById('game-screen-4').classList.remove('hidden');
}

function volverMenu4() {
    socket.emit('abandonar_sala_4');
    localStorage.removeItem('callmus4_codigo');
    localStorage.removeItem('callmus4_token');
    enPartida4 = false;
    setTimeout(() => window.location.reload(), 100);
}

// ==========================================
// 6. Estado de la mesa
// ==========================================
socket.on('actualizar_mesa_4', (datos) => {
    if (datos.para_sid !== socket.id) return;
    if (!enPartida4) entrarPantalla4();

    if (datos.aviso_baraja) mostrarToast4(t('msg_baraja_agotada'));

    renderMesa4(prevPayload4, datos);
    prevPayload4 = datos;
    estadoActual4 = datos;

    actualizarMensajeYBotones4(datos);
    actualizarTimer4(datos);
    // Las señas van DESPUÉS de pintar: renderMesa4 rehace las clases de cada
    // asiento y borraría el resaltado del foco.
    if (window.Senas4) Senas4.sincronizar(datos);
});

// Alguien de la mesa ha cambiado de baraja sin levantarse (Roadmap #5). Se
// parchea el asiento y se repinta con el mismo estado: no llega uno nuevo, que
// reiniciaría el reloj del turno.
socket.on('baraja_mesa_4', (d) => {
    if (!d || !estadoActual4 || d.asiento === undefined || d.asiento === null) return;
    const asiento = (estadoActual4.seats || []).find(s => s.asiento === d.asiento);
    if (!asiento) return;
    asiento.baraja = d.config;
    renderMesa4(estadoActual4, estadoActual4);
    // renderMesa4 rehace las clases de cada asiento: el foco, después.
    if (window.Senas4) Senas4.sincronizar(estadoActual4);
});

// ---------- Lo que canta cada jugador ----------
// El servidor anuncia toda acción de juego a la mesa (`accion_4`); aquí se
// traduce y table4.js la pinta un momento en el sitio de quien la hizo. Los
// cantes fuertes se marcan aparte para que salten a la vista.
const ACCIONES_FUERTES_4 = {
    ordago: 'fuerte', no_mus: 'corta', pedrete: 'fuerte',
    // La vuelta de cantes no es una jugada: se pinta más apagada, para que
    // «pares sí» no compita visualmente con un envite.
    pares_si: 'cante', pares_no: 'cante cante-no',
    juego_si: 'cante', juego_no: 'cante cante-no',
};

socket.on('accion_4', (d) => {
    if (!enPartida4 || !d) return;
    // El asiento propio se toma del último estado, que es la fuente autorizada
    // (tras reconectar puedes volver a un asiento distinto del que guardaste).
    const yo = estadoActual4 ? estadoActual4.mi_asiento : miAsiento4;
    if (yo === null || yo === undefined) return;
    const clave = 'acc_' + d.accion;
    if (!_resolver(clave)) return;
    const texto = (d.cantidad === null || d.cantidad === undefined)
        ? t(clave)
        : t_dinamico(clave, { n: d.cantidad });
    mostrarAccion4(yo, d.asiento, texto, ACCIONES_FUERTES_4[d.accion]);
});

function actualizarMensajeYBotones4(d) {
    const log = document.getElementById('game-log-4');

    // Transición (nadie pares, punto, etc.). El servidor auto-avanza.
    if (d.mensaje_transicion) {
        log.innerHTML = `<strong style="color:#fff;font-weight:300;letter-spacing:1px;">${textoTransicion4(d.mensaje_transicion)}</strong>`;
        mostrarBotones4([]);
        ocultarPanelesApuesta4();
        return;
    }

    if (d.fase === 'recuento') {
        renderRecuento4(d);
        return;
    }

    // Vuelta de cantes de Pares/Juego: la mesa está diciendo quién lleva la
    // jugada. No hay turno de nadie ni botones que ofrecer hasta que acabe.
    if (d.declarando) {
        log.innerText = t(d.declarando === 'Pares' ? 'cantes_pares' : 'cantes_juego');
        mostrarBotones4([]);
        ocultarPanelesApuesta4();
        return;
    }

    // Mensaje breve de fase (el turno ya se ve por el resaltado del asiento).
    if (d.fase === 'descarte' && d.mis_descartes_listos) {
        log.innerText = t('info_esperando_rival_descarte');
    } else if (d.fase === 'espera_reparto') {
        log.innerText = d.es_mi_turno ? '' : t('esperando_jugadores_4');
    } else {
        log.innerText = avisoSinJugada4(d);
    }

    // Botones de acción
    ocultarPanelesApuesta4();
    const botones = [];
    if (d.puede_pedrete) botones.push('btn-pedrete-4');

    if (d.fase === 'descarte') {
        if (!d.mis_descartes_listos) {
            botones.push('btn-todas-4', 'btn-descartar-4');
            sincronizarBotonesDescarte4();
        }
    } else if (d.es_mi_turno) {
        if (d.fase === 'espera_reparto') botones.push('btn-deal-4');
        else if (d.fase === 'mus') botones.push('btn-mus-4', 'btn-nomus-4');
        else if (d.fase === 'apuestas') mostrarPanelApuesta4(d);
    }
    mostrarBotones4(botones);
}

function textoTransicion4(mt) {
    if (mt.code === 'no_pares' || mt.code === 'no_juego') {
        const equipo = mt.equipo === 'A' ? t('equipo_a') : t('equipo_b');
        // Reutilizamos msg_no_pares/msg_no_juego con {rol}; pasamos el equipo ganador.
        return t_dinamico('msg_' + mt.code, { rol: equipo });
    }
    return t('msg_' + mt.code);
}

// Qué se puede pulsar lo decide el servidor (`acciones_legales`), no el cliente:
// además de los topes de 40 ahí está la regla que Pares y Juego son jugadas
// INDIVIDUALES —sin ellas sólo se pasa o se rehúsa, aunque las tenga tu
// compañero—. Si un servidor viejo no manda la lista se muestra todo, como antes.
function _puede4(d, accion) {
    return !d.acciones_legales || d.acciones_legales.includes(accion);
}

function mostrarPanelApuesta4(d) {
    document.getElementById('action-buttons-4').classList.remove('hidden');
    const ap = d.apuestas;
    if (ap.subida === 0) {
        document.getElementById('apuesta-iniciar-4').classList.remove('hidden');
        const inEnv = document.getElementById('in-envidar-4');
        const max = 40 - Math.max(d.mis_puntos_equipo, d.puntos_rival_equipo);
        inEnv.max = max > 0 ? max : 1;
        const puedeEnvidar = _puede4(d, 'envidar');
        inEnv.classList.toggle('hidden', !puedeEnvidar);
        document.getElementById('btn-envidar-4').classList.toggle('hidden', !puedeEnvidar);
        document.getElementById('btn-pasar-4').classList.toggle('hidden', !_puede4(d, 'pasar'));
        document.getElementById('btn-ordago-4').classList.toggle('hidden', !_puede4(d, 'ordago'));
    } else {
        document.getElementById('apuesta-responder-4').classList.remove('hidden');
        const puedeSubir = _puede4(d, 'subir');
        document.getElementById('btn-ver-4').classList.toggle('hidden', !_puede4(d, 'ver'));
        document.getElementById('in-subir-4').classList.toggle('hidden', !puedeSubir);
        document.getElementById('btn-subir-4').classList.toggle('hidden', !puedeSubir);
        document.getElementById('btn-ordago-resp-4').classList.toggle('hidden', !_puede4(d, 'ordago'));
        document.getElementById('btn-nover-4').classList.toggle('hidden', !_puede4(d, 'nover'));
    }
}

// Por qué la mesa sólo te deja pasar (o no querer) en Pares/Juego: no llevas la
// jugada. Sin este aviso el jugador ve los botones a medias y no sabe por qué.
// Quien no tiene la jugada nunca puede echar un órdago: ese es el indicador.
function avisoSinJugada4(d) {
    if (d.fase !== 'apuestas' || !d.es_mi_turno || !d.acciones_legales) return '';
    if (d.acciones_legales.includes('ordago')) return '';
    const lance = d.apuestas && d.apuestas.fase_actual;
    if (lance === 'Pares') return t('sin_pares_aviso_4');
    if (lance === 'Juego') return t('sin_juego_aviso_4');
    return '';
}

function ocultarPanelesApuesta4() {
    document.getElementById('apuesta-iniciar-4').classList.add('hidden');
    document.getElementById('apuesta-responder-4').classList.add('hidden');
}

function mostrarBotones4(ids) {
    const cont = document.getElementById('action-buttons-4');
    const all = ['btn-deal-4', 'btn-pedrete-4', 'btn-mus-4', 'btn-nomus-4', 'btn-todas-4', 'btn-descartar-4', 'btn-next-round-4', 'btn-volver-menu-4'];
    all.forEach(id => { const el = document.getElementById(id); if (el) el.classList.add('hidden'); });
    const mostrarPaneles = !document.getElementById('apuesta-iniciar-4').classList.contains('hidden') ||
                           !document.getElementById('apuesta-responder-4').classList.contains('hidden');
    if (ids.length || mostrarPaneles) {
        cont.classList.remove('hidden');
        ids.forEach(id => { const el = document.getElementById(id); if (el) el.classList.remove('hidden'); });
    } else {
        cont.classList.add('hidden');
    }
}

// Resultado de la ronda (recuento)
function renderRecuento4(d) {
    ocultarPanelesApuesta4();
    const log = document.getElementById('game-log-4');
    let html = `<strong style="font-size:1.15em;color:#fff;text-transform:uppercase;letter-spacing:2px;font-weight:300;">${t('msg_resultados')}</strong><br><br>`;

    (d.recuento || []).forEach(paso => {
        const c = paso.datos.code;
        if (c === 'recuento_nover') {
            if (paso.datos.fase !== 'Grande' && paso.datos.fase !== 'Chica') {
                const nf = t('fase_' + paso.datos.fase.toLowerCase());
                html += `<i>${t_dinamico('msg_recuento_nover', { fase: nf })}</i><br>`;
            }
        } else if (c === 'recuento_gana') {
            const nf = t('fase_' + paso.datos.fase.toLowerCase());
            const clave = paso.gano_mi_equipo ? 'msg_recuento_gana_yo' : 'msg_recuento_gana_rival';
            html += `${t_dinamico(clave, { puntos: paso.datos.puntos, fase: nf })}<br>`;
        } else if (c === 'recuento_ordago') {
            const nf = t('fase_' + paso.datos.fase.toLowerCase());
            const clave = paso.gano_mi_equipo ? 'msg_recuento_ordago_yo' : 'msg_recuento_ordago_rival';
            html += `${t_dinamico(clave, { fase: nf })}<br>`;
        } else if (c === 'recuento_pedrete_win') {
            html += `${t(paso.gano_mi_equipo ? 'msg_recuento_pedrete_win_yo' : 'msg_recuento_pedrete_win_rival')}<br>`;
        }
    });

    const alguienGano = d.puntos.A >= 40 || d.puntos.B >= 40;
    let botones = [];
    if (alguienGano) {
        const gano = d.puntos[d.mi_equipo] >= 40;
        html += `<br><strong style="font-size:1.4em;color:#fff;font-weight:300;">${gano ? t('gana_tu_equipo_partida') : t('gana_rival_partida')}</strong>`;
        if (d.match_finalizado) {
            const ganoMatch = d.ganador_equipo === d.mi_equipo;
            html += `<br><strong style="font-size:1.4em;color:#fff;font-weight:300;">${ganoMatch ? t('msg_gana_match_yo') : t('msg_gana_match_rival')}</strong>`;
            botones = ['btn-volver-menu-4'];
            localStorage.removeItem('callmus4_codigo');
            localStorage.removeItem('callmus4_token');
        } else {
            document.getElementById('btn-next-round-4').innerText = t('btn_next_game');
            botones = ['btn-next-round-4'];
        }
    } else {
        document.getElementById('btn-next-round-4').innerText = t('btn_next_round');
        botones = ['btn-next-round-4'];
    }
    log.innerHTML = html;
    mostrarBotones4(botones);
}

// ==========================================
// 7. Temporizador de turno (barra de cuenta atrás)
// ==========================================
function actualizarTimer4(d) {
    const wrap = document.getElementById('turno-timer-4');
    const bar = document.getElementById('turno-timer-bar-4');
    if (timerInterval4) { clearInterval(timerInterval4); timerInterval4 = null; }
    const activo = d.turno_deadline_epoch && !d.mensaje_transicion &&
                   ['espera_reparto', 'mus', 'apuestas', 'descarte'].includes(d.fase) && !d.match_finalizado;
    if (!activo) { wrap.classList.add('hidden'); return; }

    wrap.classList.remove('hidden');
    const fin = Date.now() + TURNO_SEGUNDOS_4 * 1000;   // cuenta atrás local (evita desfase de reloj)
    const tick = () => {
        const restante = Math.max(0, fin - Date.now());
        const pct = (restante / (TURNO_SEGUNDOS_4 * 1000)) * 100;
        bar.style.width = pct + '%';
        bar.classList.toggle('urgente', restante < 3000);
        if (restante <= 0 && timerInterval4) { clearInterval(timerInterval4); timerInterval4 = null; }
    };
    tick();
    timerInterval4 = setInterval(tick, 120);
}

function mostrarToast4(texto) {
    const toast = document.getElementById('social-toast');
    if (!toast) return;
    toast.innerText = texto;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 2500);
}

// ==========================================
// 8. Botones de acción → servidor
// ==========================================
const emit4 = (accion, extra) => { mostrarBotones4([]); socket.emit('accion_juego_4', Object.assign({ accion }, extra || {})); };

document.getElementById('btn-deal-4').addEventListener('click', () => emit4('repartir'));
document.getElementById('btn-pedrete-4').addEventListener('click', () => emit4('pedrete'));
document.getElementById('btn-mus-4').addEventListener('click', () => emit4('mus'));
document.getElementById('btn-nomus-4').addEventListener('click', () => emit4('no_mus'));
document.getElementById('btn-descartar-4').addEventListener('click', () => emit4('descartar', { indices: cartasSeleccionadas4 }));
document.getElementById('btn-todas-4').addEventListener('click', seleccionarTodas4);
document.getElementById('btn-pasar-4').addEventListener('click', () => emit4('pasar'));
document.getElementById('btn-ver-4').addEventListener('click', () => emit4('ver'));
document.getElementById('btn-nover-4').addEventListener('click', () => emit4('nover'));
document.getElementById('btn-ordago-4').addEventListener('click', () => emit4('ordago'));
document.getElementById('btn-ordago-resp-4').addEventListener('click', () => emit4('ordago'));

document.getElementById('btn-envidar-4').addEventListener('click', () => {
    let cant = parseInt(document.getElementById('in-envidar-4').value) || 2;
    if (estadoActual4) {
        const max = 40 - Math.max(estadoActual4.mis_puntos_equipo, estadoActual4.puntos_rival_equipo);
        if (cant > max) cant = max;
    }
    emit4('envidar', { cantidad: Math.max(1, cant) });
});
document.getElementById('btn-subir-4').addEventListener('click', () => {
    let cant = parseInt(document.getElementById('in-subir-4').value) || 2;
    if (estadoActual4) {
        const tope = 40 - Math.max(estadoActual4.mis_puntos_equipo, estadoActual4.puntos_rival_equipo) - (estadoActual4.apuestas.apuesta_vista || 0);
        if (cant > tope) cant = tope;
    }
    emit4('subir', { cantidad: Math.max(1, cant) });
});
document.getElementById('btn-next-round-4').addEventListener('click', () => {
    document.getElementById('game-log-4').innerText = t('info_esperando_rival_listo');
    emit4('listo_siguiente_ronda');
});
document.getElementById('btn-volver-menu-4').addEventListener('click', volverMenu4);
// El [?] de la mesa lo recoge tutorial.js, que abre la pista del 2 contra 2.

// ==========================================
// 9. Desconexión / reconexión / sustituciones
// ==========================================
socket.on('jugador_desconectado_4', () => { if (enPartida4) mostrarToast4(t('esperando_reconexion_4')); });
socket.on('jugador_reconectado_4', () => { if (enPartida4) mostrarToast4(t('jugador_reconectado_4')); });
socket.on('rival_desconectado_4', (d) => {
    if (!enPartida4) return;
    ocultarOverlaysPartida();
    alert((d && d.motivo === 'sin_reemplazo') ? t('sin_reemplazo_4') : t('rival_desconectado_4'));
    localStorage.removeItem('callmus4_codigo');
    localStorage.removeItem('callmus4_token');
    enPartida4 = false;
    window.location.reload();
});

// Salida voluntaria desde la mesa: el asiento queda libre para un sustituto.
function salirDePartida4() {
    ocultarOverlaysPartida();
    enPartida4 = false;
    localStorage.removeItem('callmus4_codigo');
    localStorage.removeItem('callmus4_token');
    socket.emit('abandonar_partida_4');
    setTimeout(() => window.location.reload(), 150);
}

document.getElementById('btn-salir-partida-4').addEventListener('click', () => {
    confirmarSalidaPartida(t('salir_texto_4'), salirDePartida4);
});

// Alguien dejó la mesa (o agotó su ventana de reconexión): esperar o salir.
socket.on('jugador_abandono_4', (d) => {
    if (!enPartida4) return;
    mostrarAvisoAbandono({
        nombre: (d && d.nombre) || '...',
        motivo: d && d.motivo,
        onEsperar: () => socket.emit('esperar_reemplazo_4'),
        onSalir: salirDePartida4,
        // El 2v2 nombra el asiento vacante en el texto.
        texto: t_dinamico(d && d.motivo === 'timeout' ? 'abandono_texto_4_timeout' : 'abandono_texto_4',
                          { nombre: (d && d.nombre) || '...', asiento: (d && d.asiento) }),
    });
});

// Se acepta esperar (o seguimos esperando tras reconectar): overlay con cuenta atrás.
socket.on('esperando_reemplazo_4', (d) => {
    if (!enPartida4) return;
    const faltan = (d && d.libres) ? d.libres.length : 1;
    mostrarEsperaReemplazo((d && d.segundos) || 0, salirDePartida4, {
        texto: t('espera_reemplazo_texto_4') + ' ' +
               (faltan === 1 ? t('espera_falta_1_4') : t_dinamico('espera_faltan_4', { n: faltan })),
    });
});

// Mesa completa otra vez: se reanuda con marcador intacto y mano nueva.
socket.on('reemplazo_encontrado_4', (d) => {
    ocultarOverlaysPartida();
    if (enPartida4 && d && d.nombre) mostrarToast4(t_dinamico('reemplazo_encontrado_4', { nombre: d.nombre }));
});

// Reconexión tras recargar/caerse (dentro de la ventana de gracia del servidor).
socket.on('connect', () => {
    const cod = localStorage.getItem('callmus4_codigo');
    const tok = localStorage.getItem('callmus4_token');
    if (cod && tok && !enPartida4) {
        miCodigo4 = cod; miToken4 = tok;
        socket.emit('reanudar_partida_4', { codigo: cod, token: tok });
    }
});

// El sondeo de la lista pública lo lleva menu.js, que sabe qué modo (1v1 o 2v2)
// está mirando el jugador y sólo pide la lista que se está viendo.
