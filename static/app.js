const socket = io({ closeOnBeforeunload: false });

let miNombre = "";
let faseJuego = 'espera';
let cartasSeleccionadas = []; 
let subfaseApuestasActual = "";
let apuestavistaActual = 0;
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
    let checkboxPublico = document.getElementById('in-publico');
    let esPublico = document.getElementById('in-publico').checked;
    // Lo enviamos a Python dentro de los datos
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
   // Damos 100 milisegundos de margen para que el mensaje llegue antes de recargar
    setTimeout(() => { window.location.reload(); }, 100);
});

window.addEventListener('beforeunload', (e) => {
    if (enPartida) {
        // Estas dos líneas son la forma estándar de decirle al navegador que muestre su aviso
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
        tr.innerHTML = `
            <td style="padding: 8px; border-bottom: 1px solid #4c566a; color: #ebcb8b;">${partida.creador}</td>
            <td style="padding: 8px; border-bottom: 1px solid #4c566a;">${partida.al_mejor_de}</td>
            <td style="padding: 8px; border-bottom: 1px solid #4c566a;">
                <button class="btn-unirse-publica" data-codigo="${partida.codigo}" style="padding: 5px 10px; font-size: 0.8em; background-color: #81a1c1;">Unirse</button>
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



// AQUI ESTABA EL FALLO PRINCIPAL: Oculta el menuScreen
socket.on('iniciar_partida', (datos) => {
    menuScreen.classList.add('hidden');
    gameScreen.classList.remove('hidden');
    enPartida = true;
});

socket.on('rival_desconectado', () => {
    if (enPartida) {
        alert("Tu rival se ha desconectado o ha abandonado la partida. Volviendo al menú principal.");
        enPartida = false; // Apagamos el escudo anti-recarga
        window.location.reload(); // Recargamos para limpiar todo
    }
});

// ==========================================
// 2. ACCIONES DE JUEGO AL SERVIDOR
// ==========================================

document.getElementById('btn-deal').addEventListener('click', () => {
    mostrarBotones([]); 
    socket.emit('accion_juego', { accion: 'repartir' });
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
    // Por seguridad, evitamos que la subida sea cero o negativa
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
                // Si estamos esperando a repartir, dejamos el espacio vacío o con un texto
                contenedorRival.innerHTML = '[Cartas sin repartir]';
            } else if (datos.fase !== 'recuento') {
                // Si ya hemos repartido y no estamos en el recuento, mostramos los dorsos
                contenedorRival.innerHTML = `
                <div class="carta"><img src="/static/img/dorso.jpg" draggable="false" oncontextmenu="return false;"></div>
                <div class="carta"><img src="/static/img/dorso.jpg" draggable="false" oncontextmenu="return false;"></div>
                <div class="carta"><img src="/static/img/dorso.jpg" draggable="false" oncontextmenu="return false;"></div>
                <div class="carta"><img src="/static/img/dorso.jpg" draggable="false" oncontextmenu="return false;"></div>
            `;
            }
        }

    // PANEL DE APUESTAS
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
        // Al subir, el máximo visual es lo que falta hasta 40 restando la apuesta actual
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

    if (datos.fase === 'descarte') {
        if (!datos.descartes_listos) mostrarBotones(['btn-descartar']);
        document.getElementById('btn-descartar').disabled = true;
    } else if (datos.es_mi_turno) {
        if (datos.fase === 'espera_reparto') {
            mostrarBotones(['btn-deal']);
        } else if (datos.fase === 'mus') {
            mostrarBotones(['btn-mus', 'btn-nomus']);
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
// LÓGICA DE USUARIOS Y MODALES
// ==========================================

const modalOverlay = document.getElementById('modal-overlay');
const modalLogin = document.getElementById('modal-login');
const modalSignup = document.getElementById('modal-signup');

// Mostrar modal Iniciar Sesión
document.getElementById('btn-show-login').addEventListener('click', () => {
    modalOverlay.style.display = 'flex'; 
    modalOverlay.classList.remove('hidden');
    modalSignup.classList.add('hidden');
    modalLogin.classList.remove('hidden');
    document.getElementById('msg-login').innerText = "";
});

// Mostrar modal Registro
document.getElementById('btn-show-signup').addEventListener('click', () => {
    modalOverlay.style.display = 'flex';
    modalOverlay.classList.remove('hidden');
    modalLogin.classList.add('hidden');
    modalSignup.classList.remove('hidden');
    document.getElementById('msg-signup').innerText = "";
});

// Cerrar modales con la X
document.querySelectorAll('.btn-cerrar-modal').forEach(btn => {
    btn.addEventListener('click', cerrarModales);
});

// Cerrar modales pinchando fuera de la ventana
modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) cerrarModales();
});

function cerrarModales() {
    modalOverlay.style.display = 'none';
    modalOverlay.classList.add('hidden');
    modalLogin.classList.add('hidden');
    modalSignup.classList.add('hidden');
}

// Recoger datos de Registro
document.getElementById('btn-submit-signup').addEventListener('click', () => {
    const user = document.getElementById('signup-user').value.trim();
    const pass = document.getElementById('signup-pass').value;
    const country = document.getElementById('signup-country').value.trim();
    const birth = document.getElementById('signup-birth').value;

    if (!user || !pass || !country || !birth) {
        document.getElementById('msg-signup').innerText = "Por favor, rellena todos los campos.";
        return;
    }
    
    document.getElementById('msg-signup').innerText = "Registrando...";
    socket.emit('intento_registro', { username: user, password: pass, country: country, birthdate: birth });
});

// Recoger datos de Login
document.getElementById('btn-submit-login').addEventListener('click', () => {
    const user = document.getElementById('login-user').value.trim();
    const pass = document.getElementById('login-pass').value;
    const remember = document.getElementById('login-remember').checked;

    if (!user || !pass) {
        document.getElementById('msg-login').innerText = "Introduce usuario y contraseña.";
        return;
    }

    document.getElementById('msg-login').innerText = "Comprobando...";
    socket.emit('intento_login', { username: user, password: pass, remember: remember });
});


// ==========================================
// RESPUESTAS DEL SERVIDOR (LOGIN/REGISTRO)
// ==========================================

// Nada más entrar a la web, preguntamos a Python si tenemos la sesión abierta
// Asegurarnos de que el socket está 100% conectado antes de pedir la sesión
socket.on('connect', () => {
    socket.emit('comprobar_sesion');
});

// Funciones para cambiar la interfaz visual
function actualizarInterfazLogueado(usuario) {
    document.getElementById('user-buttons').classList.add('hidden');
    document.getElementById('user-info-logged').classList.remove('hidden');
    document.getElementById('txt-user-stats').innerText = `Hola, ${usuario.username} (Winrate: ${usuario.winrate}%)`;

    // Bloqueamos el input de nombre y le ponemos el suyo
    let inNombre = document.getElementById('nombre-jugador');
    if (inNombre) {
        inNombre.value = usuario.username;
        inNombre.disabled = true;
        inNombre.style.backgroundColor = '#3b4252';
        inNombre.style.color = '#a3be8c';
    }
    cerrarModales();
}

function actualizarInterfazDeslogueado() {
    document.getElementById('user-buttons').classList.remove('hidden');
    document.getElementById('user-info-logged').classList.add('hidden');

    // Desbloqueamos el input de nombre para invitados
    let inNombre = document.getElementById('nombre-jugador');
    if (inNombre) {
        inNombre.value = "";
        inNombre.disabled = false;
        inNombre.style.backgroundColor = '';
        inNombre.style.color = '';
    }
}

// Escuchadores de eventos
socket.on('registro_respuesta', (datos) => {
    let msgEl = document.getElementById('msg-signup');
    msgEl.innerText = datos.mensaje;
    if (datos.exito) {
        msgEl.style.color = "#a3be8c"; // Verde éxito
        // Si sale bien, le cambiamos al modal de login tras 1.5 segundos
        setTimeout(() => {
            document.getElementById('btn-show-login').click();
            document.getElementById('login-user').value = document.getElementById('signup-user').value;
        }, 1500);
    } else {
        msgEl.style.color = "#bf616a"; // Rojo error
    }
});

socket.on('login_respuesta', (datos) => {
    if (datos.exito) {
        actualizarInterfazLogueado(datos.usuario);
    } else {
        document.getElementById('msg-login').innerText = datos.mensaje;
    }
});

socket.on('sesion_restaurada', (datos) => {
    actualizarInterfazLogueado(datos.usuario);
});

socket.on('sesion_cerrada', () => {
    actualizarInterfazDeslogueado();
});

document.getElementById('btn-logout').addEventListener('click', () => {
    socket.emit('cerrar_sesion');
});