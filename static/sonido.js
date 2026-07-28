// sonido.js — La voz de la mesa.
//
// Se carga el último, junto a pantalla.js: reutiliza los globales de app.js
// (`dict`, `t`, `aplicarTraduccion`) y no habla con el servidor.
//
// De qué va. En la mesa hay uno (1v1) o tres (2v2) jugadores que no eres tú, y
// muchos de ellos son bots. Todo lo que cantan se pinta un momento —la burbuja
// del 2v2, el tanteador del 1v1— pero si estás mirando tus cartas te lo pierdes:
// «¿ha pasado o me ha envidado?». Aquí cada cante ajeno suena, para que la mesa
// se pueda seguir de oído.
//
// Cómo suena. NO hay ficheros de audio: todo se sintetiza con la Web Audio API,
// que es lo que le conviene a este proyecto —cero peso que servir, cero latencia
// y cada timbre afinado a mano. Dos ideas lo mantienen unido:
//
//   1. UNA PALETA DE TIMBRES, como la de color: campana golpeada (el oro de la
//      interfaz), madera (el tapete) y aire (las cartas). Nada más.
//   2. UNA ESCALA: modo FRIGIO sobre mi —mi fa sol la si do re—, que es el modo
//      español por excelencia. Así dos cantes seguidos nunca chocan, y el
//      semitono que baja (fa→mi) queda reservado para el «no quiero».
//
// Todo pasa por una reverberación corta hecha con ruido, que es lo que separa un
// pitido de un sonido tocado en una habitación.
//
// Sólo suena lo AJENO. Lo que pulsas tú ya lo estás viendo; duplicarlo con un
// sonido convierte la mesa en una máquina recreativa. La única excepción es el
// aviso de turno, que es información sobre ti pero que no has provocado.

