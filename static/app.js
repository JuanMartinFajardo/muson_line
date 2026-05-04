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
        tbody.innerHTML = '<tr><td colspan="3" style="padding: 10px; opacity: 0.7;">No hay partidas públicas ahora mismo. ¡Crea tú una!</td></tr>';
        return;
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
            botonHTML = `<span style="color: #a3be8c; font-size: 0.85em; font-weight: bold;">Tu sala</span>`;
        } else {
            botonHTML = `<button class="btn-unirse-publica" data-codigo="${partida.codigo}" style="padding: 5px 10px; font-size: 0.8em; background-color: #81a1c1; border-radius: 4px; cursor: pointer; border: none;">Unirse</button>`;
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
        ? "Esperando al rival para la siguiente partida..."
        : "Esperando a que el rival esté listo...";

    gameLog.innerHTML = `<strong style='font-size: 1.2em; color: #ebcb8b;'>${textoEspera}</strong>`;
    socket.emit('accion_juego', { accion: 'listo_siguiente_ronda' });
});

// ==========================================
// 3. RECIBIR ESTADO DEL JUEGO
// ==========================================

socket.on('actualizar_mesa', (datos) => {
    faseJuego = datos.fase;

    const contenedorRival = document.querySelector('#opponent-area .cards-placeholder');
    if (contenedorRival) {
        if (datos.fase === 'espera_reparto') {
            contenedorRival.innerHTML = '[Cartas sin repartir]';
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

        let gStyle = fAct === 'Grande' ? 'color:#ebcb8b; font-weight:bold; font-size:1.1em;' : '';
        let cStyle = fAct === 'Chica' ? 'color:#ebcb8b; font-weight:bold; font-size:1.1em;' : '';
        let pStyle = fAct === 'Pares' ? 'color:#ebcb8b; font-weight:bold; font-size:1.1em;' : '';
        let jStyle = fAct === 'Juego' ? 'color:#ebcb8b; font-weight:bold; font-size:1.1em;' : '';

        let htmlBotes = `
            <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px;">
                <p style="${gStyle}">Grande: ${datos.apuestas.botes.Grande}</p>
                <p style="${cStyle}">Chica: ${datos.apuestas.botes.Chica}</p>
                <p style="${pStyle}">Pares: ${datos.apuestas.botes.Pares}</p>
                <p style="${jStyle}">Juego / Punto: ${datos.apuestas.botes.Juego}</p>
            </div>
        `;

        if (datos.apuestas && (datos.apuestas.subida > 0 || datos.apuestas.subida === 'ÓRDAGO')) {
            const cantidadStr = datos.apuestas.subida === 'ÓRDAGO' ? 'un ÓRDAGO' : datos.apuestas.subida;
            const textoSube = datos.apuestas.soy_quien_sube ? `Has subido: ${cantidadStr}` : `Te suben: ${cantidadStr}`;
            const colorSube = datos.apuestas.soy_quien_sube ? `#ebcb8b` : `#bf616a`;

            htmlBotes += `
            <div id="caja-en-aire" style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #88c0d0;">
                <p style="font-size: 1.1em; margin-bottom: 5px;">Apuesta vista: <span class="highlight">${datos.apuestas.apuesta_vista}</span></p>
                <p style="font-size: 1.2em; font-weight: bold; color: ${colorSube}; margin: 0;">${textoSube}</p>
            </div>`;
        }
        logDiv.innerHTML = htmlBotes;
    } else {
        if (logDiv) logDiv.classList.add('hidden');
    }

    if (datos.mensaje_transicion) {
        gameLog.innerHTML = `<strong style="color:#ebcb8b; font-size: 1.2em;">${datos.mensaje_transicion}</strong>`;
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
    if(btnDescartar) btnDescartar.innerText = 'Descartar (0)';

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
                    btnDescartar.innerText = `Descartar (${cartasSeleccionadas.length})`;
                    btnDescartar.disabled = cartasSeleccionadas.length === 0;
                }
            };
            contenedorCartas.appendChild(div);
        });
    } else {
        contenedorCartas.innerHTML = 'Tus cartas aparecerán aquí';
    }

    document.getElementById('puntos-mios').innerText = datos.mis_puntos;
    document.getElementById('puntos-rival').innerText = datos.puntos_rival;
    document.getElementById('mi-rol').innerText = datos.soy_mano ? "(Eres Mano)" : "(Eres Postre)";
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
        document.querySelectorAll('.mejor-de-texto').forEach(el => el.innerText = `(Al mejor de ${datos.al_mejor_de})`);
    }

    if (datos.fase === 'descarte' && datos.descartes_listos) {
        gameLog.innerText = "Esperando a que el rival se descarte...";
    } else {
        gameLog.innerText = datos.mensaje;
        if (datos.descartes_rival > 0 && datos.fase === 'mus') {
            gameLog.innerHTML += `<br><span style="color:#a3be8c; font-size:0.9em;">(El rival cambió ${datos.descartes_rival} cartas)</span>`;
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
    let htmlRecuento = "<strong style='font-size: 1.2em; color: #88c0d0;'>Resultados de la ronda:</strong><br><br>";

    if (datos.recuento && datos.recuento.length > 0) {
        for (let paso of datos.recuento) {
            htmlRecuento += `${paso}<br>`
        }
    } else {
        htmlRecuento += "<em>(Hubo un error o la ronda no tuvo apuestas válidas)</em><br>";
    }

    let btnNext = document.getElementById('btn-next-round');

    if (datos.mis_puntos >= 40 || datos.puntos_rival >= 40) {
        const txt = datos.mis_puntos >= 40 ? "🏆 ¡HAS GANADO ESTA PARTIDA!" : "💀 ¡EL RIVAL HA GANADO ESTA PARTIDA!";
        htmlRecuento += `<br><strong style="font-size: 1.5em; color: #a3be8c;">${txt}</strong>`;

        if (datos.match_finalizado) {
            const txtGlobal = datos.mis_puntos >= 40 ? "🏆 ¡HAS GANADO EL MATCH!" : "💀 ¡EL RIVAL HA GANADO EL MATCH!";
            htmlRecuento += `<br><strong style="font-size: 1.5em; color: #a3be8c;">${txtGlobal}</strong>`;
            gameLog.innerHTML = htmlRecuento;
            mostrarBotones(['btn-volver-menu']);
        } else {
            gameLog.innerHTML = htmlRecuento;
            if (btnNext) btnNext.innerText = "Siguiente partida";
            mostrarBotones(['btn-next-round']);
        }
    } else {
        gameLog.innerHTML = htmlRecuento;
        if (btnNext) btnNext.innerText = "Siguiente ronda";
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
    document.getElementById('txt-user-stats').innerText = `Hola, ${usuario.username} (Winrate: ${usuario.winrate}%)`;

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