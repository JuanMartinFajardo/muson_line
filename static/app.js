const socket = io({ closeOnBeforeunload: false });

let miNombre = "";
let faseJuego = 'espera';
let cartasSeleccionadas = [];
let subfaseApuestasActual = "";
let apuestaVistaActual = 0; // CORREGIDO: V mayúscula
let enPartida = false;

// PANTALLAS CORRECTAS
const menuScreen = document.getElementById('menu-screen');
const gameScreen = document.getElementById('game-screen');
const gameLog = document.getElementById('game-log');


// ==========================================
// 0. MOTOR DE IDIOMAS (i18n)
// ==========================================
const dict = {
    es: {
        btn_login: "Iniciar Sesión",
        btn_signup: "Registrarse",
        btn_logout: "Cerrar Sesión",
        btn_crear: "Crear partida nueva",
        btn_unirse: "Unirse con código",
        btn_show_leaderboard: "Ver Leaderboard",
        btn_deal: "Repartir Cartas",
        btn_nomus: "Corto",
        btn_descartar: "Descartar",
        btn_next_round: "Siguiente ronda",
        btn_volver_menu: "Volver al Menú",
        btn_envidar: "Envidar",
        btn_pasar: "Pasar",
        btn_ordago: "Órdago",
        btn_ver: "Ver",
        btn_subir: "Subir",
        btn_nover: "No ver",
        btn_ordago_resp: "Órdago",
        al_mejor_de: "Al mejor de:",
        al_mejor_de_colname: "Mejor de",
        user_colname: "Usuario",
        action_colname: "Acción",
        public_games: "🌐 Partidas Públicas",
        esperando_rival: "Esperando a que se una el rival...",
        in_publico: "Hacer pública (visible para todos)",
        partidas: "partidas",
        mi_turno: "⚠️ Tú hablas",
        my_cards: "Tus cartas aparecerán aquí",
        watermark: "Creado por Juan Martín Fajardo",
        login_remember: "Mantener la sesión iniciada",
        leaderboard_title: "🏆 Clasificación Mundial",
        elo_colname: "ELO 🔽",
        wins_colname: "Victorias ↕️",
        winrate_colname: "Winrate ↕️",
        loading_players: "Loading players...",
        codigo_sala: "Código de tu sala:",
        tu_nombre: "Tu nombre...",
        password: "Contraseña",
        signup_birth: "Fecha de nacimiento:",
        user_name: "Nombre de usuario",
        pais_nacimiento: "País de nacimiento",
        btn_cuenta: "Crear cuenta",
        opponent_speaks: "⚠️ El rival habla",
        cartas_rival_ocultas: "[Cartas del rival ocultas]",
        txt_tu: "Tú",
        txt_pts: "Pts:",
        txt_partidas: "Partidas:",
        txt_rival: "Rival",
        codigo_placeholder: "Código de sala...",
        btn_next_game: "Siguiente partida",
        info_tus_cartas: "Tus cartas aparecerán aquí",
        info_esperando_rival_descarte: "Esperando a que el rival se descarte...",
        rival_siguiente_partida: "Esperando al rival para la siguiente partida...",
        info_esperando_rival_listo: "Esperando a que el rival esté listo...",
        info_rival_cambio: "El rival cambió ",
        cartas: " cartas",
        has_ganado_partida: "🏆 ¡HAS GANADO ESTA PARTIDA!",
        el_rival_ganado_partida: "💀 ¡HAS PERDIDO ESTA PARTIDA!",
        has_ganado_match: "🏆 ¡HAS GANADO EL MATCH!",
        el_rival_ganado_match: "💀 ¡HAS PERDIDO EL MATCH!",
        info_apuesta_vista: "Apuesta vista:",
        cartas_sin_repartir: "[Cartas sin repartir]",
        te_suben: "Te suben: ",
        has_subido: "Has subido: ",
        eres_mano: "(Eres Mano)",
        eres_postre: "(Eres Postre)",
        resultados_ronda: "Resultados de la ronda:",
        txt_mano: "Mano",
        txt_postre: "Postre",
        fase_grande: "GRANDE",
        fase_chica: "CHICA",
        fase_pares: "PARES",
        fase_juego: "JUEGO",
        fase_mus: "MUS",
        msg_nadie_pares: "Nadie tiene Pares.",
        msg_no_pares: "El {rol} no tiene Pares.",
        msg_juego_a_punto: "Nadie tiene Juego. Se juega al Punto.",
        msg_no_juego: "El {rol} no tiene Juego.",
        msg_fase_descarte: "Fase: DESCARTE. Selecciona qué cartas quieres tirar.",
        msg_fase_apuestas: "Fase de {fase}. Turno de: {jugador}",
        msg_fase_recuento: "Fase de RECUENTO...",
        msg_fase_general: "Fase: {fase}. Turno de: {jugador}",
        msg_resultados: "Resultados de la ronda:",
        msg_recuento_nover: "(Alguien no quiso ver en {fase})",
        msg_recuento_gana_yo: "<b> Has </b> ganado {puntos} en {fase}.",
        msg_recuento_gana_rival: "<b>El rival ha</b> ganado {puntos} puntos en {fase}.",
        msg_recuento_pedrete_win_yo: "<b>Has</b> ganado la partida con un ¡Pedrete!",
        msg_recuento_pedrete_win_rival: "<b>El rival ha</b> ganado la partida con un ¡Pedrete!",
        msg_error_ronda: "<em>(Hubo un error o la ronda no tuvo apuestas válidas)</em>",
        msg_gana_partida_yo: "🏆 ¡HAS GANADO ESTA PARTIDA!",
        msg_gana_partida_rival: "💀 ¡EL RIVAL HA GANADO ESTA PARTIDA!",
        msg_gana_match_yo: "🏆 ¡HAS GANADO EL MATCH!",
        msg_gana_match_rival: "💀 ¡EL RIVAL HA GANADO EL MATCH!",
        msg_fase_espera_reparto: "Esperando el reparto...",
        txt_tu_sala: "Tu sala",
        btn_unirse_publica: "Unirse",
        msg_no_publicas: "No hay partidas públicas ahora mismo. ¡Crea tú una!",
        txt_cartas_sin_repartir: "[Cartas sin repartir]",
        txt_hola: "Hola",
        btn_jugar_bot: "Jugar contra bot",
        txt_creando_partida_bot: "Creando partida contra un bot...",
        fase_espera_reparto: "Esperando el reparto..."

    },
    en: {
        btn_login: "Log In",
        btn_signup: "Sign Up",
        btn_logout: "Log Out",
        btn_crear: "Create new game",
        btn_unirse: "Join with code",
        btn_show_leaderboard: "View Leaderboard",
        btn_deal: "Deal Cards",
        btn_nomus: "Cut",
        btn_descartar: "Discard",
        btn_next_round: "Next round",
        btn_volver_menu: "Return to Menu",
        btn_envidar: "Bid",
        btn_pasar: "Pass",
        btn_ordago: "Órdago",
        btn_ver: "Call",
        btn_subir: "Raise",
        btn_nover: "Fold",
        btn_ordago_resp: "Órdago",
        al_mejor_de: "Best of:",
        al_mejor_de_colname: "Best of",
        user_colname: "User",
        action_colname: "Action",
        public_games: "🌐 Public Games",
        esperando_rival: "Waiting for opponent to join...",
        in_publico: "Make public (visible to everyone)",
        partidas: "games",
        mi_turno: "⚠️ Your turn",
        my_cards: "Your cards will appear here",
        watermark: "Created by Juan Martín Fajardo",
        login_remember: "Keep me logged in",
        leaderboard_title: "🏆 Global Leaderboard",
        elo_colname: "ELO 🔽",
        wins_colname: "Victorias ↕️",
        winrate_colname: "Winrate ↕️",
        loading_players: "Loading players...",
        codigo_sala: "Your room code:",
        tu_nombre: "Your name...",
        password: "Password",
        signup_birth: "Birthdate:",
        user_name: "Username",
        pais_nacimiento: "Country of birth",
        btn_cuenta: "Create account",
        opponent_speaks: "⚠️ Opponent speaks",
        cartas_rival_ocultas: "[Opponent's cards hidden]",
        txt_tu: "You", 
        txt_pts: "Pts:",
        txt_partidas: "Games:",
        txt_rival: "Opponent",
        codigo_placeholder: "Room code...",
        btn_next_game: "Next game",
        info_tus_cartas: "Your cards will appear here",
        info_esperando_rival_descarte: "Waiting for opponent to discard...",
        info_esperando_rival_listo: "Waiting for opponent to be ready...",
        rival_siguiente_partida: "Waiting for opponent for the next game...",
        info_rival_cambio: "Opponent changed ",
        cartas: " cards",
        has_ganado_partida: "🏆 YOU WON THIS GAME!",
        el_rival_ganado_partida: "💀 YOU LOST THIS GAME!",
        has_ganado_match: "🏆 YOU WON THE MATCH!",
        el_rival_ganado_match: "💀 YOU LOST THE MATCH!",
        info_apuesta_vista: "Bet seen:",
        cartas_sin_repartir: "[Cards not dealt]",
        te_suben: "You are raised: ",
        has_subido: "You raised: ",
        eres_mano: "(You are Mano)",
        eres_postre: "(You are Postre)",
        resultados_ronda: "Results of the round:",
        txt_mano: "Mano",
        txt_postre: "Postre",
        fase_grande: "HIGH",
        fase_chica: "LOW",
        fase_pares: "PAIRS",
        fase_juego: "GAME",
        fase_mus: "MUS",
        msg_nadie_pares: "No one has Pairs.",
        msg_no_pares: "The {rol} doesn't have Pairs.",
        msg_juego_a_punto: "No one has Game. Playing for Point.",
        msg_no_juego: "The {rol} doesn't have Game.",
        msg_fase_descarte: "Phase: DISCARD. Select which cards to throw.",
        msg_fase_apuestas: "Phase {fase}. {jugador}'s turn",
        msg_fase_espera_reparto: "Waiting for the deal...",
        msg_fase_recuento: "Phase COUNTING...",
        msg_fase_general: "Phase: {fase}. {jugador}'s turn",
        msg_resultados: "Results of the round:",
        msg_recuento_nover: "(Someone didn't want to see in {fase})",
        msg_recuento_gana_yo: "<b> You </b> won {puntos} points in {fase}.",
        msg_recuento_gana_rival: "<b>The opponent</b> won {puntos} points in {fase}.",
        msg_recuento_pedrete_win_yo: "<b>You</b> won the match with a ¡Pedrete!",
        msg_recuento_pedrete_win_rival: "<b>The opponent</b> won the match with a ¡Pedrete!",
        msg_error_ronda: "<em>(There was an error or the round had no valid bets)</em>",
        msg_gana_partida_yo: "🏆 YOU WON THIS GAME!",
        msg_gana_partida_rival: "💀 THE OPPONENT WON THIS GAME!",
        msg_gana_match_yo: "🏆 YOU WON THE MATCH!",
        msg_gana_match_rival: "💀 THE OPPONENT WON THE MATCH!",
        txt_tu_sala: "Your room",
        btn_unirse_publica: "Join",
        msg_no_publicas: "There are no public games right now. Create one!",
        txt_cartas_sin_repartir: "[Cards not dealt yet]",
        txt_hola: "Hello",
        btn_jugar_bot: "Play against bot",
        txt_creando_partida_bot: "Creating game against a bot...",
        fase_espera_reparto: "Waiting for the deal..."
    }
};