(function () {
    'use strict';

    // ======================================================================
    // 1. i18n
    // ======================================================================
    Object.assign(dict.es, {
        sonido_quitar_tooltip: 'Silenciar la mesa',
        sonido_poner_tooltip: 'Oír la mesa',
    });
    Object.assign(dict.en, {
        sonido_quitar_tooltip: 'Mute the table',
        sonido_poner_tooltip: 'Unmute the table',
    });
    Object.assign(dict.eu, {
        sonido_quitar_tooltip: 'Mahaia isilarazi',
        sonido_poner_tooltip: 'Mahaia entzun',
    });
    aplicarTraduccion();

    // ======================================================================
    // 2. Encendido y apagado
    // ======================================================================
    const CLAVE = 'callmus_sonido';
    // Por defecto CON sonido: si no, nadie encuentra el botón y la mesa se queda
    // muda para siempre. El navegador no deja sonar nada hasta que el jugador
    // toca algo, así que abrir la página nunca pilla a nadie por sorpresa.
    let encendido = localStorage.getItem(CLAVE) !== '0';

    // ======================================================================
    // 3. El taller: contexto, salida y reverberación
    // ======================================================================
    let ctx = null;       // AudioContext, creado en el primer gesto del jugador
    let maestro = null;   // ganancia general → altavoces
    let sala = null;      // envío a la reverberación

    /** Ruido blanco de un segundo, reaprovechado por la madera y el aire. */
    let ruidoBuf = null;

    function crear() {
        if (ctx) return true;
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return false;
        try { ctx = new AC(); } catch (e) { return false; }

        maestro = ctx.createGain();
        // 0,9 medido, no elegido a ojo: con 0,55 el pico del órdago se quedaba en
        // 0,23 y el barrido de las cartas en 0,016, que en un móvil a medio
        // volumen no se oye. Aquí el órdago pica en ~0,38 y nada llega a saturar
        // ni sumando dos voces a la vez (lo peor posible: órdago + aviso de
        // turno, ~0,45).
        maestro.gain.value = 0.9;

        // Un paso bajo suave le quita el filo digital a los armónicos altos:
        // es la diferencia entre una campana y una alarma.
        const techo = ctx.createBiquadFilter();
        techo.type = 'lowpass';
        techo.frequency.value = 7200;
        techo.Q.value = 0.4;

        maestro.connect(techo);
        techo.connect(ctx.destination);

        // La habitación. La respuesta al impulso es ruido que se apaga: corta
        // (0,9 s) y oscura, para que suene a sala pequeña y no a catedral.
        try {
            const rev = ctx.createConvolver();
            rev.buffer = impulso(0.9, 3.2);
            const oscura = ctx.createBiquadFilter();
            oscura.type = 'lowpass';
            oscura.frequency.value = 2600;
            sala = ctx.createGain();
            sala.gain.value = 1;
            sala.connect(oscura);
            oscura.connect(rev);
            rev.connect(maestro);
        } catch (e) {
            sala = null;   // sin reverberación se juega igual
        }

        ruidoBuf = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
        const d = ruidoBuf.getChannelData(0);
        for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;

        return true;
    }

    /** Respuesta al impulso: ruido estéreo que decae con una potencia. */
    function impulso(segundos, caida) {
        const n = Math.floor(ctx.sampleRate * segundos);
        const buf = ctx.createBuffer(2, n, ctx.sampleRate);
        for (let c = 0; c < 2; c++) {
            const canal = buf.getChannelData(c);
            for (let i = 0; i < n; i++) {
                canal[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, caida);
            }
        }
        return buf;
    }

    /** Salida de una voz: seco al maestro y una parte al eco de la sala. */
    function salida(nodo, eco) {
        nodo.connect(maestro);
        if (sala && eco) {
            const envio = ctx.createGain();
            envio.gain.value = eco;
            nodo.connect(envio);
            envio.connect(sala);
        }
    }

    // ======================================================================
    // 4. La paleta de timbres
    // ======================================================================

    /** CAMPANA golpeada. Una portadora en seno y un modulador INARMÓNICO
     *  (×3,51) cuyo índice se desploma: eso es lo que convierte un pitido en
     *  algo metálico y tocado. `brillo` mueve la cantidad de metal. */
    function campana(f, t0, dur, vol, brillo) {
        brillo = brillo === undefined ? 1 : brillo;

        const port = ctx.createOscillator();
        port.type = 'sine';
        port.frequency.value = f;

        const mod = ctx.createOscillator();
        mod.type = 'sine';
        mod.frequency.value = f * 3.51;

        const indice = ctx.createGain();
        indice.gain.setValueAtTime(f * 2.4 * brillo, t0);
        indice.gain.exponentialRampToValueAtTime(f * 0.02, t0 + dur * 0.5);
        mod.connect(indice);
        indice.connect(port.frequency);

        const g = ctx.createGain();
        g.gain.setValueAtTime(0.0001, t0);
        g.gain.exponentialRampToValueAtTime(vol, t0 + 0.006);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);

        port.connect(g);
        salida(g, 0.20);

        port.start(t0); port.stop(t0 + dur + 0.05);
        mod.start(t0);  mod.stop(t0 + dur + 0.05);
    }

    /** MADERA: el nudillo en el tapete. Un triángulo que cae de tono en 60 ms
     *  más un pellizco de ruido filtrado que le pone el «toc». */
    function madera(f, t0, vol, dur) {
        dur = dur || 0.10;

        const o = ctx.createOscillator();
        o.type = 'triangle';
        o.frequency.setValueAtTime(f, t0);
        o.frequency.exponentialRampToValueAtTime(f * 0.55, t0 + dur);

        const g = ctx.createGain();
        g.gain.setValueAtTime(0.0001, t0);
        g.gain.exponentialRampToValueAtTime(vol, t0 + 0.004);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);

        o.connect(g);
        salida(g, 0.12);
        o.start(t0); o.stop(t0 + dur + 0.02);

        ruido(t0, 0.028, vol * 0.45, f * 5, 3, 0.08);
    }

    /** RUIDO de banda estrecha: chasquidos y brillos. */
    function ruido(t0, dur, vol, frec, q, eco) {
        if (!ruidoBuf) return;
        const src = ctx.createBufferSource();
        src.buffer = ruidoBuf;
        src.loop = true;

        const bp = ctx.createBiquadFilter();
        bp.type = 'bandpass';
        bp.frequency.value = frec;
        bp.Q.value = q;

        const g = ctx.createGain();
        g.gain.setValueAtTime(0.0001, t0);
        g.gain.exponentialRampToValueAtTime(vol, t0 + 0.004);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);

        src.connect(bp); bp.connect(g);
        salida(g, eco === undefined ? 0.10 : eco);
        src.start(t0); src.stop(t0 + dur + 0.02);
    }

    /** AIRE: las cartas resbalando sobre el paño. Ruido ancho barriendo hacia
     *  arriba, con una entrada y una salida blandas. */
    function aire(t0, dur, f0, f1, vol) {
        if (!ruidoBuf) return;
        const src = ctx.createBufferSource();
        src.buffer = ruidoBuf;
        src.loop = true;
        src.playbackRate.value = 0.85;

        const bp = ctx.createBiquadFilter();
        bp.type = 'bandpass';
        bp.Q.value = 0.9;
        bp.frequency.setValueAtTime(f0, t0);
        bp.frequency.exponentialRampToValueAtTime(f1, t0 + dur);

        const g = ctx.createGain();
        g.gain.setValueAtTime(0.0001, t0);
        g.gain.exponentialRampToValueAtTime(vol, t0 + dur * 0.35);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);

        src.connect(bp); bp.connect(g);
        salida(g, 0.16);
        src.start(t0); src.stop(t0 + dur + 0.02);
    }

    // ======================================================================
    // 5. Las recetas: un cante, un sonido
    // ======================================================================

    // Modo frigio sobre MI. Todas las notas salen de aquí.
    const N = {
        E2: 82.41,
        E3: 164.81, F3: 174.61, G3: 196.00, A3: 220.00, B3: 246.94,
        C4: 261.63, D4: 293.66, E4: 329.63, F4: 349.23, G4: 392.00,
        A4: 440.00, B4: 493.88, C5: 523.25, E5: 659.26, G5: 784.00,
    };

    // Las ganancias de abajo NO están puestas a ojo: se midieron una por una
    // sobre la salida real (pico y energía) y se ajustaron hasta que la jerarquía
    // de la mesa se oye sola —órdago ≫ envite > cante > mus > turno > paso >
    // cartas— con las cartas a unas cuatro veces por debajo de un envite, que es
    // «de fondo» sin llegar a inaudible.
    const RECETAS = {
        // «Mus»: la mesa se pone de acuerdo sin levantar la voz. Dos golpes
        // secos y graves, más un asentimiento que un cante.
        mus(t) {
            madera(N.E3, t, 0.26);
            madera(N.E3, t + 0.095, 0.17);
        },

        // «¡No hay mus!»: se corta. El golpe abre y una campana clara lo remata.
        no_mus(t) {
            madera(N.A3, t, 0.30);
            campana(N.B4, t + 0.03, 0.55, 0.18, 1.2);
        },

        // El reparto: el abanico entero sobre el tapete.
        repartir(t) { aire(t, 0.42, 650, 2500, 0.34); },

        // El descarte: el mismo gesto, más corto, y tanto más largo cuantas más
        // cartas se van (el servidor manda el número).
        descartar(t, n) {
            const cartas = Math.max(1, Math.min(4, n || 1));
            aire(t, 0.13 + cartas * 0.05, 900, 2700, 0.28);
        },

        // «Paso»: un no-suceso. Lo más callado que hay en la mesa; si esto
        // llamara la atención, la mesa entera cansaría a los diez minutos.
        pasar(t) { madera(N.E3 * 0.75, t, 0.26, 0.085); },

        // «Envido»: dos campanas que suben una quinta. Es el oro de la paleta,
        // y por eso el envite es lo primero que se reconoce de oído.
        envidar(t) {
            campana(N.E4, t, 0.80, 0.19);
            campana(N.B4, t + 0.10, 1.15, 0.17, 1.2);
        },

        // «Subo»: la misma idea con tres peldaños y más arriba. Apremia.
        subir(t) {
            campana(N.G4, t, 0.50, 0.17);
            campana(N.C5, t + 0.085, 0.55, 0.16, 1.15);
            campana(N.E5, t + 0.17, 1.00, 0.15, 1.3);
        },

        // «Quiero»: se acepta. Cae de la quinta a la tercera; cálido, resuelto.
        ver(t) {
            campana(N.A4, t, 0.55, 0.17);
            campana(N.F4, t + 0.11, 1.05, 0.175, 0.85);
        },

        // «No quiero»: fa→mi, el semitono frigio que baja, y apagado de brillo.
        // Es la cadencia española de toda la vida y suena exactamente a que no.
        nover(t) {
            campana(N.F4, t, 0.33, 0.15, 0.55);
            campana(N.E4, t + 0.10, 0.60, 0.14, 0.40);
        },

        // «¡ÓRDAGO!»: lo único a lo que se le consiente sonar grande. Un gong
        // en la tónica dos octavas abajo, la octava encima y un brillo que se
        // abre tarde, cuando el golpe ya se ha asentado.
        ordago(t) {
            campana(N.E2, t, 2.8, 0.30, 1.7);
            campana(N.E3, t + 0.015, 2.1, 0.155, 1.4);
            campana(N.B4, t + 0.17, 1.7, 0.095, 1.8);
            ruido(t, 0.55, 0.045, 1500, 1.1, 0.40);
        },

        // «¡Pedrete!»: 4-5-6-7, un punto de regalo y mano nueva. Un destello
        // corto que sube; premio pequeño, alegría pequeña.
        pedrete(t) {
            campana(N.B4, t, 0.30, 0.115, 1.3);
            campana(N.E5, t + 0.06, 0.30, 0.105, 1.35);
            campana(N.G5, t + 0.12, 0.75, 0.095, 1.4);
        },

        // La vuelta de cantes de Pares y Juego no es una jugada: se declara lo
        // que se lleva. Suena más pequeño que un envite, a propósito.
        pares_si(t) {
            campana(N.A4, t, 0.40, 0.105);
            campana(N.C5, t + 0.075, 0.55, 0.095, 1.1);
        },
        pares_no(t) { campana(N.F3, t, 0.45, 0.10, 0.45); },
        juego_si(t) {
            campana(N.B4, t, 0.40, 0.105);
            campana(N.E5, t + 0.075, 0.60, 0.095, 1.15);
        },
        juego_no(t) { campana(N.E3, t, 0.45, 0.10, 0.45); },

        // «Te toca»: información sobre ti que tú no has provocado, y el único
        // sonido que no viene de otro jugador. Lo más discreto de todo.
        turno(t) {
            campana(N.E5, t, 0.28, 0.09, 0.9);
            campana(N.B4, t + 0.10, 0.55, 0.08, 0.8);
        },
    };

    // ======================================================================
    // 6. La puerta de entrada
    // ======================================================================

    // Un mismo cante no se repite si llega dos veces casi a la vez: el 2v2
    // difunde a la sala entera y una reconexión puede duplicar el aviso.
    const ultimaVez = Object.create(null);

    function jugar(nombre, cantidad) {
        if (!encendido) return;
        const receta = RECETAS[nombre];
        if (!receta) return;
        // Pestaña en segundo plano: nada. El navegador además estrangula los
        // temporizadores ahí, así que sonaría tarde y mal.
        if (document.hidden) return;
        if (!crear()) return;
        if (ctx.state === 'suspended') ctx.resume().catch(() => {});
        if (ctx.state !== 'running') return;   // aún sin gesto del jugador

        const ahora = ctx.currentTime;
        if (ultimaVez[nombre] !== undefined && ahora - ultimaVez[nombre] < 0.08) return;
        ultimaVez[nombre] = ahora;

        try { receta(ahora + 0.02, cantidad); } catch (e) { /* que no tumbe la mesa */ }
    }

    // El navegador no deja sonar nada hasta que el jugador toca la página. Se
    // aprovecha el primer gesto que haya —cualquiera vale— para tener el
    // contexto listo antes de que cante nadie.
    function desbloquear() {
        if (!crear()) return;
        if (ctx.state === 'suspended') ctx.resume().catch(() => {});
    }
    ['pointerdown', 'touchstart', 'keydown'].forEach(ev =>
        document.addEventListener(ev, desbloquear, { once: true, passive: true }));

    // ======================================================================
    // 7. El botón 🔊
    // ======================================================================
    const btn = document.getElementById('btn-sonido');

    function pintarBoton() {
        if (!btn) return;
        btn.textContent = encendido ? '🔊' : '🔇';
        btn.classList.toggle('apagado', !encendido);
        btn.setAttribute('aria-pressed', encendido ? 'false' : 'true');
        const clave = encendido ? 'sonido_quitar_tooltip' : 'sonido_poner_tooltip';
        btn.setAttribute('data-i18n-title', clave);
        btn.title = t(clave);
    }

    if (btn) {
        btn.addEventListener('click', () => {
            encendido = !encendido;
            localStorage.setItem(CLAVE, encendido ? '1' : '0');
            pintarBoton();
            // Al volver a encender, una confirmación audible: el aviso de turno,
            // que es el más discreto de todos.
            if (encendido) { desbloquear(); jugar('turno'); }
        });
        pintarBoton();
    }

    // El idioma se cambia desde Ajustes; el tooltip depende del estado, así que
    // se repinta a mano como hace pantalla.js con el de pantalla completa.
    const btnLang = document.getElementById('btn-lang');
    if (btnLang) btnLang.addEventListener('click', () => setTimeout(pintarBoton, 0));

    // ======================================================================
    // 8. Lo que ven app.js y app4.js
    // ======================================================================
    window.Sonido = {
        jugar: jugar,
        activo: () => encendido,
        desbloquear: desbloquear,
    };
})();