// Recuperar idioma guardado o usar español por defecto
let langActual = localStorage.getItem('callmus_lang') || 'es';

function t(clave) {
    // Si la clave existe en el idioma actual, la devuelve. Si no, devuelve la propia clave para que te des cuenta del error.
    return (dict[langActual] && dict[langActual][clave]) ? dict[langActual][clave] : clave;
}

// Traduce e inyecta variables dinámicas en la frase
function t_dinamico(clave, variables) {
    let texto = t(clave);
    for (let prop in variables) {
        texto = texto.replace('{' + prop + '}', variables[prop]);
    }
    return texto;
}


function aplicarTraduccion() {
// 1. Traducir todos los elementos estáticos que tengan data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
        let clave = el.getAttribute('data-i18n');
        if (dict[langActual] && dict[langActual][clave]) {
            // NUEVO: Si es un campo de texto, cambiamos el placeholder
            if (el.tagName === 'INPUT') {
                el.placeholder = dict[langActual][clave];
            } else {
                el.innerText = dict[langActual][clave];
            }
        }
    });
    
    // 2. Cambiar el texto del botón de idioma para mostrar la alternativa
    const btnLang = document.getElementById('btn-lang');
    if(btnLang) btnLang.innerText = langActual === 'es' ? 'EN' : 'ES';
}

// Escuchador del botón para alternar
document.getElementById('btn-lang').addEventListener('click', () => {
    langActual = langActual === 'es' ? 'en' : 'es';
    localStorage.setItem('callmus_lang', langActual); // Guardar preferencia
    aplicarTraduccion(); // Traducir todo al vuelo
});

// Ejecutar la primera vez que carga la web
aplicarTraduccion();


// ==========================================
// PANTALLA COMPLETA
// ==========================================
const btnFullscreen = document.getElementById('btn-fullscreen');
if (btnFullscreen) {
    btnFullscreen.addEventListener('click', () => {
        // Si NO estamos en pantalla completa, la pedimos
        if (!document.fullscreenElement) {
            // Se la pedimos al elemento raíz (toda la página)
            document.documentElement.requestFullscreen().catch(err => {
                console.log(`Error al intentar iniciar pantalla completa: ${err.message}`);
            });
        } else {
            // Si ya estamos, salimos
            if (document.exitFullscreen) {
                document.exitFullscreen();
            }
        }
    });
}


// ==========================================
// 1. LÓGICA DEL MENÚ Y SALAS
// ==========================================

const btnCrear = document.getElementById('btn-crear');
const btnUnirse = document.getElementById('btn-unirse');
const inCodigo = document.getElementById('in-codigo');
const menuMsg = document.getElementById('menu-msg');

socket.emit('pedir_publicas');

btnCrear.addEventListener('click', () => {
    miNombre = document.getElementById('nombre-jugador').value.trim() || "Jugador 1";
    let mejorDe = parseInt(document.getElementById('in-mejor-de').value) || 3;
    let esPublico = document.getElementById('in-publico').checked;
    socket.emit('crear_sala', { nombre: miNombre, al_mejor_de: mejorDe, publico: esPublico});
    btnCrear.disabled = true;
    btnUnirse.disabled = true;
    menuMsg.innerText = "Creando sala...";
});

const btnJugarBot = document.getElementById('btn-jugar-bot');

btnJugarBot.addEventListener('click', () => {
    miNombre = document.getElementById('nombre-jugador').value.trim() || "Jugador 1";
    let mejorDe = parseInt(document.getElementById('in-mejor-de').value) || 3;
    
    // Emitimos un nuevo evento específico para el bot
    socket.emit('crear_partida_bot', { nombre: miNombre, al_mejor_de: mejorDe });
    
    btnCrear.disabled = true;
    btnUnirse.disabled = true;
    btnJugarBot.disabled = true;
    menuMsg.innerText = t('txt_creando_partida_bot');
});



btnUnirse.addEventListener('click', () => {
    miNombre = document.getElementById('nombre-jugador').value.trim() || "Jugador 2";
    let cod = inCodigo.value.trim().toUpperCase();
    if (!cod) {
        menuMsg.innerText = "Escribe un código primero.";
        return;
    }
    socket.emit('unirse_sala', { nombre: miNombre, codigo: cod });
    menuMsg.innerText = "Conectando...";
});

document.getElementById('btn-volver-menu').addEventListener('click', () => {
    enPartida = false;
    socket.emit('abandonar_sala_limpiamente');
    setTimeout(() => { window.location.reload(); }, 100);
});

window.addEventListener('beforeunload', (e) => {
    if (enPartida) {
        e.preventDefault();
        e.returnValue = '';
    }
});

socket.on('sala_creada', (datos) => {
    document.getElementById('codigo-creado').classList.remove('hidden');
    document.getElementById('txt-codigo').innerText = datos.codigo;
    menuMsg.innerText = "";
});

socket.on('error_sala', (datos) => {
    menuMsg.innerText = datos.mensaje;
    btnCrear.disabled = false;
    btnUnirse.disabled = false;
});

// Dibujar la tabla de partidas públicas
socket.on('actualizar_publicas', (lista) => {
    const tbody = document.getElementById('lista-partidas-publicas');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (lista.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="padding: 10px; opacity: 0.7;">' + t('msg_no_publicas') + '</td></tr>';        return;
    }

    lista.forEach(partida => {
        const tr = document.createElement('tr');
        
        // SISTEMA ROBUSTO: Es nuestra sala si el ID de conexión es el nuestro, 
        // o si estamos logueados y la sala pertenece a nuestra misma cuenta.
        let esMiSala = false;
        if (partida.creador_sid === socket.id) esMiSala = true;
        if (miUsernameLogueado && partida.creador_username === miUsernameLogueado) esMiSala = true;

        let botonHTML = '';
        if (esMiSala) {
            botonHTML = `<span style="color: #a3be8c; font-size: 0.85em; font-weight: bold;">${t("txt_tu_sala")}</span>`;
        } else {
            botonHTML = `<button class="btn-unirse-publica" data-codigo="${partida.codigo}" style="padding: 5px 10px; font-size: 0.8em; background-color: #81a1c1; border-radius: 4px; cursor: pointer; border: none;">${t("btn_unirse_publica")}</button>`;
        }

        tr.innerHTML = `
            <td style="padding: 8px; border-bottom: 1px solid #4c566a; color: #ebcb8b;">${partida.creador}</td>
            <td style="padding: 8px; border-bottom: 1px solid #4c566a;">${partida.al_mejor_de}</td>
            <td style="padding: 8px; border-bottom: 1px solid #4c566a;">
                ${botonHTML}
            </td>
        `;
        tbody.appendChild(tr);
    });

    // Darle funcionalidad a los botones generados
    document.querySelectorAll('.btn-unirse-publica').forEach(btn => {
        btn.addEventListener('click', (e) => {
            let cod = e.target.getAttribute('data-codigo');
            miNombre = document.getElementById('nombre-jugador').value.trim() || "Jugador 2";
            socket.emit('unirse_sala', { nombre: miNombre, codigo: cod });
            menuMsg.innerText = "Conectando...";
        });
    });
});

socket.on('iniciar_partida', (datos) => {
    menuScreen.classList.add('hidden');
    gameScreen.classList.remove('hidden');
    enPartida = true;
});

socket.on('rival_desconectado', () => {
    if (enPartida) {
        alert("Tu rival se ha desconectado o ha abandonado la partida. Volviendo al menú principal.");
        enPartida = false;
        window.location.reload();
    }
});

// ==========================================
// 2. ACCIONES DE JUEGO AL SERVIDOR
// ==========================================

document.getElementById('btn-deal').addEventListener('click', () => {
    mostrarBotones([]);
    socket.emit('accion_juego', { accion: 'repartir' });
});

document.getElementById('btn-pedrete').addEventListener('click', () => {
    mostrarBotones([]);
    socket.emit('accion_juego', { accion: 'pedrete' });
});


document.getElementById('btn-mus').addEventListener('click', () => {
    mostrarBotones([]);
    socket.emit('accion_juego', { accion: 'mus' });
});

document.getElementById('btn-nomus').addEventListener('click', () => {
    mostrarBotones([]);
    socket.emit('accion_juego', { accion: 'no_mus' });
});

document.getElementById('btn-descartar').addEventListener('click', () => {
    mostrarBotones([]);
    socket.emit('accion_juego', { accion: 'descartar', indices: cartasSeleccionadas });
});

['pasar', 'ver', 'nover', 'ordago', 'ordago-resp'].forEach(id => {
    let el = document.getElementById('btn-' + id);
    if(el) el.addEventListener('click', () => {
        mostrarBotones([]);
        let accion = id === 'ordago-resp' ? 'ordago' : id;
        socket.emit('accion_juego', { accion: accion });
    });
});

document.getElementById('btn-envidar').addEventListener('click', () => {
    mostrarBotones([]);
    let cant = parseInt(document.getElementById('in-envidar').value) || 2;
    let misPuntos = parseInt(document.getElementById('puntos-mios').innerText) || 0;
    if (cant > 40 - misPuntos) cant = 40 - misPuntos;
    socket.emit('accion_juego', { accion: 'envidar', cantidad: cant });
});

document.getElementById('btn-subir').addEventListener('click', () => {
    mostrarBotones([]);
    let cant = parseInt(document.getElementById('in-subir').value) || 2;
    let misPuntos = parseInt(document.getElementById('puntos-mios').innerText) || 0;
    let tope = 40 - misPuntos - apuestaVistaActual;
    if (cant > tope) cant = tope;
    if (cant < 1) cant = 1;
    if (cant > 40 - misPuntos) cant = 40 - misPuntos;
    socket.emit('accion_juego', { accion: 'subir', cantidad: cant });
});

document.getElementById('btn-next-round').addEventListener('click', (e) => {
    mostrarBotones([]);
    document.getElementById('my-cards').innerHTML = '';
    const contenedorRival = document.querySelector('#opponent-area .cards-placeholder');
    if (contenedorRival) contenedorRival.innerHTML = '';

    let textoEspera = e.target.innerText === "Siguiente partida"
        ? `${t('rival_siguiente_partida')}`
        : `${t('info_esperando_rival_listo')}`;

    gameLog.innerHTML = `<strong style='font-size: 1.2em; color: #ebcb8b;'>${textoEspera}</strong>`;
    socket.emit('accion_juego', { accion: 'listo_siguiente_ronda' });
});

// ==========================================
// 3. RECIBIR ESTADO DEL JUEGO
// ==========================================

socket.on('actualizar_mesa', (datos) => {
    // 1. FILTRO: Si el paquete no es para mí, lo ignoro
    if (datos.para_sid !== socket.id) return;
    
    // 2. CHIVATO: Esto imprimirá los datos en la consola si por fin llegan
     console.log("📥 Datos recibidos del servidor:", datos);

    if (!enPartida) {
        document.getElementById('menu-screen').classList.add('hidden');
        document.getElementById('game-screen').classList.remove('hidden');
        enPartida = true;
    }
    
    faseJuego = datos.fase;

    const contenedorRival = document.querySelector('#opponent-area .cards-placeholder');
    if (contenedorRival) {
        if (datos.fase === 'espera_reparto') {
            contenedorRival.innerHTML = t('txt_cartas_sin_repartir');
        } else if (datos.fase !== 'recuento') {
            contenedorRival.innerHTML = `
            <div class="carta"><img src="/static/img/dorso.jpg" draggable="false" oncontextmenu="return false;"></div>
            <div class="carta"><img src="/static/img/dorso.jpg" draggable="false" oncontextmenu="return false;"></div>
            <div class="carta"><img src="/static/img/dorso.jpg" draggable="false" oncontextmenu="return false;"></div>
            <div class="carta"><img src="/static/img/dorso.jpg" draggable="false" oncontextmenu="return false;"></div>
            `;
        }
    }

    const logDiv = document.getElementById('betting-log');
    if (datos.fase === 'apuestas' || datos.fase === 'recuento') {
        logDiv.classList.remove('hidden');

        let fAct = datos.apuestas ? datos.apuestas.fase_actual : '';

        if (datos.fase === 'apuestas' && fAct !== subfaseApuestasActual) {
            subfaseApuestasActual = fAct;
            document.getElementById('in-envidar').value = 2;
            document.getElementById('in-subir').value = 2;
        }

        let gStyle = fAct === t('fase_grande') ? 'color:#ebcb8b; font-weight:bold; font-size:1.1em;' : '';
        let cStyle = fAct === t('fase_chica') ? 'color:#ebcb8b; font-weight:bold; font-size:1.1em;' : '';
        let pStyle = fAct === t('fase_pares') ? 'color:#ebcb8b; font-weight:bold; font-size:1.1em;' : '';
        let jStyle = fAct === t('fase_juego') ? 'color:#ebcb8b; font-weight:bold; font-size:1.1em;' : '';

        let htmlBotes = `
            <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px;">
                <p style="${gStyle}">${t('fase_grande')}: ${datos.apuestas.botes.Grande}</p>
                <p style="${cStyle}">${t('fase_chica')}: ${datos.apuestas.botes.Chica}</p>
                <p style="${pStyle}">${t('fase_pares')}: ${datos.apuestas.botes.Pares}</p>
                <p style="${jStyle}">${t('fase_juego')}: ${datos.apuestas.botes.Juego}</p>
            </div>
        `;

        if (datos.apuestas && (datos.apuestas.subida > 0 || datos.apuestas.subida === 'ÓRDAGO')) {
            const cantidadStr = datos.apuestas.subida === 'ÓRDAGO' ? 'un ÓRDAGO' : datos.apuestas.subida;
            const textoSube = datos.apuestas.soy_quien_sube ? t('has_subido') + cantidadStr : t('te_suben') + cantidadStr;
            const colorSube = datos.apuestas.soy_quien_sube ? `#ebcb8b` : `#bf616a`;

            htmlBotes += `
            <div id="caja-en-aire" style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #88c0d0;">
                <p style="font-size: 1.1em; margin-bottom: 5px;">${t('info_apuesta_vista')} <span class="highlight">${datos.apuestas.apuesta_vista}</span></p>
                <p style="font-size: 1.2em; font-weight: bold; color: ${colorSube}; margin: 0;">${textoSube}</p>
            </div>`;
        }
        logDiv.innerHTML = htmlBotes;
    } else {
        if (logDiv) logDiv.classList.add('hidden');
    }

    if (datos.mensaje_transicion) {
        // NUEVO: Traducir transición dinámica
        let textoTrans = "";
        if (datos.mensaje_transicion.code === 'no_pares' || datos.mensaje_transicion.code === 'no_juego') {
            let rolTrad = datos.mensaje_transicion.rol === 'mano' ? t('txt_mano') : t('txt_postre');
            textoTrans = t_dinamico('msg_' + datos.mensaje_transicion.code, { rol: rolTrad });
        } else {
            textoTrans = t('msg_' + datos.mensaje_transicion.code);
        }
        
        gameLog.innerHTML = `<strong style="color:#ebcb8b; font-size: 1.2em;">${textoTrans}</strong>`;
        mostrarBotones([]);
        if (datos.es_mi_turno) {
            setTimeout(() => socket.emit('accion_juego', { accion: 'continuar_transicion' }), 3000);
        }
        return;
    }

    if (datos.fase === 'recuento') {
        document.getElementById('apuesta-iniciar').classList.add('hidden');
        document.getElementById('apuesta-responder').classList.add('hidden');
        const cajaEnAire = document.getElementById('caja-en-aire');
        if (cajaEnAire) cajaEnAire.classList.add('hidden');
        mostrarRecuentoEstatico(datos);
        return;
    }

    cartasSeleccionadas = [];
    const btnDescartar = document.getElementById('btn-descartar');
    if(btnDescartar) btnDescartar.innerText = `${t('btn_descartar')} (0)`;

    const contenedorCartas = document.getElementById('my-cards');
    contenedorCartas.innerHTML = '';

    if (datos.mis_cartas && datos.mis_cartas.length > 0) {
        datos.mis_cartas.forEach((carta, index) => {
            const div = document.createElement('div');
            div.className = 'carta';
            div.innerHTML = `<img src="${carta.img}" alt="${carta.texto}" draggable="false" oncontextmenu="return false;">`;

            div.onclick = () => {
                if (datos.fase === 'descarte' && !datos.descartes_listos) {
                    const pos = cartasSeleccionadas.indexOf(index);
                    if (pos === -1) {
                        cartasSeleccionadas.push(index);
                        div.classList.add('seleccionada');
                    } else {
                        cartasSeleccionadas.splice(pos, 1);
                        div.classList.remove('seleccionada');
                    }
                    btnDescartar.innerText = `${t('btn_descartar')} (${cartasSeleccionadas.length})`;
                    btnDescartar.disabled = cartasSeleccionadas.length === 0;
                }
            };
            contenedorCartas.appendChild(div);
        });
    } else {
        contenedorCartas.innerHTML = `${t('info_tus_cartas')}`;
    }

    document.getElementById('puntos-mios').innerText = datos.mis_puntos;
    document.getElementById('puntos-rival').innerText = datos.puntos_rival;
    document.getElementById('mi-rol').innerText = datos.soy_mano ? t('eres_mano') : t('eres_postre');
    document.getElementById('mi-turno').classList.toggle('hidden', !datos.es_mi_turno);
    document.getElementById('turno-rival').classList.toggle('hidden', datos.es_mi_turno);

    apuestaVistaActual = datos.apuestas ? datos.apuestas.apuesta_vista : 0;

    let maxApuesta = 40 - datos.mis_puntos;
    let inEnvidar = document.getElementById('in-envidar');
    let inSubir = document.getElementById('in-subir');

    if (inEnvidar) inEnvidar.max = maxApuesta;
    if (inSubir) {
        let topeSubida = maxApuesta - apuestaVistaActual;
        inSubir.max = topeSubida > 0 ? topeSubida : 1;
    }

    if(document.getElementById('partidas-mios')) {
        document.getElementById('partidas-mios').innerText = datos.mis_partidas;
        document.getElementById('partidas-rival').innerText = datos.partidas_rival;
        document.querySelectorAll('.mejor-de-texto').forEach(el => el.innerText = `${t('al_mejor_de')} ${datos.al_mejor_de }`);
    }

    if (datos.fase === 'descarte' && datos.descartes_listos) {
        gameLog.innerText = `${t('info_esperando_rival_descarte')}`;
    } else {
        
        let textoMsg = "";
        if (datos.mensaje) {
            if (datos.mensaje.code === 'fase_apuestas' || datos.mensaje.code === 'fase_general') {
                let nombreFaseTraducida = t('fase_' + datos.mensaje.fase.toLowerCase());
                textoMsg = t_dinamico('msg_' + datos.mensaje.code, { fase: nombreFaseTraducida, jugador: datos.mensaje.jugador });
            } else {
                textoMsg = t('msg_' + datos.mensaje.code);
            }
        }
        
        gameLog.innerText = textoMsg;

        if (datos.descartes_rival > 0 && datos.fase === 'mus') {
            gameLog.innerHTML += `<br><span style="color:#a3be8c; font-size:0.9em;">(${t('info_rival_cambio')} ${datos.descartes_rival} ${t('cartas')})</span>`;
        }
    }

    mostrarBotones([]);
    document.getElementById('apuesta-iniciar').classList.add('hidden');
    document.getElementById('apuesta-responder').classList.add('hidden');

    // Creamos una cesta de botones
    let botonesActivos = [];

    // 1. El pedrete es el rey. Si lo tienes, el botón aparece siempre, sea el turno que sea.
    if (datos.puede_pedrete) {
        botonesActivos.push('btn-pedrete');
    }

    // 2. Lógica normal del resto de fases
    if (datos.fase === 'descarte') {
        if (!datos.descartes_listos) {
            botonesActivos.push('btn-descartar');
        }
        document.getElementById('btn-descartar').disabled = true;
        
    } else if (datos.es_mi_turno) {
        if (datos.fase === 'espera_reparto') {
            botonesActivos.push('btn-deal');
            
        } else if (datos.fase === 'mus') {
            botonesActivos.push('btn-mus', 'btn-nomus');
            
        } else if (datos.fase === 'apuestas') {
            document.getElementById('action-buttons').classList.remove('hidden');

            if (datos.apuestas && datos.apuestas.subida === 0) {
                document.getElementById('apuesta-iniciar').classList.remove('hidden');
            } else if (datos.apuestas) {
                document.getElementById('apuesta-responder').classList.remove('hidden');

                let ocultarSubir = datos.apuestas.subida === 'ÓRDAGO';
                document.getElementById('in-subir').classList.toggle('hidden', ocultarSubir);
                document.getElementById('btn-subir').classList.toggle('hidden', ocultarSubir);
                document.getElementById('btn-ordago-resp').classList.toggle('hidden', ocultarSubir);
            }
        }
    }

    // 3. Mostramos todos los botones de la cesta a la vez
    if (botonesActivos.length > 0) {
        mostrarBotones(botonesActivos);
    }
});

// ==========================================
// 4. UTILIDADES VISUALES
// ==========================================
function mostrarBotones(ids) {
    const contenedor = document.getElementById('action-buttons');
    const allIds = ['btn-deal', 'btn-pedrete', 'btn-mus', 'btn-nomus', 'btn-descartar', 'btn-next-round','btn-volver-menu'];
    allIds.forEach(id => {
        let el = document.getElementById(id);
        if(el) el.classList.add('hidden');
    });
    if (ids.length > 0) {
        contenedor.classList.remove('hidden');
        ids.forEach(id => {
            let el = document.getElementById(id);
            if(el) el.classList.remove('hidden');
        });
    } else {
        contenedor.classList.add('hidden');
    }
}

function mostrarRecuentoEstatico(datos) {
    mostrarBotones([]);

    const contenedorRival = document.querySelector('#opponent-area .cards-placeholder');
    if (contenedorRival) {
        contenedorRival.innerHTML = '';
        if (datos.cartas_rival) {
            datos.cartas_rival.forEach(c => {
                const d = document.createElement('div');
                d.className = 'carta';
                d.innerHTML = `<img src="${c.img}" alt="${c.texto}" draggable="false" oncontextmenu="return false;">`;
                contenedorRival.appendChild(d);
            });
        }
    }

    document.getElementById('puntos-mios').innerText = datos.mis_puntos;
    document.getElementById('puntos-rival').innerText = datos.puntos_rival;

    if(document.getElementById('partidas-mios')) {
        document.getElementById('partidas-mios').innerText = datos.mis_partidas;
        document.getElementById('partidas-rival').innerText = datos.partidas_rival;
    }

const gameLog = document.getElementById('game-log');
    let htmlRecuento = `<strong style='font-size: 1.2em; color: #88c0d0;'>${t('msg_resultados')}</strong><br><br>`;

    if (datos.recuento && datos.recuento.length > 0) {
        for (let paso of datos.recuento) {
            let code = paso.datos.code;
            
            if (code === 'recuento_nover') {
                let nombreFase = t('fase_' + paso.datos.fase.toLowerCase());
                htmlRecuento += `<i>${t_dinamico('msg_recuento_nover', {fase: nombreFase})}</i><br>`;
                
            } else if (code === 'recuento_gana') {
                let nombreFase = t('fase_' + paso.datos.fase.toLowerCase());
                let claveGana = paso.gano_yo ? 'msg_recuento_gana_yo' : 'msg_recuento_gana_rival';
                htmlRecuento += `${t_dinamico(claveGana, {puntos: paso.datos.puntos, fase: nombreFase})}<br>`;
                
            } else if (code === 'recuento_pedrete_win') {
                let claveGana = paso.gano_yo ? 'msg_recuento_pedrete_win_yo' : 'msg_recuento_pedrete_win_rival';
                htmlRecuento += `${t(claveGana)}<br>`;
            }
        }
    } else {
        htmlRecuento += `${t('msg_error_ronda')}<br>`;
    }

    let btnNext = document.getElementById('btn-next-round');

    // Comprobar victorias de partida o match
    if (datos.mis_puntos >= 40 || datos.puntos_rival >= 40) {
        const txt = datos.mis_puntos >= 40 ? t('msg_gana_partida_yo') : t('msg_gana_partida_rival');
        htmlRecuento += `<br><strong style="font-size: 1.5em; color: #a3be8c;">${txt}</strong>`;
        
        if (datos.match_finalizado) {
            const txtGlobal = datos.mis_puntos >= 40 ? t('msg_gana_match_yo') : t('msg_gana_match_rival');
            htmlRecuento += `<br><strong style="font-size: 1.5em; color: #a3be8c;">${txtGlobal}</strong>`;
            gameLog.innerHTML = htmlRecuento;
            mostrarBotones(['btn-volver-menu']);
        } else {
            gameLog.innerHTML = htmlRecuento;
            if (btnNext) btnNext.innerText = t("btn_next_game"); 
            mostrarBotones(['btn-next-round']);
        }
    } else {
        gameLog.innerHTML = htmlRecuento;
        if (btnNext) btnNext.innerText = t("btn_next_round");
        mostrarBotones(['btn-next-round']);
    }
}

// ==========================================
// 5. USUARIOS, MODALES Y FETCH
// ==========================================

const modalOverlay = document.getElementById('modal-overlay');
const modalLogin = document.getElementById('modal-login');
const modalSignup = document.getElementById('modal-signup');

document.getElementById('btn-show-login').addEventListener('click', () => {
    modalOverlay.style.display = 'flex';
    modalOverlay.classList.remove('hidden');
    modalSignup.classList.add('hidden');

    const modalLeaderboard = document.getElementById('modal-leaderboard');
    if (modalLeaderboard) modalLeaderboard.classList.add('hidden');

    modalLogin.classList.remove('hidden');
    document.getElementById('msg-login').innerText = "";
});

document.getElementById('btn-show-signup').addEventListener('click', () => {
    modalOverlay.style.display = 'flex';
    modalOverlay.classList.remove('hidden');
    modalLogin.classList.add('hidden');

    const modalLeaderboard = document.getElementById('modal-leaderboard');
    if (modalLeaderboard) modalLeaderboard.classList.add('hidden');

    modalSignup.classList.remove('hidden');
    document.getElementById('msg-signup').innerText = "";
});

document.querySelectorAll('.btn-cerrar-modal').forEach(btn => {
    btn.addEventListener('click', cerrarModales);
});

modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) cerrarModales();
});

function cerrarModales() {
    modalOverlay.style.display = 'none';
    modalOverlay.classList.add('hidden');
    modalLogin.classList.add('hidden');
    modalSignup.classList.add('hidden');
    const modalLeaderboard = document.getElementById('modal-leaderboard');
    if (modalLeaderboard) modalLeaderboard.classList.add('hidden');
}

let miUsernameLogueado = null; // NUEVO: Variable para recordar quiénes somos

fetch('/auth/sesion').then(res => res.json()).then(datos => {
    if (datos.exito) {
        miUsernameLogueado = datos.usuario.username; // Guardamos nuestro nombre real
        actualizarInterfazLogueado(datos.usuario);
    }
});


function actualizarInterfazLogueado(usuario) {
    document.getElementById('user-buttons').classList.add('hidden');
    document.getElementById('user-info-logged').classList.remove('hidden');
    document.getElementById('txt-user-stats').innerText = t('txt_hola') + `, ${usuario.username}`;

    let inNombre = document.getElementById('nombre-jugador');
    if (inNombre) {
        inNombre.value = usuario.username;
        inNombre.disabled = true;
        inNombre.style.backgroundColor = '#3b4252';
        inNombre.style.color = '#a3be8c';
    }
    cerrarModales();
}

if (document.getElementById('btn-submit-signup')) {
    document.getElementById('btn-submit-signup').addEventListener('click', () => {
        const user = document.getElementById('signup-user').value.trim();
        const pass = document.getElementById('signup-pass').value;
        const country = document.getElementById('signup-country').value.trim();
        const birth = document.getElementById('signup-birth').value;

        if (!user || !pass || !country || !birth) {
            document.getElementById('msg-signup').innerText = "Rellena todos los campos.";
            return;
        }

        document.getElementById('msg-signup').innerText = "Registrando...";

        fetch('/auth/registro', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass, country: country, birthdate: birth })
        }).then(res => res.json()).then(datos => {
            let msgEl = document.getElementById('msg-signup');
            msgEl.innerText = datos.mensaje;
            if (datos.exito) {
                msgEl.style.color = "#a3be8c";
                setTimeout(() => {
                    document.getElementById('btn-show-login').click();
                    document.getElementById('login-user').value = user;
                }, 1500);
            } else {
                msgEl.style.color = "#bf616a";
            }
        });
    });
}

if (document.getElementById('btn-submit-login')) {
    document.getElementById('btn-submit-login').addEventListener('click', () => {
        const user = document.getElementById('login-user').value.trim();
        const pass = document.getElementById('login-pass').value;
        const remember = document.getElementById('login-remember').checked;

        if (!user || !pass) {
            document.getElementById('msg-login').innerText = "Introduce usuario y contraseña.";
            return;
        }

        document.getElementById('msg-login').innerText = "Comprobando...";

        fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass, remember: remember })
        }).then(res => res.json()).then(datos => {
            if (datos.exito) {
                window.location.reload();
            } else {
                document.getElementById('msg-login').innerText = datos.mensaje;
            }
        });
    });
}

document.getElementById('btn-logout').addEventListener('click', () => {
    fetch('/auth/logout', { method: 'POST' }).then(() => {
        window.location.reload();
    });
});

// ==========================================
// 6. LÓGICA DE LA LEADERBOARD
// ==========================================

const modalLeaderboard = document.getElementById('modal-leaderboard');
let leaderboardData = [];
let currentSort = 'elo';
let sortDesc = true;

if (document.getElementById('btn-show-leaderboard')) {
    document.getElementById('btn-show-leaderboard').addEventListener('click', () => {
        modalOverlay.style.display = 'flex';
        modalOverlay.classList.remove('hidden');
        modalLogin.classList.add('hidden');
        modalSignup.classList.add('hidden');
        modalLeaderboard.classList.remove('hidden');

        cargarLeaderboard();
    });
}

function cargarLeaderboard() {
    document.getElementById('lista-leaderboard-body').innerHTML = '<tr><td colspan="4" style="padding: 10px; opacity: 0.7;">Cargando jugadores...</td></tr>';

    fetch('/api/leaderboard').then(res => res.json()).then(datos => {
        if (datos.exito) {
            leaderboardData = datos.leaderboard;
            currentSort = 'elo';
            sortDesc = true;
            renderLeaderboard();
        }
    });
}

function renderLeaderboard() {
    const tbody = document.getElementById('lista-leaderboard-body');
    tbody.innerHTML = '';

    leaderboardData.sort((a, b) => {
        let valA = a[currentSort];
        let valB = b[currentSort];
        if (valA < valB) return sortDesc ? 1 : -1;
        if (valA > valB) return sortDesc ? -1 : 1;
        return 0;
    });

    document.getElementById('th-sort-elo').innerHTML = `ELO ${currentSort === 'elo' ? (sortDesc ? '🔽' : '🔼') : '↕️'}`;
    document.getElementById('th-sort-elo').style.color = currentSort === 'elo' ? '#a3be8c' : '#eceff4';

    document.getElementById('th-sort-wins').innerHTML = `Victorias ${currentSort === 'victorias' ? (sortDesc ? '🔽' : '🔼') : '↕️'}`;
    document.getElementById('th-sort-wins').style.color = currentSort === 'victorias' ? '#a3be8c' : '#eceff4';

    document.getElementById('th-sort-winrate').innerHTML = `Winrate ${currentSort === 'winrate' ? (sortDesc ? '🔽' : '🔼') : '↕️'}`;
    document.getElementById('th-sort-winrate').style.color = currentSort === 'winrate' ? '#a3be8c' : '#eceff4';

    if (leaderboardData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="padding: 10px; opacity: 0.7;">No hay jugadores registrados todavía.</td></tr>';
        return;
    }

    leaderboardData.forEach((jugador, index) => {
        const tr = document.createElement('tr');

        let icono = "";
        if (currentSort === 'elo' && sortDesc) {
            if (index === 0) icono = "🥇 ";
            else if (index === 1) icono = "🥈 ";
            else if (index === 2) icono = "🥉 ";
        }

        tr.innerHTML = `
            <td style="padding: 10px; border-bottom: 1px solid #4c566a; color: #ebcb8b; font-weight: bold;">${icono}${jugador.username}</td>
            <td style="padding: 10px; border-bottom: 1px solid #4c566a; color: #81a1c1; font-weight: bold;">${jugador.elo}</td>
            <td style="padding: 10px; border-bottom: 1px solid #4c566a;">${jugador.victorias}</td>
            <td style="padding: 10px; border-bottom: 1px solid #4c566a;">${jugador.winrate}%</td>
        `;
        tbody.appendChild(tr);
    });
}

document.getElementById('th-sort-elo').addEventListener('click', () => {
    if (currentSort === 'elo') sortDesc = !sortDesc;
    else { currentSort = 'elo'; sortDesc = true; }
    renderLeaderboard();
});

document.getElementById('th-sort-wins').addEventListener('click', () => {
    if (currentSort === 'victorias') sortDesc = !sortDesc;
    else { currentSort = 'victorias'; sortDesc = true; }
    renderLeaderboard();
});

document.getElementById('th-sort-winrate').addEventListener('click', () => {
    if (currentSort === 'winrate') sortDesc = !sortDesc;
    else { currentSort = 'winrate'; sortDesc = true; }
    renderLeaderboard();
});