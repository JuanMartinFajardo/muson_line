// ==========================================
// ESTILOS DINÁMICOS PARA AMPLIAR CARTAS (UX)
// ==========================================
const tutStyles = document.createElement('style');
tutStyles.innerHTML = `
    .tut-cards-group {
        display: flex;
        justify-content: center;
        transition: transform 0.22s ease-in-out;
        transform-origin: center;
        cursor: pointer;
        touch-action: manipulation;
        position: relative;
        z-index: 10;
    }

    /* Regla limpia para solapar las cartas de los ejemplos */
    .tut-overlap img + img {
        margin-left: -18px;
    }

    /* Súper Zoom en Ordenador (PC) - Incrementado a 1.75x */
    @media (min-width: 769px) {
        .tut-cards-group:hover {
            transform: scale(1.75);
            z-index: 999;
        }
        .tut-cards-group:hover img {
            box-shadow: 0 10px 25px rgba(0,0,0,0.65);
        }
    }

    /* Súper Zoom en Móvil - Incrementado a 1.9x */
    .tut-cards-group.tut-mobile-zoom {
        transform: scale(1.9);
        z-index: 999;
    }
    .tut-cards-group.tut-mobile-zoom img {
        box-shadow: 0 12px 28px rgba(0,0,0,0.75);
    }

    .tut-zoom-hint {
        font-size: 0.72em;
        color: #88c0d0;
        opacity: 0.65;
        margin-top: 6px;
        margin-bottom: 12px;
        font-style: italic;
        letter-spacing: 0.5px;
        display: block;
        text-align: center;
    }

    /* ---------- Índice: las tres pistas ---------- */
    .tut-hub { display: flex; flex-direction: column; gap: 12px; }
    .tut-hub-btn {
        display: flex; align-items: center; gap: 14px;
        width: 100%; padding: 15px 14px;
        background: #3b4252;
        border: 1px solid #4c566a;
        border-left: 4px solid var(--tc, #a3be8c);
        border-radius: 8px;
        color: #eceff4; text-align: left; cursor: pointer;
        transition: background 0.18s ease, transform 0.18s ease;
    }
    .tut-hub-btn:hover { background: #434c5e; transform: translateX(3px); }
    .tut-hub-ico { flex: 0 0 40px; font-size: 1.8em; text-align: center; }
    .tut-hub-btn b { display: block; color: var(--tc, #a3be8c); font-size: 1.05em; margin-bottom: 3px; }
    .tut-hub-btn small { display: block; color: #d8dee9; font-size: 0.85em; font-weight: normal; line-height: 1.35; }

    /* ---------- Piezas comunes de las diapositivas nuevas ---------- */
    .tut-lead { font-size: 1.05em; color: #eceff4; margin: 0 0 16px; }
    .tut-col { display: flex; flex-direction: column; gap: 10px; text-align: left; }
    .tut-box {
        background: #3b4252;
        border-left: 4px solid var(--tc, #88c0d0);
        border-radius: 4px;
        padding: 10px 14px;
        text-align: left;
    }
    .tut-box .tt { display: block; color: var(--tc, #88c0d0); font-weight: bold; font-size: 1.02em; margin-bottom: 5px; }
    .tut-box p { margin: 0; font-size: 0.92em; color: #d8dee9; line-height: 1.45; }
    .tut-box p + p { margin-top: 7px; }
    .tut-tip {
        background: rgba(235, 203, 139, 0.1);
        border-left: 4px solid #ebcb8b;
        border-radius: 0 4px 4px 0;
        padding: 10px 12px; margin-top: 14px;
        color: #eceff4; font-size: 0.92em; text-align: left; line-height: 1.45;
    }
    .tut-nota { display: block; margin-top: 16px; font-size: 0.82em; color: #88c0d0; opacity: 0.75; font-style: italic; }
    .tut-goto {
        display: block; width: 100%; margin-top: 16px; padding: 12px;
        background: #4c566a; color: #eceff4;
        border: none; border-radius: 8px;
        font-size: 0.95em; font-weight: bold; cursor: pointer;
        transition: background 0.18s ease;
    }
    .tut-goto:hover { background: #5e6b82; }
    .tut-key {
        display: inline-block; min-width: 20px; padding: 1px 6px;
        background: #2e3440; border: 1px solid #4c566a; border-bottom-width: 2px;
        border-radius: 4px;
        font-family: monospace; font-size: 0.85em; color: #eceff4;
    }

    /* ---------- La mesa de cuatro (asientos / regiones de foco) ---------- */
    .tut-mesa {
        display: grid; grid-template-columns: repeat(3, 1fr);
        gap: 8px; align-items: center;
        margin: 0 auto 16px; max-width: 340px;
    }
    .tut-mesa .s-t { grid-column: 2; grid-row: 1; }
    .tut-mesa .s-l { grid-column: 1; grid-row: 2; }
    .tut-mesa .s-c { grid-column: 2; grid-row: 2; }
    .tut-mesa .s-r { grid-column: 3; grid-row: 2; }
    .tut-mesa .s-b { grid-column: 2; grid-row: 3; }
    .tut-seat {
        background: #3b4252; border: 1px solid #4c566a; border-radius: 8px;
        padding: 8px 5px; font-size: 0.78em; color: #d8dee9; text-align: center;
    }
    .tut-seat b { display: block; color: #eceff4; font-size: 1.05em; }
    .tut-seat small { display: block; color: #88c0d0; font-size: 0.92em; }
    .tut-seat.eqA { border-color: #ebcb8b; }
    .tut-seat.eqB { border-color: #81a1c1; }
    .tut-seat.yo { background: #434c5e; }
    .tut-mesa-centro { font-size: 0.72em; color: #6c7686; text-align: center; line-height: 1.4; }

    /* ---------- Fichas de seña (la cara hace el gesto en bucle) ---------- */
    .tut-senas { display: flex; flex-direction: column; gap: 8px; }
    .tut-sena {
        display: flex; align-items: center; gap: 12px;
        background: #3b4252; border: 1px solid #434c5e; border-radius: 6px;
        padding: 7px 10px; text-align: left;
    }
    /* La caja respeta el 64x74 del viewBox de la cara: los gestos de boca hay
       que poder distinguirlos, así que no se puede achatar. */
    .tut-sena-cara { flex: 0 0 52px; width: 52px; height: 60px; }
    .tut-sena-txt { flex: 1 1 auto; min-width: 0; }
    .tut-sena-nom { display: block; color: #ebcb8b; font-weight: bold; font-size: 0.9em; }
    .tut-sena-mano { display: block; color: #eceff4; font-size: 0.84em; }
    .tut-sena-gesto { display: block; color: #88c0d0; font-size: 0.78em; font-style: italic; }

    /* El título tiene que dejar sitio a los dos botones redondos de las esquinas
       (índice y cerrar), que van por encima del contenido. */
    .tut-titulo { padding: 0 42px; }

    /* El contenido va centrado en vertical, pero cuando no cabe hay que dejar
       de centrarlo: si no, se recorta por ARRIBA y no hay forma de subir. El
       !important es porque el centrado viene en el style= del propio div; si el
       navegador no entiende "safe", tira la regla entera y se queda como estaba. */
    #tutorial-content { justify-content: safe center !important; }

    @media (max-width: 480px) {
        .tut-titulo { padding: 0 40px; font-size: 1.45em !important; }
        /* Con trece diapositivas los puntitos se comen la barra: en un móvil se
           encogen para que los dos botones quepan enteros. */
        #tut-nav { padding: 12px 10px; }
        #tut-prev, #tut-next { padding: 8px 10px; font-size: 0.84em; white-space: nowrap; }
        #tut-dots { gap: 5px !important; flex-wrap: wrap; justify-content: center; }
        #tut-dots div { width: 7px !important; height: 7px !important; }
    }
`;
document.head.appendChild(tutStyles);



// ==========================================
// MOTOR DEL TUTORIAL DE MUS (BILINGÜE ES/EN)
// ==========================================
// El tutorial son TRES PISTAS independientes, más un índice que las presenta:
//
//   · '1v1'   — las reglas del mus desde cero (`dictTut1v1`).
//   · '2v2'   — sólo lo que cambia al jugar por parejas (`dictTut2v2`).
//   · 'senas' — los diez gestos y sus reglas (`dictTutSenas`).
//
// Cada pista es un array de diapositivas `{title, content}` por idioma, indexado
// por la variable global `langActual` que define app.js (única fuente de verdad
// del idioma; se persiste en localStorage con la clave 'callmus_lang'). Los dos
// idiomas de una pista tienen SIEMPRE el mismo número de diapositivas y el mismo
// orden, para que los índices (en el 1v1: slide 8 = práctica, slide 9 = Ejemplo 1)
// sean idénticos en ambos.
//
// `content` puede ser una cadena o una FUNCIÓN que la devuelva: las señas se
// generan al pintar porque necesitan la cara SVG de senas4.js, que se carga
// después de este archivo.

const dictTut1v1 = {
    es: [
        {
            title: "La Baraja Española",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">El Mus se juega con la baraja española tradicional de 40 cartas, dividida en 4 palos.</p>

                <div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 25px;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🪙<br><span style="font-size: 0.8em; color: #88c0d0;">Oros</span></div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🍷<br><span style="font-size: 0.8em; color: #88c0d0;">Copas</span></div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">⚔️<br><span style="font-size: 0.8em; color: #88c0d0;">Espadas</span></div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🏏<br><span style="font-size: 0.8em; color: #88c0d0;">Bastos</span></div>
                </div>

                <p style="font-size: 1em; color: #d8dee9; margin-bottom: 15px;">Cada palo contiene números del <b>1 al 7</b> y tres "Figuras" especiales:</p>

                <div class="tut-cards-group" style="gap: 12px; align-items: center; margin: 0 auto; max-width: max-content; padding: 5px;">
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">Sota (10)</span>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <img src="/static/img/card_coins_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">Caballo (11)</span>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">Rey (12)</span>
                    </div>
                </div>
                <span class="tut-zoom-hint">🔍 Pasa el ratón o toca las figuras para ampliar</span>
            `
        },
        {
            title: "El Secreto Real: los 3 y los 2",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">En el Mus no existen los 3 ni los 2 de verdad. ¡Son impostores! Se juega con 8 Reyes y 8 Ases.</p>

                <div style="background: rgba(46, 52, 64, 0.6); border: 1px solid #4c566a; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                    <p style="margin-top: 0; color: #ebcb8b; font-weight: bold;">Cada 3 es un Rey</p>
                    <div style="display: flex; justify-content: center; align-items: center; gap: 15px;">
                        <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px;">
                        <span style="font-size: 2em; color: #a3be8c;">&rarr;</span>
                        <img src="/static/img/card_cups_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 0 15px rgba(235, 203, 139, 0.5);">
                    </div>
                </div>

                <div style="background: rgba(46, 52, 64, 0.6); border: 1px solid #4c566a; border-radius: 8px; padding: 15px;">
                    <p style="margin-top: 0; color: #88c0d0; font-weight: bold;">Cada 2 es un As (1)</p>
                    <div style="display: flex; justify-content: center; align-items: center; gap: 15px;">
                        <img src="/static/img/card_coins_02.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px;">
                        <span style="font-size: 2em; color: #a3be8c;">&rarr;</span>
                        <img src="/static/img/card_coins_01.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 0 15px rgba(136, 192, 208, 0.5);">
                    </div>
                </div>
            `
        },
        {
            title: "La Fase de Mus (Descartes)",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">Tras repartir 4 cartas, los jugadores deciden si quieren descartarse para mejorar sus manos. A esto se le llama pedir <b>"Mus"</b>.</p>

                <div style="display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 20px; font-size: 0.9em;">

                    <div style="background: #4c566a; color: white; padding: 10px 20px; border-radius: 20px; font-weight: bold;">
                        1. Reparto de 4 cartas
                    </div>

                    <div style="color: #88c0d0;">&darr;</div>

                    <div style="background: #3b4252; border: 2px solid #88c0d0; color: #eceff4; padding: 15px; border-radius: 8px; text-align: center; width: 80%;">
                        <b>¿Quieren Mus AMBOS jugadores?</b>
                    </div>

                    <div style="display: flex; justify-content: space-between; width: 90%; margin-top: 5px;">
                        <div style="display: flex; flex-direction: column; align-items: center; width: 45%;">
                            <div style="color: #a3be8c; font-weight: bold; margin-bottom: 5px;">SÍ</div>
                            <div style="color: #a3be8c;">&darr;</div>
                            <div style="background: rgba(163, 190, 140, 0.2); border: 1px solid #a3be8c; color: #a3be8c; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9em;">
                                Descarta 1-4 cartas.<br>Roba otras nuevas.<br><i>(Se repite)</i>
                            </div>
                        </div>

                        <div style="display: flex; flex-direction: column; align-items: center; width: 45%;">
                            <div style="color: #bf616a; font-weight: bold; margin-bottom: 5px;">NO (Corto)</div>
                            <div style="color: #bf616a;">&darr;</div>
                            <div style="background: rgba(191, 97, 106, 0.2); border: 1px solid #bf616a; color: #bf616a; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9em;">
                                El reparto se detiene.<br>Empiezan las apuestas.
                            </div>
                        </div>
                    </div>
                </div>

                <p style="font-size: 0.9em; color: #d8dee9; font-style: italic;">* Si tienes una buena mano, ¡corta el Mus para evitar que el rival mejore la suya!</p>
            `
        },
        {
            title: "Los 4 Lances de Apuestas",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 15px;">Una vez cortado el Mus, se apuesta por turnos en 4 lances distintos:</p>

                <div style="display: flex; flex-direction: column; gap: 10px; text-align: left;">

                    <div style="background: #3b4252; border-left: 5px solid #ebcb8b; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #ebcb8b; font-size: 1.1em;">⬆️ Grande</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">Ganan las cartas más altas. (Reyes > Caballos > Sotas...)</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #88c0d0; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #88c0d0; font-size: 1.1em;">⬇️ Chica</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">Ganan las cartas más bajas. (Ases > 4 > 5...)</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #b48ead; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #b48ead; font-size: 1.1em;">👯 Pares</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">Solo puedes apostar si tienes 2 o más cartas iguales. (Duples > Medias > Pares simples).</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #a3be8c; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #a3be8c; font-size: 1.1em;">🎯 Juego</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">Suma el valor de tus cartas (Figuras = 10). Necesitas <b>31 o más</b>. La mejor es 31, seguida de 32, luego 40, 37, 36, 35, 34 y por último 33. <br><i>*Si nadie llega a 31, se juega al "Punto" más alto.</i></p>
                    </div>

                </div>
            `
        },
        {
            title: "El Lenguaje de las Apuestas",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">Durante un lance puedes iniciar una apuesta o responder a ella. Este es tu arsenal:</p>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left;">

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #a3be8c; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Envido</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">Apuestas 2 puntos.</div>
                    </div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #4c566a; color: white; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Paso</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">No apuestas. Si ambos pasan, el lance se queda en 0 puntos.</div>
                    </div>

                    <div style="width: 100%; height: 1px; background: #4c566a; margin: 5px 0;"></div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #88c0d0; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Quiero</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">Aceptas la apuesta (<b>Quiero</b> / Ver). Los puntos quedan reservados hasta el final.</div>
                    </div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #bf616a; color: white; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">No quiero</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">Te retiras (<b>No quiero</b>). El rival gana al instante 1 punto (o la apuesta anterior).</div>
                    </div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #ebcb8b; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Órdago</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;"><b>¡A TODO O NADA!</b> Si se acepta, ¡la partida termina de inmediato!</div>
                    </div>

                </div>
            `
        },
        {
            title: "Mano vs. Postre",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">La posición lo es todo en el Mus. Los roles se intercambian en cada ronda.</p>

                <div style="display: flex; justify-content: space-between; gap: 15px; margin-bottom: 20px;">

                    <div style="background: #3b4252; border: 2px solid #ebcb8b; border-radius: 8px; padding: 15px; width: 48%; position: relative;">
                        <div style="position: absolute; top: -15px; left: 50%; transform: translateX(-50%); font-size: 1.5em;">👑</div>
                        <h3 style="color: #ebcb8b; margin-top: 10px; margin-bottom: 5px;">Mano</h3>
                        <p style="font-size: 0.9em; color: #d8dee9; text-align: left; margin: 0;">
                            • Habla <b>primero</b>.<br>
                            • Gana todos los <b>empates</b> absolutos.<br>
                        </p>
                    </div>

                    <div style="background: #3b4252; border: 2px solid #81a1c1; border-radius: 8px; padding: 15px; width: 48%;">
                        <h3 style="color: #81a1c1; margin-top: 10px; margin-bottom: 5px;">Postre</h3>
                        <p style="font-size: 0.9em; color: #d8dee9; text-align: left; margin: 0;">
                            • Habla el <b>último</b> (gran ventaja de información).<br>
                            • Necesita cartas estrictamente mejores para ganar.
                        </p>
                    </div>

                </div>

                <div style="background: rgba(235, 203, 139, 0.1); border-left: 4px solid #ebcb8b; padding: 10px; color: #eceff4; font-size: 0.95em; text-align: left;">
                    <b>La Regla de Oro:</b> Si tienes exactamente las mismas cartas que el rival, ¡la Mano siempre gana!
                </div>
            `
        },
        {
            title: "La Fase de Recuento (Puntos)",
            content: `
                <p style="font-size: 1em; color: #eceff4; margin-bottom: 15px;">Al final de la ronda se muestran las cartas. El ganador de cada lance se lleva las <b>apuestas</b> de la mesa, más los <b>puntos de bonificación</b> por las cartas que tengas:</p>

                <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 45%; text-align: left;">
                        <div style="color: #88c0d0; font-weight: bold; margin-bottom: 5px;">Grande y Chica</div>
                        <div style="font-size: 0.85em; color: #d8dee9;">Sin bonificación. Solo ganas las apuestas realizadas (o 1 pt si ambos pasaron).</div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 45%; text-align: left;">
                        <div style="color: #a3be8c; font-weight: bold; margin-bottom: 5px;">Punto</div>
                        <div style="font-size: 0.85em; color: #d8dee9;">Ganar el Punto da <span style="color:#a3be8c; font-weight:bold;">+1 pt</span>.</div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 93%; text-align: left; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="color: #b48ead; font-weight: bold; margin-bottom: 5px;">Pares</div>
                            <div style="font-size: 0.85em; color: #d8dee9;">Pares simples: <span style="color:#a3be8c; font-weight:bold;">+1 pt</span><br>Medias (trío): <span style="color:#a3be8c; font-weight:bold;">+2 pts</span><br>Duples (dos parejas): <span style="color:#a3be8c; font-weight:bold;">+3 pts</span></div>
                        </div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 93%; text-align: left; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px;">Juego</div>
                            <div style="font-size: 0.85em; color: #d8dee9;">Tener 31 exacto: <span style="color:#a3be8c; font-weight:bold;">+3 pts</span><br>Tener de 32 a 40: <span style="color:#a3be8c; font-weight:bold;">+2 pts</span></div>
                        </div>
                    </div>

                </div>
            `
        },
        {
            title: "Secretos Avanzados",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 15px;">Dos manos poco frecuentes pero muy poderosas que debes conocer:</p>

                <div style="display: flex; flex-direction: column; gap: 15px; text-align: left;">
                    <div style="background: #3b4252; border-left: 5px solid #d08770; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #d08770; font-size: 1.1em;">🃏 Pedrete (4-5-6-7)</strong>
                        <div class="tut-cards-group" style="display: flex; gap: 5px; margin: 10px 0;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_coins_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_clubs_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint" style="margin-bottom: 0;">🔍 Pasa el ratón o toca las cartas para ampliar</span>
                        <p style="margin: 0; font-size: 0.95em; color: #d8dee9;">Es la peor mano, así que como compensación ¡te da al instante <b style="color:#a3be8c;">+1 pt</b> y robas 4 cartas nuevas! Pero <b>debes cantarlo</b> durante la fase de Mus, antes de que el rival corte.</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #ebcb8b; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #ebcb8b; font-size: 1.1em;">👑 La Real</strong>
                        <div class="tut-cards-group" style="display: flex; gap: 5px; margin: 10px 0;">
                            <img src="/static/img/card_coins_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint" style="margin-bottom: 0;">🔍 Pasa el ratón o toca las cartas para ampliar</span>
                        <p style="margin: 0; font-size: 0.95em; color: #d8dee9;">Tres 7 y una Sota (10) forman el 31 supremo. ¡Esta mano <b>siempre gana el Juego</b>, incluso siendo Postre!</p>
                    </div>
                </div>
            `
        },
        {
            title: "¿Listo para Practicar?",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 25px;">Ya conoces la teoría. Ahora veamos cómo se juega en la mesa.</p>

                <div style="display: flex; flex-direction: column; gap: 15px; align-items: center; margin-top: 30px;">
                    <button onclick="window.goToSlide(9)" style="width: 85%; background: #81a1c1; color: #2e3440; font-weight: bold; padding: 15px; border-radius: 8px; font-size: 1.1em; border: none; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">📖 Leer Ejemplos (Paso a Paso)</button>

                    <button id="btn-start-interactive" style="width: 85%; background: #a3be8c; color: #2e3440; font-weight: bold; padding: 15px; border-radius: 8px; font-size: 1.1em; border: none; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">🎮 Empezar a Practicar</button>
                </div>
            `
        },
        {
            title: "Ej. 1: Grande y Chica (el 'No quiero')",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">El Jugador 1 tiene cartas geniales para GRANDE, pero el J2 es fuerte en CHICA.</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J1 (Mano)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Ampliar</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J2 (Postre)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_01.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_02.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Ampliar</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #ebcb8b;">
                        <strong style="color: #ebcb8b; font-size: 1.1em;">⬆️ GRANDE</strong><br>
                        <span style="color: #ebcb8b;">J1:</span> <b>Envida 2.</b><br>
                        <span style="color: #81a1c1;">J2:</span> Sabe que el 6 y el As son pésimos para Grande. <b>No quiere.</b><br>
                        <div style="margin-top: 5px; color: #a3be8c;"><b>Resultado:</b> J1 gana al instante <b>1 punto</b> (el envite no querido).</div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #88c0d0;">
                        <strong style="color: #88c0d0; font-size: 1.1em;">⬇️ CHICA</strong><br>
                        <span style="color: #ebcb8b;">J1:</span> Pasa.<br>
                        <span style="color: #81a1c1;">J2:</span> <b>Envida 2.</b><br>
                        <span style="color: #ebcb8b;">J1:</span> Farolea y <b>quiere (Ver)</b>.<br>
                        <div style="margin-top: 5px; color: #a3be8c;"><b>Resultado:</b> 2 puntos reservados. ¡J2 los ganará en el recuento!</div>
                    </div>
                </div>
            `
        },
        {
            title: "Ej. 2: Choque de Pares",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">Tener una pareja de Reyes está bien, pero las medias (trío) son mejores.</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J1 (Pareja)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Ampliar</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J2 (Medias)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Ampliar</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #b48ead;">
                        <strong style="color: #b48ead; font-size: 1.1em;">👯 PARES</strong><br>
                        <span style="color: #eceff4; font-style: italic;">Ambos declaran que tienen pares.</span><br>
                        <span style="color: #ebcb8b;">J1:</span> Confía en los Reyes. <b>Envida 2.</b><br>
                        <span style="color: #81a1c1;">J2:</span> ¡Tiene medias! <b>Sube a 4.</b><br>
                        <span style="color: #ebcb8b;">J1:</span> <b>Quiere (Ver).</b><br>
                        <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                            <b>Recuento final:</b> J2 muestra los tres 4 y aplasta a los Reyes del J1. <br>¡J2 se lleva los <b>4 puntos apostados</b> + <b>2 pts de bonificación</b> por las medias!
                        </div>
                    </div>
                </div>
            `
        },
        {
            title: "Ej. 3: 31 vs 32",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">En el Juego, 31 es la mejor de todas. ¡32 es la peor!</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J1 (Suma 32)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Ampliar</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J2 (Suma 31)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Ampliar</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                        <strong style="color: #a3be8c; font-size: 1.1em;">🎯 JUEGO</strong><br>
                        <span style="color: #eceff4; font-style: italic;">Ambos llegan a 31 o más.</span><br>
                        <span style="color: #ebcb8b;">J1:</span> Soy Mano, quizá 32 baste. <b>Envida 2.</b><br>
                        <span style="color: #81a1c1;">J2:</span> ¡Tengo 31 justo! <b>¡ÓRDAGO!</b><br>
                        <span style="color: #ebcb8b;">J1:</span> Sabe que 32 es pésimo. <b>No quiere.</b><br>
                        <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                            <b>Recuento final:</b> J2 se lleva los 2 puntos apostados de inmediato. Al final, ¡J2 también consigue <b>+3 pts de bonificación</b> por tener 31!
                        </div>
                    </div>
                </div>
            `
        },
        {
            title: "Ej. 4: Jugando al Punto",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">Si nadie llega a 31, se juega al "Punto" (gana la suma más alta).</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J1 (Suma 29)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Ampliar</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J2 (Suma 28)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Ampliar</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                        <strong style="color: #a3be8c; font-size: 1.1em;">🎯 PUNTO</strong><br>
                        <span style="color: #eceff4; font-style: italic;">"Nadie tiene Juego. Se juega al Punto."</span><br>
                        <span style="color: #ebcb8b;">J1:</span> 29 está muy cerca de 30 (el punto máximo). <b>Envida 2.</b><br>
                        <span style="color: #81a1c1;">J2:</span> Tengo 28, ¿quizá baste? <b>Quiere (Ver).</b><br>
                        <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                            <b>Recuento final:</b> J1 muestra 29, J2 muestra 28. ¡Gana J1!<br>J1 se lleva los <b>2 puntos apostados</b> + <b>1 pt de bonificación</b> por ganar el Punto.
                        </div>
                    </div>
                </div>
            `
        }
    ],

    en: [
        {
            title: "The Spanish Deck",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">Mus is played with a traditional 40-card Spanish deck, divided into 4 suits.</p>

                <div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 25px;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🪙<br><span style="font-size: 0.8em; color: #88c0d0;">Coins</span></div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🍷<br><span style="font-size: 0.8em; color: #88c0d0;">Cups</span></div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">⚔️<br><span style="font-size: 0.8em; color: #88c0d0;">Swords</span></div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🏏<br><span style="font-size: 0.8em; color: #88c0d0;">Clubs</span></div>
                </div>

                <p style="font-size: 1em; color: #d8dee9; margin-bottom: 15px;">Each suit contains numbers from <b>1 to 7</b>, and three special "Figures":</p>

                <div class="tut-cards-group" style="gap: 12px; align-items: center; margin: 0 auto; max-width: max-content; padding: 5px;">
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">Jack (10)</span>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <img src="/static/img/card_coins_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">Knight (11)</span>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">King (12)</span>
                    </div>
                </div>
                <span class="tut-zoom-hint">🔍 Hover or tap figures to zoom</span>
            `
        },
        {
            title: "The Royal Secret: 3s & 2s",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">In Mus, there are no actual 3s or 2s. They are impostors! We play with 8 Kings and 8 Aces.</p>

                <div style="background: rgba(46, 52, 64, 0.6); border: 1px solid #4c566a; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                    <p style="margin-top: 0; color: #ebcb8b; font-weight: bold;">Every 3 is a King</p>
                    <div style="display: flex; justify-content: center; align-items: center; gap: 15px;">
                        <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px;">
                        <span style="font-size: 2em; color: #a3be8c;">&rarr;</span>
                        <img src="/static/img/card_cups_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 0 15px rgba(235, 203, 139, 0.5);">
                    </div>
                </div>

                <div style="background: rgba(46, 52, 64, 0.6); border: 1px solid #4c566a; border-radius: 8px; padding: 15px;">
                    <p style="margin-top: 0; color: #88c0d0; font-weight: bold;">Every 2 is an Ace (1)</p>
                    <div style="display: flex; justify-content: center; align-items: center; gap: 15px;">
                        <img src="/static/img/card_coins_02.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px;">
                        <span style="font-size: 2em; color: #a3be8c;">&rarr;</span>
                        <img src="/static/img/card_coins_01.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 0 15px rgba(136, 192, 208, 0.5);">
                    </div>
                </div>
            `
        },
        {
            title: "The Mus Phase (Discards)",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">After dealing 4 cards, players decide if they want to discard to improve their hands. This is called asking for <b>"Mus"</b>.</p>

                <div style="display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 20px; font-size: 0.9em;">

                    <div style="background: #4c566a; color: white; padding: 10px 20px; border-radius: 20px; font-weight: bold;">
                        1. Deal 4 cards
                    </div>

                    <div style="color: #88c0d0;">&darr;</div>

                    <div style="background: #3b4252; border: 2px solid #88c0d0; color: #eceff4; padding: 15px; border-radius: 8px; text-align: center; width: 80%;">
                        <b>Do BOTH players want Mus?</b>
                    </div>

                    <div style="display: flex; justify-content: space-between; width: 90%; margin-top: 5px;">
                        <div style="display: flex; flex-direction: column; align-items: center; width: 45%;">
                            <div style="color: #a3be8c; font-weight: bold; margin-bottom: 5px;">YES</div>
                            <div style="color: #a3be8c;">&darr;</div>
                            <div style="background: rgba(163, 190, 140, 0.2); border: 1px solid #a3be8c; color: #a3be8c; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9em;">
                                Discard 1-4 cards.<br>Draw new ones.<br><i>(Loop back)</i>
                            </div>
                        </div>

                        <div style="display: flex; flex-direction: column; align-items: center; width: 45%;">
                            <div style="color: #bf616a; font-weight: bold; margin-bottom: 5px;">NO (Cut)</div>
                            <div style="color: #bf616a;">&darr;</div>
                            <div style="background: rgba(191, 97, 106, 0.2); border: 1px solid #bf616a; color: #bf616a; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9em;">
                                The dealing stops.<br>Betting starts immediately.
                            </div>
                        </div>
                    </div>
                </div>

                <p style="font-size: 0.9em; color: #d8dee9; font-style: italic;">* If you have a good hand, cut the Mus to prevent the opponent from improving theirs!</p>
            `
        },
        {
            title: "The 4 Betting Phases",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 15px;">Once the Mus is cut, players bet sequentially in 4 distinct phases:</p>

                <div style="display: flex; flex-direction: column; gap: 10px; text-align: left;">

                    <div style="background: #3b4252; border-left: 5px solid #ebcb8b; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #ebcb8b; font-size: 1.1em;">⬆️ Grande (High)</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">The highest cards win. (Kings > Knights > Jacks...)</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #88c0d0; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #88c0d0; font-size: 1.1em;">⬇️ Chica (Low)</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">The lowest cards win. (Aces > 4s > 5s...)</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #b48ead; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #b48ead; font-size: 1.1em;">👯 Pares (Pairs)</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">You can only bet if you have 2 or more matching cards. (2 pairs > 3 of a kind > 1 pair).</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #a3be8c; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #a3be8c; font-size: 1.1em;">🎯 Juego (Game)</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">Sum the value of your cards (Figures = 10). You need <b>31 or more</b>. The best is 31, followed by 32, then 40, then 37, 36, 35, 34, and finally 33. <br><i>*If nobody reaches 31, we play for the closest "Punto" (Point).</i></p>
                    </div>

                </div>
            `
        },
        {
            title: "The Betting Language",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">During a phase, you can start a bet or respond to one. Here is your arsenal:</p>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left;">

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #a3be8c; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Bid</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">You bet 2 points.</div>
                    </div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #4c566a; color: white; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Pass</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">You don't bet. If both pass, the phase is left at 0 points.</div>
                    </div>

                    <div style="width: 100%; height: 1px; background: #4c566a; margin: 5px 0;"></div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #88c0d0; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Call</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">You <b>Call</b> the bet. The points are locked until the end.</div>
                    </div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #bf616a; color: white; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Fold</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">You <b>Fold</b>. The opponent instantly wins 1 point (or the previous bet).</div>
                    </div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #ebcb8b; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Órdago</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;"><b>ALL-IN!</b> If accepted, the game ends immediately!</div>
                    </div>

                </div>
            `
        },
        {
            title: "Mano vs. Postre",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">Position is everything in Mus. The roles swap every round.</p>

                <div style="display: flex; justify-content: space-between; gap: 15px; margin-bottom: 20px;">

                    <div style="background: #3b4252; border: 2px solid #ebcb8b; border-radius: 8px; padding: 15px; width: 48%; position: relative;">
                        <div style="position: absolute; top: -15px; left: 50%; transform: translateX(-50%); font-size: 1.5em;">👑</div>
                        <h3 style="color: #ebcb8b; margin-top: 10px; margin-bottom: 5px;">Mano (Hand)</h3>
                        <p style="font-size: 0.9em; color: #d8dee9; text-align: left; margin: 0;">
                            • Speaks <b>first</b>.<br>
                            • Wins all absolute <b>ties</b>.<br>
                        </p>
                    </div>

                    <div style="background: #3b4252; border: 2px solid #81a1c1; border-radius: 8px; padding: 15px; width: 48%;">
                        <h3 style="color: #81a1c1; margin-top: 10px; margin-bottom: 5px;">Postre (Last)</h3>
                        <p style="font-size: 0.9em; color: #d8dee9; text-align: left; margin: 0;">
                            • Speaks <b>last</b> (huge information advantage).<br>
                            • Must have strictly better cards to win.
                        </p>
                    </div>

                </div>

                <div style="background: rgba(235, 203, 139, 0.1); border-left: 4px solid #ebcb8b; padding: 10px; color: #eceff4; font-size: 0.95em; text-align: left;">
                    <b>The Golden Rule:</b> If you have exactly the same cards as the opponent, the Mano always wins!
                </div>
            `
        },
        {
            title: "The Counting Phase (Points)",
            content: `
                <p style="font-size: 1em; color: #eceff4; margin-bottom: 15px;">At the end of the round, you reveal your cards. The winner of each phase gets the <b>Bets</b> from the table, plus <b>Bonus Points</b> for the cards you hold:</p>

                <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 45%; text-align: left;">
                        <div style="color: #88c0d0; font-weight: bold; margin-bottom: 5px;">Grande & Chica (High & Low)</div>
                        <div style="font-size: 0.85em; color: #d8dee9;">No bonus points. You only win the bets placed (or 1 pt if both passed).</div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 45%; text-align: left;">
                        <div style="color: #a3be8c; font-weight: bold; margin-bottom: 5px;">Punto (Point)</div>
                        <div style="font-size: 0.85em; color: #d8dee9;">Winning the Punto gives <span style="color:#a3be8c; font-weight:bold;">+1 pt</span>.</div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 93%; text-align: left; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="color: #b48ead; font-weight: bold; margin-bottom: 5px;">Pares (Pairs)</div>
                            <div style="font-size: 0.85em; color: #d8dee9;">Simple Pair: <span style="color:#a3be8c; font-weight:bold;">+1 pt</span><br>Three of a kind: <span style="color:#a3be8c; font-weight:bold;">+2 pts</span><br>Two Pairs: <span style="color:#a3be8c; font-weight:bold;">+3 pts</span></div>
                        </div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 93%; text-align: left; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px;">Juego (Game)</div>
                            <div style="font-size: 0.85em; color: #d8dee9;">Having 31 exactly: <span style="color:#a3be8c; font-weight:bold;">+3 pts</span><br>Having 32 to 40: <span style="color:#a3be8c; font-weight:bold;">+2 pts</span></div>
                        </div>
                    </div>

                </div>
            `
        },
        {
            title: "Advanced Secrets",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 15px;">Two rare but powerful hands you must know:</p>

                <div style="display: flex; flex-direction: column; gap: 15px; text-align: left;">
                    <div style="background: #3b4252; border-left: 5px solid #d08770; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #d08770; font-size: 1.1em;">🃏 Pedrete (4-5-6-7)</strong>
                        <div class="tut-cards-group" style="display: flex; gap: 5px; margin: 10px 0;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_coins_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_clubs_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint" style="margin-bottom: 0;">🔍 Hover or tap cards to zoom</span>
                        <p style="margin: 0; font-size: 0.95em; color: #d8dee9;">This is the worst hand, so to compensate for it, instantly gives you <b style="color:#a3be8c;">+1 pt</b> and you draw 4 new cards! But you <b>must claim it</b> during the Mus phase, before your opponent cuts.</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #ebcb8b; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #ebcb8b; font-size: 1.1em;">👑 La Real (Royal)</strong>
                        <div class="tut-cards-group" style="display: flex; gap: 5px; margin: 10px 0;">
                            <img src="/static/img/card_coins_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint" style="margin-bottom: 0;">🔍 Hover or tap cards to zoom</span>
                        <p style="margin: 0; font-size: 0.95em; color: #d8dee9;">Three 7s and a Jack (10) form the ultimate 31. This hand <b>always wins the Game phase</b>, even if you are the Postre!</p>
                    </div>
                </div>
            `
        },
        {
            title: "Ready to Practice?",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 25px;">You know the theory. Now let's see how it plays out on the table.</p>

                <div style="display: flex; flex-direction: column; gap: 15px; align-items: center; margin-top: 30px;">
                    <button onclick="window.goToSlide(9)" style="width: 85%; background: #81a1c1; color: #2e3440; font-weight: bold; padding: 15px; border-radius: 8px; font-size: 1.1em; border: none; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">📖 Read Examples (Step by Step)</button>

                    <button id="btn-start-interactive" style="width: 85%; background: #a3be8c; color: #2e3440; font-weight: bold; padding: 15px; border-radius: 8px; font-size: 1.1em; border: none; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">🎮 Start Practising</button>
                </div>
            `
        },
        {
            title: "Ex 1: High & Low (The Fold)",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">Player 1 has great cards for HIGH, but P2 is strong in LOW.</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P1 (Mano)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Zoom</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P2 (Postre)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_01.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_02.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Zoom</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #ebcb8b;">
                        <strong style="color: #ebcb8b; font-size: 1.1em;">⬆️ HIGH (Grande)</strong><br>
                        <span style="color: #ebcb8b;">P1:</span> <b>Bids 2.</b><br>
                        <span style="color: #81a1c1;">P2:</span> Knows 6 and Ace are terrible for High. <b>Folds (No Ver).</b><br>
                        <div style="margin-top: 5px; color: #a3be8c;"><b>Result:</b> P1 instantly wins <b>1 point</b> (the uncalled bet).</div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #88c0d0;">
                        <strong style="color: #88c0d0; font-size: 1.1em;">⬇️ LOW (Chica)</strong><br>
                        <span style="color: #ebcb8b;">P1:</span> Passes.<br>
                        <span style="color: #81a1c1;">P2:</span> <b>Bids 2.</b><br>
                        <span style="color: #ebcb8b;">P1:</span> Bluffs and <b>Calls (Ver)</b>.<br>
                        <div style="margin-top: 5px; color: #a3be8c;"><b>Result:</b> 2 points locked. P2 will win them during the counting phase!</div>
                    </div>
                </div>
            `
        },
        {
            title: "Ex 2: Clash of Pairs",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">Having a pair of Kings is good, but 3 of a kind is better.</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P1 (Pair)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Zoom</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P2 (3 of a kind)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Zoom</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #b48ead;">
                        <strong style="color: #b48ead; font-size: 1.1em;">👯 PAIRS (Pares)</strong><br>
                        <span style="color: #eceff4; font-style: italic;">Both declare they have pairs.</span><br>
                        <span style="color: #ebcb8b;">P1:</span> Trusts the Kings. <b>Bids 2.</b><br>
                        <span style="color: #81a1c1;">P2:</span> Has 3 of a kind! <b>Raises to 4.</b><br>
                        <span style="color: #ebcb8b;">P1:</span> <b>Calls (Ver).</b><br>
                        <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                            <b>Final Count:</b> P2 reveals the three 4s and crushes P1's Kings. <br>P2 takes the <b>4 bet points</b> + <b>2 bonus pts</b> for the 3 of a kind!
                        </div>
                    </div>
                </div>
            `
        },
        {
            title: "Ex 3: 31 vs 32",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">In Game (Juego), 31 is the absolute best. 32 is the worst!</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P1 (Sum 32)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Zoom</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P2 (Sum 31)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Zoom</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                        <strong style="color: #a3be8c; font-size: 1.1em;">🎯 GAME (Juego)</strong><br>
                        <span style="color: #eceff4; font-style: italic;">Both reach 31 or more.</span><br>
                        <span style="color: #ebcb8b;">P1:</span> I'm the Mano, 32 might be enough. <b>Bids 2.</b><br>
                        <span style="color: #81a1c1;">P2:</span> I have exactly 31! <b>ÓRDAGO!</b><br>
                        <span style="color: #ebcb8b;">P1:</span> Knows 32 is terrible. <b>Folds (No Ver).</b><br>
                        <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                            <b>Final Count:</b> P2 takes the 2 bet points immediately. At the end, P2 will also get <b>+3 bonus pts</b> for having 31!
                        </div>
                    </div>
                </div>
            `
        },
        {
            title: "Ex 4: Playing for the Point",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">If nobody reaches 31, we play "Punto" (highest sum wins).</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P1 (Sum 29)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Zoom</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P2 (Sum 28)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Zoom</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                        <strong style="color: #a3be8c; font-size: 1.1em;">🎯 POINT (Punto)</strong><br>
                        <span style="color: #eceff4; font-style: italic;">"Nobody has Game. Playing for Point."</span><br>
                        <span style="color: #ebcb8b;">P1:</span> 29 is very close to 30 (the max point). <b>Bids 2.</b><br>
                        <span style="color: #81a1c1;">P2:</span> I have 28, maybe it's enough? <b>Calls (Ver).</b><br>
                        <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                            <b>Final Count:</b> P1 reveals 29, P2 reveals 28. P1 wins!<br>P1 takes the <b>2 bet points</b> + <b>1 bonus pt</b> for winning the Point.
                        </div>
                    </div>
                </div>
            `
        }
    ],

    eu: [
        {
            title: "Espainiako karta-sorta",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">Musa Espainiako 40 kartako karta-sorta tradizionalarekin jokatzen da, lau palotan banatuta.</p>

                <div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 25px;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🪙<br><span style="font-size: 0.8em; color: #88c0d0;">Urreak</span></div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🍷<br><span style="font-size: 0.8em; color: #88c0d0;">Kopak</span></div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">⚔️<br><span style="font-size: 0.8em; color: #88c0d0;">Ezpatak</span></div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🏏<br><span style="font-size: 0.8em; color: #88c0d0;">Bastoiak</span></div>
                </div>

                <p style="font-size: 1em; color: #d8dee9; margin-bottom: 15px;">Palo bakoitzak <b>1etik 7ra</b> bitarteko zenbakiak ditu eta hiru "Figura" berezi:</p>

                <div class="tut-cards-group" style="gap: 12px; align-items: center; margin: 0 auto; max-width: max-content; padding: 5px;">
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">Txanka (10)</span>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <img src="/static/img/card_coins_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">Zaldia (11)</span>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">Erregea (12)</span>
                    </div>
                </div>
                <span class="tut-zoom-hint">🔍 Pasatu sagua edo ukitu figurak handitzeko</span>
            `
        },
        {
            title: "Errege-sekretua: 3ak eta 2ak",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">Musean ez dago benetako 3rik ez 2rik. Iruzurtiak dira! 8 Erregerekin eta 8 Asekin jokatzen da.</p>

                <div style="background: rgba(46, 52, 64, 0.6); border: 1px solid #4c566a; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                    <p style="margin-top: 0; color: #ebcb8b; font-weight: bold;">3 bakoitza Errege bat da</p>
                    <div style="display: flex; justify-content: center; align-items: center; gap: 15px;">
                        <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px;">
                        <span style="font-size: 2em; color: #a3be8c;">&rarr;</span>
                        <img src="/static/img/card_cups_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 0 15px rgba(235, 203, 139, 0.5);">
                    </div>
                </div>

                <div style="background: rgba(46, 52, 64, 0.6); border: 1px solid #4c566a; border-radius: 8px; padding: 15px;">
                    <p style="margin-top: 0; color: #88c0d0; font-weight: bold;">2 bakoitza As bat da (1)</p>
                    <div style="display: flex; justify-content: center; align-items: center; gap: 15px;">
                        <img src="/static/img/card_coins_02.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px;">
                        <span style="font-size: 2em; color: #a3be8c;">&rarr;</span>
                        <img src="/static/img/card_coins_01.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 0 15px rgba(136, 192, 208, 0.5);">
                    </div>
                </div>
            `
        },
        {
            title: "Mus fasea (deskarteak)",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">4 karta banatu ondoren, jokalariek erabakitzen dute kartak bota nahi dituzten eskua hobetzeko. Horri <b>"Mus"</b> eskatzea esaten zaio.</p>

                <div style="display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 20px; font-size: 0.9em;">

                    <div style="background: #4c566a; color: white; padding: 10px 20px; border-radius: 20px; font-weight: bold;">
                        1. 4 kartaren banaketa
                    </div>

                    <div style="color: #88c0d0;">&darr;</div>

                    <div style="background: #3b4252; border: 2px solid #88c0d0; color: #eceff4; padding: 15px; border-radius: 8px; text-align: center; width: 80%;">
                        <b>BI jokalariek nahi dute musa?</b>
                    </div>

                    <div style="display: flex; justify-content: space-between; width: 90%; margin-top: 5px;">
                        <div style="display: flex; flex-direction: column; align-items: center; width: 45%;">
                            <div style="color: #a3be8c; font-weight: bold; margin-bottom: 5px;">BAI</div>
                            <div style="color: #a3be8c;">&darr;</div>
                            <div style="background: rgba(163, 190, 140, 0.2); border: 1px solid #a3be8c; color: #a3be8c; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9em;">
                                1-4 karta botatzen dira.<br>Beste horrenbeste hartzen dira.<br><i>(Errepikatu egiten da)</i>
                            </div>
                        </div>

                        <div style="display: flex; flex-direction: column; align-items: center; width: 45%;">
                            <div style="color: #bf616a; font-weight: bold; margin-bottom: 5px;">EZ (Mus ez)</div>
                            <div style="color: #bf616a;">&darr;</div>
                            <div style="background: rgba(191, 97, 106, 0.2); border: 1px solid #bf616a; color: #bf616a; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9em;">
                                Banaketa gelditu egiten da.<br>Apustuak hasten dira.
                            </div>
                        </div>
                    </div>
                </div>

                <p style="font-size: 0.9em; color: #d8dee9; font-style: italic;">* Esku ona baduzu, moztu musa aurkariak berea hobetu ez dezan!</p>
            `
        },
        {
            title: "Apustuen 4 lanceak",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 15px;">Musa moztu ondoren, txandaka egiten da apustu 4 lance ezberdinetan:</p>

                <div style="display: flex; flex-direction: column; gap: 10px; text-align: left;">

                    <div style="background: #3b4252; border-left: 5px solid #ebcb8b; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #ebcb8b; font-size: 1.1em;">⬆️ Handia</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">Karta altuenek irabazten dute. (Erregeak > Zaldiak > Txankak...)</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #88c0d0; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #88c0d0; font-size: 1.1em;">⬇️ Txikia</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">Karta baxuenek irabazten dute. (Asak > 4 > 5...)</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #b48ead; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #b48ead; font-size: 1.1em;">👯 Pareak</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">2 karta berdin edo gehiago badituzu bakarrik egin dezakezu apustu. (Duplak > Mediak > Pare soilak).</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #a3be8c; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #a3be8c; font-size: 1.1em;">🎯 Jokoa</strong>
                        <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">Batu zure karten balioa (Figurak = 10). <b>31 edo gehiago</b> behar duzu. Onena 31 da, gero 32, ondoren 40, 37, 36, 35, 34 eta azkenik 33. <br><i>*Inor 31era iristen ez bada, "Puntu" altuenera jokatzen da.</i></p>
                    </div>

                </div>
            `
        },
        {
            title: "Apustuen hizkuntza",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">Lance batean apustu bat has dezakezu edo hari erantzun. Hau da zure arsenala:</p>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left;">

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #a3be8c; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Envido</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">2 puntu apustatzen dituzu.</div>
                    </div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #4c566a; color: white; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Paso</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">Ez duzu apustatzen. Biek pasatzen badute, lancea 0 puntutan geratzen da.</div>
                    </div>

                    <div style="width: 100%; height: 1px; background: #4c566a; margin: 5px 0;"></div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #88c0d0; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Nahi dut</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">Apustua onartzen duzu (<b>Nahi dut</b> / Ikusi). Puntuak amaierara arte gordeta geratzen dira.</div>
                    </div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #bf616a; color: white; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Ez dut nahi</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">Erretiratu egiten zara (<b>Ez dut nahi</b>). Aurkariak berehala irabazten du puntu 1 (edo aurreko apustua).</div>
                    </div>

                    <div style="display: flex; gap: 10px;">
                        <div style="background: #ebcb8b; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Hordago</div>
                        <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;"><b>DENA EDO EZER EZ!</b> Onartzen bada, partida berehala amaitzen da!</div>
                    </div>

                </div>
            `
        },
        {
            title: "Eskua vs. Postrea",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">Musean posizioa da dena. Rolak esku bakoitzean trukatzen dira.</p>

                <div style="display: flex; justify-content: space-between; gap: 15px; margin-bottom: 20px;">

                    <div style="background: #3b4252; border: 2px solid #ebcb8b; border-radius: 8px; padding: 15px; width: 48%; position: relative;">
                        <div style="position: absolute; top: -15px; left: 50%; transform: translateX(-50%); font-size: 1.5em;">👑</div>
                        <h3 style="color: #ebcb8b; margin-top: 10px; margin-bottom: 5px;">Eskua</h3>
                        <p style="font-size: 0.9em; color: #d8dee9; text-align: left; margin: 0;">
                            • <b>Lehenengo</b> hitz egiten du.<br>
                            • <b>Berdinketa</b> guztiak irabazten ditu.<br>
                        </p>
                    </div>

                    <div style="background: #3b4252; border: 2px solid #81a1c1; border-radius: 8px; padding: 15px; width: 48%;">
                        <h3 style="color: #81a1c1; margin-top: 10px; margin-bottom: 5px;">Postrea</h3>
                        <p style="font-size: 0.9em; color: #d8dee9; text-align: left; margin: 0;">
                            • <b>Azkena</b> hitz egiten du (informazio-abantaila handia).<br>
                            • Karta hertsiki hobeak behar ditu irabazteko.
                        </p>
                    </div>

                </div>

                <div style="background: rgba(235, 203, 139, 0.1); border-left: 4px solid #ebcb8b; padding: 10px; color: #eceff4; font-size: 0.95em; text-align: left;">
                    <b>Urrezko araua:</b> aurkariaren karta berberak badituzu, Eskuak beti irabazten du!
                </div>
            `
        },
        {
            title: "Zenbaketa fasea (puntuak)",
            content: `
                <p style="font-size: 1em; color: #eceff4; margin-bottom: 15px;">Eskuaren amaieran kartak erakusten dira. Lance bakoitzeko irabazleak mahaiko <b>apustuak</b> eramaten ditu, gehi dituzun kartengatiko <b>hobari-puntuak</b>:</p>

                <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 45%; text-align: left;">
                        <div style="color: #88c0d0; font-weight: bold; margin-bottom: 5px;">Handia eta Txikia</div>
                        <div style="font-size: 0.85em; color: #d8dee9;">Hobaririk gabe. Egindako apustuak baino ez dituzu irabazten (edo pnt 1 biek pasatu badute).</div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 45%; text-align: left;">
                        <div style="color: #a3be8c; font-weight: bold; margin-bottom: 5px;">Puntua</div>
                        <div style="font-size: 0.85em; color: #d8dee9;">Puntua irabazteak <span style="color:#a3be8c; font-weight:bold;">+1 pnt</span> ematen du.</div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 93%; text-align: left; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="color: #b48ead; font-weight: bold; margin-bottom: 5px;">Pareak</div>
                            <div style="font-size: 0.85em; color: #d8dee9;">Pare soilak: <span style="color:#a3be8c; font-weight:bold;">+1 pnt</span><br>Mediak (hirukotea): <span style="color:#a3be8c; font-weight:bold;">+2 pnt</span><br>Duplak (bi pare): <span style="color:#a3be8c; font-weight:bold;">+3 pnt</span></div>
                        </div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 93%; text-align: left; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px;">Jokoa</div>
                            <div style="font-size: 0.85em; color: #d8dee9;">31 zehatza izatea: <span style="color:#a3be8c; font-weight:bold;">+3 pnt</span><br>32tik 40ra izatea: <span style="color:#a3be8c; font-weight:bold;">+2 pnt</span></div>
                        </div>
                    </div>

                </div>
            `
        },
        {
            title: "Sekretu aurreratuak",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 15px;">Gutxitan gertatzen diren baina oso indartsuak diren bi esku, ezagutu behar dituzunak:</p>

                <div style="display: flex; flex-direction: column; gap: 15px; text-align: left;">
                    <div style="background: #3b4252; border-left: 5px solid #d08770; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #d08770; font-size: 1.1em;">🃏 Pedrete (4-5-6-7)</strong>
                        <div class="tut-cards-group" style="display: flex; gap: 5px; margin: 10px 0;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_coins_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_clubs_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint" style="margin-bottom: 0;">🔍 Pasatu sagua edo ukitu kartak handitzeko</span>
                        <p style="margin: 0; font-size: 0.95em; color: #d8dee9;">Eskurik txarrena da, eta konpentsazio gisa berehala ematen dizu <b style="color:#a3be8c;">+1 pnt</b> eta 4 karta berri hartzen dituzu! Baina <b>kantatu egin behar duzu</b> mus fasean, aurkariak moztu baino lehen.</p>
                    </div>

                    <div style="background: #3b4252; border-left: 5px solid #ebcb8b; padding: 10px 15px; border-radius: 4px;">
                        <strong style="color: #ebcb8b; font-size: 1.1em;">👑 Erreala</strong>
                        <div class="tut-cards-group" style="display: flex; gap: 5px; margin: 10px 0;">
                            <img src="/static/img/card_coins_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint" style="margin-bottom: 0;">🔍 Pasatu sagua edo ukitu kartak handitzeko</span>
                        <p style="margin: 0; font-size: 0.95em; color: #d8dee9;">Hiru 7k eta Txanka batek (10) 31 gorena osatzen dute. Esku honek <b>Jokoa beti irabazten du</b>, Postre izanda ere!</p>
                    </div>
                </div>
            `
        },
        {
            title: "Praktikatzeko prest?",
            content: `
                <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 25px;">Teoria badakizu jada. Ikus dezagun orain nola jokatzen den mahaian.</p>

                <div style="display: flex; flex-direction: column; gap: 15px; align-items: center; margin-top: 30px;">
                    <button onclick="window.goToSlide(9)" style="width: 85%; background: #81a1c1; color: #2e3440; font-weight: bold; padding: 15px; border-radius: 8px; font-size: 1.1em; border: none; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">📖 Adibideak irakurri (urratsez urrats)</button>

                    <button id="btn-start-interactive" style="width: 85%; background: #a3be8c; color: #2e3440; font-weight: bold; padding: 15px; border-radius: 8px; font-size: 1.1em; border: none; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">🎮 Praktikatzen hasi</button>
                </div>
            `
        },
        {
            title: "1. adib.: Handia eta Txikia ('Ez dut nahi')",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">1. jokalariak karta bikainak ditu HANDIRAKO, baina 2.a indartsua da TXIKIAN.</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J1 (Eskua)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Handitu</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J2 (Postrea)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_01.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_02.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Handitu</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #ebcb8b;">
                        <strong style="color: #ebcb8b; font-size: 1.1em;">⬆️ HANDIA</strong><br>
                        <span style="color: #ebcb8b;">J1:</span> <b>2 envidatzen ditu.</b><br>
                        <span style="color: #81a1c1;">J2:</span> Badaki 6a eta Asa negargarriak direla Handirako. <b>Ez du nahi.</b><br>
                        <div style="margin-top: 5px; color: #a3be8c;"><b>Emaitza:</b> J1ek berehala irabazten du <b>puntu 1</b> (nahi izan ez den envitea).</div>
                    </div>

                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #88c0d0;">
                        <strong style="color: #88c0d0; font-size: 1.1em;">⬇️ TXIKIA</strong><br>
                        <span style="color: #ebcb8b;">J1:</span> Pasatu.<br>
                        <span style="color: #81a1c1;">J2:</span> <b>2 envidatzen ditu.</b><br>
                        <span style="color: #ebcb8b;">J1:</span> Faroleatu eta <b>nahi du (Ikusi)</b>.<br>
                        <div style="margin-top: 5px; color: #a3be8c;"><b>Emaitza:</b> 2 puntu gordeta. J2k zenbaketan irabaziko ditu!</div>
                    </div>
                </div>
            `
        },
        {
            title: "2. adib.: Pareen talka",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">Errege-pare bat izatea ondo dago, baina mediak (hirukotea) hobeak dira.</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J1 (Parea)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Handitu</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J2 (Mediak)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Handitu</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #b48ead;">
                        <strong style="color: #b48ead; font-size: 1.1em;">👯 PAREAK</strong><br>
                        <span style="color: #eceff4; font-style: italic;">Biek deklaratzen dute pareak dituztela.</span><br>
                        <span style="color: #ebcb8b;">J1:</span> Erregeetan konfiantza du. <b>2 envidatzen ditu.</b><br>
                        <span style="color: #81a1c1;">J2:</span> Mediak ditu! <b>4ra igotzen du.</b><br>
                        <span style="color: #ebcb8b;">J1:</span> <b>Nahi du (Ikusi).</b><br>
                        <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                            <b>Azken zenbaketa:</b> J2k hiru 4ak erakusten ditu eta J1en Erregeak txikitzen ditu. <br>J2k <b>apustatutako 4 puntuak</b> + <b>2 pnt hobari</b> eramaten ditu mediengatik!
                        </div>
                    </div>
                </div>
            `
        },
        {
            title: "3. adib.: 31 vs 32",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">Jokoan, 31 da guztien onena. 32 da txarrena!</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J1 (32 batura)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Handitu</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J2 (31 batura)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Handitu</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                        <strong style="color: #a3be8c; font-size: 1.1em;">🎯 JOKOA</strong><br>
                        <span style="color: #eceff4; font-style: italic;">Biak iristen dira 31ra edo gehiagora.</span><br>
                        <span style="color: #ebcb8b;">J1:</span> Eskua naiz, agian 32 nahikoa da. <b>2 envidatzen ditu.</b><br>
                        <span style="color: #81a1c1;">J2:</span> 31 zehatza dut! <b>HORDAGO!</b><br>
                        <span style="color: #ebcb8b;">J1:</span> Badaki 32 negargarria dela. <b>Ez du nahi.</b><br>
                        <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                            <b>Azken zenbaketa:</b> J2k apustatutako 2 puntuak berehala eramaten ditu. Amaieran, J2k <b>+3 pnt hobari</b> ere lortzen ditu 31 izateagatik!
                        </div>
                    </div>
                </div>
            `
        },
        {
            title: "4. adib.: Puntura jokatzen",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">Inor 31ra iristen ez bada, "Puntura" jokatzen da (baturarik altuenak irabazten du).</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J1 (29 batura)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Handitu</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">J2 (28 batura)</div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                            <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Handitu</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                        <strong style="color: #a3be8c; font-size: 1.1em;">🎯 PUNTUA</strong><br>
                        <span style="color: #eceff4; font-style: italic;">"Inork ez du jokorik. Puntura jokatzen da."</span><br>
                        <span style="color: #ebcb8b;">J1:</span> 29 oso hurbil dago 30etik (puntu gorenetik). <b>2 envidatzen ditu.</b><br>
                        <span style="color: #81a1c1;">J2:</span> 28 dut, agian nahikoa izango da? <b>Nahi du (Ikusi).</b><br>
                        <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                            <b>Azken zenbaketa:</b> J1ek 29 erakusten du, J2k 28. J1ek irabazi du!<br>J1ek <b>apustatutako 2 puntuak</b> + <b>1 pnt hobari</b> eramaten ditu Puntua irabazteagatik.
                        </div>
                    </div>
                </div>
            `
        }
    ]
};

// ==========================================
// PISTA 2: EL MUS POR PAREJAS (2 contra 2)
// ==========================================
// Da por sabido el 1v1: aquí sólo está lo que CAMBIA al jugar cuatro. Las
// diapositivas 6 y 7 son ejemplos con cartas, igual que en la pista del 1v1.

const dictTut2v2 = {
    es: [
        {
            title: "La mesa: dos parejas",
            content: `
                <p class="tut-lead">En el 2 contra 2 hay cuatro jugadores y dos equipos. <b>Tu pareja se sienta enfrente</b> de ti; los rivales, a los lados.</p>

                <div class="tut-mesa">
                    <div class="tut-seat eqA s-t"><b>Tu pareja</b><small>equipo A</small></div>
                    <div class="tut-seat eqB s-l"><b>Rival</b><small>equipo B</small></div>
                    <div class="tut-mesa-centro s-c">el turno gira<br>hacia la derecha &#8635;</div>
                    <div class="tut-seat eqB s-r"><b>Rival</b><small>equipo B</small></div>
                    <div class="tut-seat eqA yo s-b"><b>Tú</b><small>equipo A</small></div>
                </div>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Los puntos son del equipo</span>
                        <p>Tu pareja y tú compartéis marcador. Gana la partida el equipo que llega a <b>40 puntos</b>, y el duelo se juega al mejor de las partidas que se elijan al crear la mesa.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">La mano rota un asiento</span>
                        <p>Cada ronda la <b>Mano</b> pasa al siguiente asiento, así que los cuatro pasan por ser mano y por ser postre. Se habla en orden de mesa empezando por la mano.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Lo que no cambia",
            content: `
                <p class="tut-lead">Las reglas de fondo son exactamente las del 1 contra 1.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Igual que en el 1v1</span>
                        <p>• La baraja de 40 cartas, con los <b>3 como reyes</b> y los <b>2 como ases</b>.<br>
                        • Los cuatro lances: <b>Grande, Chica, Pares y Juego</b> (o Punto).<br>
                        • Las mismas palabras: paso, envido, subir, quiero, no quiero y órdago.<br>
                        • Los mismos premios en el recuento, el <b>Pedrete</b> y <b>La Real</b>.</p>
                    </div>
                </div>

                <button class="tut-goto" data-tut-pista="1v1">📖 Repasar las reglas básicas (1 contra 1)</button>
                <span class="tut-nota">Lo que sigue son las cuatro diferencias del juego por parejas.</span>
            `
        },
        {
            title: "El mus se corta entre cuatro",
            content: `
                <p class="tut-lead">Se pregunta a los cuatro por orden, empezando por la mano.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Hay mus si lo quieren LOS CUATRO</span>
                        <p>Basta con que <b>uno solo diga «no hay mus»</b> para cortar: no se descarta nadie y empiezan las apuestas.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">Quien corta, abre Grande</span>
                        <p>El que ha cortado habla primero en Grande, aunque no sea la mano. En los demás lances se vuelve a empezar por la mano.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Los descartes son de cada uno</span>
                        <p>Si hay mus, cada jugador tira de 1 a 4 cartas y roba otras tantas. Después se vuelve a preguntar, y así hasta que alguien corte.</p>
                    </div>
                </div>

                <div class="tut-tip"><b>Ojo:</b> cortar el mus con una buena mano no sólo te protege a ti: también impide que <b>los dos rivales</b> mejoren.</div>
            `
        },
        {
            title: "Pares y Juego se declaran",
            content: `
                <p class="tut-lead">Antes de apostar Pares y Juego, los cuatro dicen en voz alta si tienen o no. Es información <b>pública</b>, y de las más valiosas de la mesa.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#b48ead;">
                        <span class="tt">Un equipo «tiene» si tiene cualquiera de los dos</span>
                        <p>Da igual quién de la pareja lleve los pares: el equipo entra en el lance.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Si sólo un equipo tiene</span>
                        <p>No se apuesta: el lance se lo lleva ese equipo directamente. Los <b>premios de sus manos se cuentan igual</b> en el recuento.</p>
                    </div>
                    <div class="tut-box" style="--tc:#4c566a;">
                        <span class="tt">Si no tiene nadie</span>
                        <p>Pares se salta sin más. En Juego, si nadie llega a 31 se juega al <b>Punto</b> — y ahí sí se apuesta.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Apostar es cosa de dos",
            content: `
                <p class="tut-lead">Se envida contra el equipo rival, no contra un jugador. Y la pareja responde <b>entre los dos</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">1. Alguien envida</span>
                        <p>Se habla por orden desde la mano. Quien tiene el turno puede pasar, envidar u ordagar.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">2. Responde el rival de turno</span>
                        <p>Puede <b>querer</b>, <b>subir</b> o <b>no querer</b>.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">3. …y si no quiere, aún habla su pareja</span>
                        <p>Antes de conceder la apuesta, el compañero puede <b>querer o subir por el equipo</b>. Sólo se concede si <b>los dos</b> dicen que no.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">4. Todo va al marcador del equipo</span>
                        <p>Nadie puede apostar más de lo que falta para 40 (si te pasas, se convierte en <b>órdago</b>), y un «no quiero» que le daría la partida al rival se convierte en <b>«quiero»</b> a la fuerza.</p>
                    </div>
                </div>
            `
        },
        {
            title: "El recuento por parejas",
            content: `
                <p class="tut-lead">Al enseñar las cartas, cada lance se resuelve comparando <b>la mejor mano de cada equipo</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Gana el equipo, no el jugador</span>
                        <p>De los dos de tu pareja se toma la mano que mejor va en ese lance y se enfrenta a la mejor de los rivales.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Los empates los rompe la mano</span>
                        <p>Si las dos manos son idénticas, gana la del jugador <b>más cerca de la mano</b> en el orden de la mesa.</p>
                    </div>
                    <div class="tut-box" style="--tc:#b48ead;">
                        <span class="tt">Los premios SE SUMAN</span>
                        <p>En Pares y en Juego, el equipo que gana el lance cobra el premio de <b>cada una de sus dos manos</b> que cualifique. Dos parejas con pares cobran las dos.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Ej. 1: los premios se suman",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">Lance de <b>Pares</b>. Los cuatro declaran: el equipo A tiene dos manos con pares; el B, una.</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: flex-start;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.85em;">Tú (A)<br><span style="font-weight:normal; color:#d8dee9;">pareja de reyes</span></div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_clubs_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Ampliar</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.85em;">Tu pareja (A)<br><span style="font-weight:normal; color:#d8dee9;">duples</span></div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_clubs_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Ampliar</span>
                    </div>
                </div>

                <div style="text-align: center; margin-bottom: 12px;">
                    <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.85em;">La mejor del equipo B: medias de sotas</div>
                    <div class="tut-cards-group tut-overlap" style="justify-content:center;">
                        <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_cups_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_swords_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_clubs_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                    </div>
                </div>

                <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #b48ead; text-align: left; font-size: 0.85em;">
                    <strong style="color: #b48ead; font-size: 1.1em;">👯 PARES</strong><br>
                    <span style="color: #ebcb8b;">A:</span> <b>Envida 2.</b> &nbsp;<span style="color: #81a1c1;">B:</span> <b>Quiere.</b><br>
                    <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                        <b>Recuento:</b> los duples de tu pareja ganan a las medias del rival.<br>
                        El equipo A se lleva <b>2 (lo apostado)</b> + <b>3 (duples)</b> + <b>1 (tu pareja de reyes)</b> = <b>6 puntos</b>.
                    </div>
                </div>
            `
        },
        {
            title: "Ej. 2: responde la pareja",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 12px;">Lance de <b>Grande</b>. El rival de tu derecha envida y a ti no te da la mano… pero la decisión no acaba en ti.</p>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.88em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #81a1c1;">
                        <span style="color: #81a1c1; font-weight: bold;">Rival (B):</span> <b>Envida 2.</b>
                    </div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #ebcb8b;">
                        <span style="color: #ebcb8b; font-weight: bold;">Tú (A):</span> llevas 7-6-5-4. <b>No quiero.</b>
                    </div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                        <span style="color: #a3be8c; font-weight: bold;">Tu pareja (A):</span> antes de conceder nada, le toca hablar a ella: lleva <b>tres reyes</b> y <b>sube a 4</b>.
                    </div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #bf616a;">
                        <span style="color: #bf616a; font-weight: bold;">Equipo B:</span> se lo piensa y <b>no quiere</b>.
                    </div>
                    <div style="padding: 10px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                        <b>Resultado:</b> el equipo A gana los <b>2 puntos</b> del envite que el rival no ha querido. Tu «no quiero» no cerró el lance: sólo se concede cuando <b>los dos</b> de la pareja rechazan.
                    </div>
                </div>

                <div class="tut-tip">Por eso conviene mirar lo que declara tu pareja: cuando ella tiene algo, tú puedes pasar tranquilo.</div>
            `
        },
        {
            title: "Y luego están las señas",
            content: `
                <p class="tut-lead">Tu pareja y tú nunca veis vuestras cartas… pero en el mus de siempre <b>os avisáis con la cara</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Son una opción de la mesa</span>
                        <p>Al crear una partida de 2 contra 2 puedes activar <b>«Con señas»</b>. Con ellas la mesa cambia: tus cartas están boca abajo y sólo ves la cara de quien estés mirando.</p>
                    </div>
                </div>

                <button class="tut-goto" data-tut-pista="senas" style="background:#ebcb8b; color:#2e3440;">☞ Aprender las señas</button>
            `
        }
    ],

    en: [
        {
            title: "The table: two pairs",
            content: `
                <p class="tut-lead">In 2 vs 2 there are four players and two teams. <b>Your partner sits across</b> from you; the opponents, on either side.</p>

                <div class="tut-mesa">
                    <div class="tut-seat eqA s-t"><b>Your partner</b><small>team A</small></div>
                    <div class="tut-seat eqB s-l"><b>Opponent</b><small>team B</small></div>
                    <div class="tut-mesa-centro s-c">the turn goes<br>to the right &#8635;</div>
                    <div class="tut-seat eqB s-r"><b>Opponent</b><small>team B</small></div>
                    <div class="tut-seat eqA yo s-b"><b>You</b><small>team A</small></div>
                </div>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Points belong to the team</span>
                        <p>You and your partner share one score. A game is won by the team that reaches <b>40 points</b>, and the match is best of however many games you pick when creating the table.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Mano moves one seat</span>
                        <p>Every round the <b>Mano</b> passes to the next seat, so all four take turns being first and last. Play always goes around the table starting at the Mano.</p>
                    </div>
                </div>
            `
        },
        {
            title: "What doesn't change",
            content: `
                <p class="tut-lead">The underlying rules are exactly the ones from 1 vs 1.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Same as in 1v1</span>
                        <p>• The 40-card deck, with <b>3s as Kings</b> and <b>2s as Aces</b>.<br>
                        • The four phases: <b>Grande, Chica, Pares and Juego</b> (or Punto).<br>
                        • The same words: pass, bid, raise, call, fold and órdago.<br>
                        • The same showdown bonuses, the <b>Pedrete</b> and <b>La Real</b>.</p>
                    </div>
                </div>

                <button class="tut-goto" data-tut-pista="1v1">📖 Review the basic rules (1 vs 1)</button>
                <span class="tut-nota">What follows are the four differences of the partner game.</span>
            `
        },
        {
            title: "Cutting the Mus with four",
            content: `
                <p class="tut-lead">All four are asked in turn, starting with the Mano.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">There is Mus only if ALL FOUR want it</span>
                        <p>A <b>single "no mus"</b> is enough to cut: nobody discards and betting starts.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">Whoever cuts, opens Grande</span>
                        <p>The player who cut speaks first in Grande, even if they are not the Mano. Every other phase starts at the Mano again.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Discards are personal</span>
                        <p>If there is Mus, each player throws 1 to 4 cards and draws that many. Then everyone is asked again, until someone cuts.</p>
                    </div>
                </div>

                <div class="tut-tip"><b>Note:</b> cutting the Mus with a good hand doesn't only protect you: it also stops <b>both opponents</b> from improving.</div>
            `
        },
        {
            title: "Pares and Juego are declared",
            content: `
                <p class="tut-lead">Before betting Pares and Juego, all four say out loud whether they have it. It is <b>public</b> information, and some of the most valuable at the table.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#b48ead;">
                        <span class="tt">A team "has it" if either partner does</span>
                        <p>It doesn't matter which of the two holds the pairs: the team is in the phase.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">If only one team has it</span>
                        <p>There is no betting: that team simply takes the phase. The <b>bonuses of its hands still count</b> at the showdown.</p>
                    </div>
                    <div class="tut-box" style="--tc:#4c566a;">
                        <span class="tt">If nobody has it</span>
                        <p>Pares is skipped altogether. In Juego, if nobody reaches 31 the phase becomes <b>Punto</b> — and that one is still bet.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Betting takes two",
            content: `
                <p class="tut-lead">You bid against the rival team, not against a player. And the pair answers <b>between the two of them</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">1. Someone bids</span>
                        <p>Players speak in order from the Mano. Whoever is on turn may pass, bid or go all-in.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">2. The opponent on turn answers</span>
                        <p>They may <b>call</b>, <b>raise</b> or <b>fold</b>.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">3. …and if they fold, their partner still speaks</span>
                        <p>Before the bet is conceded, the partner may still <b>call or raise for the team</b>. It is only conceded when <b>both</b> say no.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">4. Everything goes to the team score</span>
                        <p>Nobody can bet more than what is left to reach 40 (any excess becomes an <b>órdago</b>), and a fold that would hand the opponents the game is turned into a forced <b>call</b>.</p>
                    </div>
                </div>
            `
        },
        {
            title: "The showdown, by pairs",
            content: `
                <p class="tut-lead">When the cards come up, each phase is resolved by comparing <b>the best hand of each team</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">The team wins, not the player</span>
                        <p>From your pair, the hand that does best in that phase is taken and faced against the opponents' best.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Ties are broken by the Mano</span>
                        <p>If the two hands are identical, the one belonging to the player <b>closest to the Mano</b> in table order wins.</p>
                    </div>
                    <div class="tut-box" style="--tc:#b48ead;">
                        <span class="tt">Bonuses ADD UP</span>
                        <p>In Pares and Juego, the team that wins the phase collects the bonus of <b>each of its two hands</b> that qualifies. Two hands with pairs, two bonuses.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Ex 1: bonuses add up",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;"><b>Pares</b> phase. All four declare: team A has two hands with pairs; team B, one.</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: flex-start;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.85em;">You (A)<br><span style="font-weight:normal; color:#d8dee9;">pair of Kings</span></div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_clubs_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Zoom</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.85em;">Your partner (A)<br><span style="font-weight:normal; color:#d8dee9;">two pairs</span></div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_clubs_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Zoom</span>
                    </div>
                </div>

                <div style="text-align: center; margin-bottom: 12px;">
                    <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.85em;">Team B's best: three Jacks</div>
                    <div class="tut-cards-group tut-overlap" style="justify-content:center;">
                        <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_cups_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_swords_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_clubs_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                    </div>
                </div>

                <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #b48ead; text-align: left; font-size: 0.85em;">
                    <strong style="color: #b48ead; font-size: 1.1em;">👯 PARES</strong><br>
                    <span style="color: #ebcb8b;">A:</span> <b>Bids 2.</b> &nbsp;<span style="color: #81a1c1;">B:</span> <b>Calls.</b><br>
                    <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                        <b>Showdown:</b> your partner's two pairs beat the opponents' three of a kind.<br>
                        Team A takes <b>2 (the bet)</b> + <b>3 (two pairs)</b> + <b>1 (your pair of Kings)</b> = <b>6 points</b>.
                    </div>
                </div>
            `
        },
        {
            title: "Ex 2: your partner answers",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 12px;"><b>Grande</b> phase. The opponent on your right bids and your hand is useless… but the decision doesn't stop with you.</p>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.88em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #81a1c1;">
                        <span style="color: #81a1c1; font-weight: bold;">Opponent (B):</span> <b>Bids 2.</b>
                    </div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #ebcb8b;">
                        <span style="color: #ebcb8b; font-weight: bold;">You (A):</span> you hold 7-6-5-4. <b>Fold.</b>
                    </div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                        <span style="color: #a3be8c; font-weight: bold;">Your partner (A):</span> before anything is conceded it is their turn to speak: they hold <b>three Kings</b> and <b>raise to 4</b>.
                    </div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #bf616a;">
                        <span style="color: #bf616a; font-weight: bold;">Team B:</span> thinks about it and <b>folds</b>.
                    </div>
                    <div style="padding: 10px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                        <b>Result:</b> team A wins the <b>2 points</b> of the bid the opponents didn't take. Your fold didn't close the phase: it is only conceded when <b>both</b> partners refuse.
                    </div>
                </div>

                <div class="tut-tip">That is why it pays to listen to what your partner declares: when they have something, you can pass in peace.</div>
            `
        },
        {
            title: "And then there are signs",
            content: `
                <p class="tut-lead">You and your partner never see each other's cards… but in traditional Mus <b>you warn each other with your face</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">They are a table option</span>
                        <p>When creating a 2 vs 2 game you can switch on <b>"With signs"</b>. With them the table changes: your cards lie face down and you only see the face of whoever you are looking at.</p>
                    </div>
                </div>

                <button class="tut-goto" data-tut-pista="senas" style="background:#ebcb8b; color:#2e3440;">☞ Learn the signs</button>
            `
        }
    ],

    eu: [
        {
            title: "Mahaia: bi bikote",
            content: `
                <p class="tut-lead">2 aurka 2 jokoan lau jokalari eta bi talde daude. <b>Zure bikotekidea zure parean</b> esertzen da; aurkariak, alboetan.</p>

                <div class="tut-mesa">
                    <div class="tut-seat eqA s-t"><b>Zure bikotekidea</b><small>A taldea</small></div>
                    <div class="tut-seat eqB s-l"><b>Aurkaria</b><small>B taldea</small></div>
                    <div class="tut-mesa-centro s-c">txanda eskuinerantz<br>biratzen da &#8635;</div>
                    <div class="tut-seat eqB s-r"><b>Aurkaria</b><small>B taldea</small></div>
                    <div class="tut-seat eqA yo s-b"><b>Zu</b><small>A taldea</small></div>
                </div>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Puntuak taldearenak dira</span>
                        <p>Zure bikotekideak eta zuk markagailua partekatzen duzue. <b>40 puntura</b> iristen den taldeak irabazten du partida, eta norgehiagoka mahaia sortzean aukeratzen diren partidetatik onenera jokatzen da.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Eskua eserleku bat biratzen da</span>
                        <p>Esku bakoitzean <b>Eskua</b> hurrengo eserlekura pasatzen da, beraz laurak izaten dira esku eta postre. Mahaiaren ordenan hitz egiten da, eskutik hasita.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Aldatzen ez dena",
            content: `
                <p class="tut-lead">Funtsezko arauak 1 aurka 1ekoak berberak dira.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">1v1ean bezala</span>
                        <p>• 40 kartako karta-sorta, <b>3ak errege</b> eta <b>2ak as</b> direla.<br>
                        • Lau lanceak: <b>Handia, Txikia, Pareak eta Jokoa</b> (edo Puntua).<br>
                        • Hitz berberak: paso, envido, igo, nahi dut, ez dut nahi eta hordago.<br>
                        • Zenbaketan sari berberak, <b>Pedretea</b> eta <b>Erreala</b>.</p>
                    </div>
                </div>

                <button class="tut-goto" data-tut-pista="1v1">📖 Oinarrizko arauak errepasatu (1 aurka 1)</button>
                <span class="tut-nota">Ondoren datozenak bikoteka jokatzearen lau desberdintasunak dira.</span>
            `
        },
        {
            title: "Musa lauren artean mozten da",
            content: `
                <p class="tut-lead">Laurei galdetzen zaie hurrenez hurren, eskutik hasita.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Musa dago LAUREK nahi badute</span>
                        <p><b>Batek bakarrik «musik ez» esatea</b> nahikoa da mozteko: inork ez du deskartatzen eta apustuak hasten dira.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">Mozten duenak zabaltzen du Handia</span>
                        <p>Moztu duenak hitz egiten du lehenengo Handian, eskua ez izan arren. Gainerako lanceetan eskutik hasten da berriro.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Deskarteak norberarenak dira</span>
                        <p>Musa badago, jokalari bakoitzak 1etik 4ra karta botatzen ditu eta beste horrenbeste hartzen. Gero berriro galdetzen da, eta horrela norbaitek moztu arte.</p>
                    </div>
                </div>

                <div class="tut-tip"><b>Kontuz:</b> esku on batekin musa mozteak ez zaitu zu bakarrik babesten: <b>bi aurkariek</b> hobetzea ere eragozten du.</div>
            `
        },
        {
            title: "Pareak eta Jokoa deklaratu egiten dira",
            content: `
                <p class="tut-lead">Pareak eta Jokoa apustatu aurretik, laurek ozen esaten dute badituzten ala ez. Informazio <b>publikoa</b> da, eta mahaiko baliotsuenetakoa.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#b48ead;">
                        <span class="tt">Talde batek «badu» bietako batek badu</span>
                        <p>Berdin dio bikoteko zeinek dituen pareak: taldea lancean sartzen da.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Talde bakar batek badu</span>
                        <p>Ez da apustatzen: lancea talde horrek eramaten du zuzenean. Bere esken <b>sariak berdin zenbatzen dira</b> zenbaketan.</p>
                    </div>
                    <div class="tut-box" style="--tc:#4c566a;">
                        <span class="tt">Inork ez badu</span>
                        <p>Pareak besterik gabe saltatzen da. Jokoan, inor 31ra iristen ez bada, <b>Puntura</b> jokatzen da — eta hor bai egiten da apustu.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Apustatzea biren kontua da",
            content: `
                <p class="tut-lead">Aurkako taldearen aurka envidatzen da, ez jokalari baten aurka. Eta bikoteak <b>bien artean</b> erantzuten du.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">1. Norbaitek envidatzen du</span>
                        <p>Eskutik hasita hitz egiten da hurrenez hurren. Txanda duenak pasatu, envidatu edo hordagoa bota dezake.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">2. Txandako aurkariak erantzuten du</span>
                        <p><b>Nahi izan</b>, <b>igo</b> edo <b>ez nahi izan</b> dezake.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">3. …eta nahi ez badu, bere bikotekideak hitz egiten du oraindik</span>
                        <p>Apustua eman aurretik, kideak <b>taldearen alde nahi izan edo igo</b> dezake. <b>Biek</b> ezetz esaten badute bakarrik ematen da.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">4. Dena taldearen markagailura doa</span>
                        <p>Inork ezin du 40ra iristeko falta dena baino gehiago apustatu (pasatuz gero, <b>hordago</b> bihurtzen da), eta aurkariari partida emango liokeen «ez dut nahi» bat nahitaez <b>«nahi dut»</b> bihurtzen da.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Bikoteka zenbatzea",
            content: `
                <p class="tut-lead">Kartak erakustean, lance bakoitza <b>talde bakoitzaren eskurik onena</b> alderatuz ebazten da.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Taldeak irabazten du, ez jokalariak</span>
                        <p>Zure bikoteko bien artean lance horretan hoberen doan eskua hartzen da eta aurkarien onenaren aurka jartzen da.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Berdinketak eskuak hausten ditu</span>
                        <p>Bi eskuak berdin-berdinak badira, mahaiaren ordenan <b>eskutik hurbilen</b> dagoen jokalariarenak irabazten du.</p>
                    </div>
                    <div class="tut-box" style="--tc:#b48ead;">
                        <span class="tt">Sariak BATU egiten dira</span>
                        <p>Paretan eta Jokoan, lancea irabazten duen taldeak kualifikatzen duen <b>bere bi eskuetako bakoitzaren</b> saria kobratzen du. Pareak dituzten bi eskuk biek kobratzen dute.</p>
                    </div>
                </div>
            `
        },
        {
            title: "1. adib.: sariak batu egiten dira",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;"><b>Pareen</b> lancea. Laurek deklaratzen dute: A taldeak pareak dituzten bi esku ditu; B taldeak, bat.</p>

                <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: flex-start;">
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.85em;">Zu (A)<br><span style="font-weight:normal; color:#d8dee9;">errege-parea</span></div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_clubs_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Handitu</span>
                    </div>
                    <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.85em;">Zure bikotekidea (A)<br><span style="font-weight:normal; color:#d8dee9;">duplak</span></div>
                        <div class="tut-cards-group tut-overlap">
                            <img src="/static/img/card_coins_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_cups_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                            <img src="/static/img/card_clubs_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        </div>
                        <span class="tut-zoom-hint">🔍 Handitu</span>
                    </div>
                </div>

                <div style="text-align: center; margin-bottom: 12px;">
                    <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.85em;">B taldearen onena: txanka-mediak</div>
                    <div class="tut-cards-group tut-overlap" style="justify-content:center;">
                        <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_cups_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_swords_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_clubs_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                    </div>
                </div>

                <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #b48ead; text-align: left; font-size: 0.85em;">
                    <strong style="color: #b48ead; font-size: 1.1em;">👯 PAREAK</strong><br>
                    <span style="color: #ebcb8b;">A:</span> <b>2 envidatzen ditu.</b> &nbsp;<span style="color: #81a1c1;">B:</span> <b>Nahi du.</b><br>
                    <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                        <b>Zenbaketa:</b> zure bikotekidearen duplek aurkariaren mediei irabazten diete.<br>
                        A taldeak <b>2 (apustatutakoa)</b> + <b>3 (duplak)</b> + <b>1 (zure errege-parea)</b> = <b>6 puntu</b> eramaten ditu.
                    </div>
                </div>
            `
        },
        {
            title: "2. adib.: bikotekideak erantzuten du",
            content: `
                <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 12px;"><b>Handiaren</b> lancea. Zure eskuineko aurkariak envidatu du eta zuk ez duzu eskurik… baina erabakia ez da zurekin amaitzen.</p>

                <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.88em;">
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #81a1c1;">
                        <span style="color: #81a1c1; font-weight: bold;">Aurkaria (B):</span> <b>2 envidatzen ditu.</b>
                    </div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #ebcb8b;">
                        <span style="color: #ebcb8b; font-weight: bold;">Zu (A):</span> 7-6-5-4 duzu. <b>Ez dut nahi.</b>
                    </div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                        <span style="color: #a3be8c; font-weight: bold;">Zure bikotekidea (A):</span> ezer eman aurretik, berari dagokio hitz egitea: <b>hiru errege</b> ditu eta <b>4ra igotzen du</b>.
                    </div>
                    <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #bf616a;">
                        <span style="color: #bf616a; font-weight: bold;">B taldea:</span> pentsatu eta <b>ez du nahi</b>.
                    </div>
                    <div style="padding: 10px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                        <b>Emaitza:</b> A taldeak aurkariak nahi izan ez duen envitearen <b>2 puntuak</b> irabazten ditu. Zure «ez dut nahi»-ak ez zuen lancea itxi: bikoteko <b>biek</b> baztertzen dutenean bakarrik ematen da.
                    </div>
                </div>

                <div class="tut-tip">Horregatik komeni da zure bikotekideak deklaratzen duena begiratzea: berak zerbait duenean, zu lasai pasa zaitezke.</div>
            `
        },
        {
            title: "Eta gero keinuak daude",
            content: `
                <p class="tut-lead">Zure bikotekideak eta zuk ez duzue inoiz elkarren kartarik ikusten… baina betiko musean <b>aurpegiarekin abisatzen diozue elkarri</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Mahaiaren aukera bat dira</span>
                        <p>2 aurka 2 partida bat sortzean <b>«Keinuekin»</b> aktiba dezakezu. Haiekin mahaia aldatu egiten da: zure kartak ahoz behera daude eta begiratzen ari zarenaren aurpegia baino ez duzu ikusten.</p>
                    </div>
                </div>

                <button class="tut-goto" data-tut-pista="senas" style="background:#ebcb8b; color:#2e3440;">☞ Keinuak ikasi</button>
            `
        }
    ]
};

// ==========================================
// PISTA 3: LAS SEÑAS
// ==========================================
// Las diapositivas de los diez gestos se generan al pintar (`content` función),
// porque la cara SVG vive en senas4.js, que se carga después que este archivo.

/** La cara de senas4.js haciendo una seña en bucle. Si por lo que sea todavía no
 *  está cargado, deja una mano señalando en su sitio: se entiende igual. */
function tutCaraSena(sena) {
    const svg = (window.Senas4 && typeof window.Senas4.svgCara === 'function')
        ? window.Senas4.svgCara() : null;
    if (!svg) return `<span class="tut-sena-cara sena-muestra" style="font-size:1.6em;">☞</span>`;
    // Las clases son las mismas que usa la chuleta de la ventana de denuncia.
    return `<span class="tut-sena-cara sena-muestra">${
        svg.replace('class="cara"', `class="cara en-bucle sena-${sena}"`)
    }</span>`;
}

/** Una ficha de la lista de señas. */
function tutFilaSena(sena, nombre, mano, gesto) {
    return `
        <div class="tut-sena">
            ${tutCaraSena(sena)}
            <span class="tut-sena-txt">
                <span class="tut-sena-nom">${nombre}</span>
                <span class="tut-sena-mano">${mano}</span>
                <span class="tut-sena-gesto">${gesto}</span>
            </span>
        </div>`;
}

function tutListaSenas(filas) {
    return `<div class="tut-senas">${filas.map(f => tutFilaSena(...f)).join('')}</div>`;
}

const dictTutSenas = {
    es: [
        {
            title: "Qué son las señas",
            content: `
                <p class="tut-lead">Las señas son los gestos con los que avisas a tu pareja de lo que llevas — y con los que los rivales intentan pillarte.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Sólo en el 2 contra 2</span>
                        <p>Se activan al crear la partida, con el interruptor <b>«Con señas»</b>. Sin él, la mesa es la de siempre.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">La mesa se mira de una en una</span>
                        <p>Con señas <b>no ves la mesa entera</b>: giras la cabeza y sólo ves la cara —y por tanto la seña— de quien estés mirando. Tus cartas están boca abajo salvo mientras las miras.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">Y por eso hay riesgo</span>
                        <p>Para que tu pareja vea tu seña tiene que estar mirándote <b>justo cuando la haces</b>. Y si te está mirando un rival, te ha pillado.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Mirar es medio juego",
            content: `
                <p class="tut-lead">Hay cuatro sitios a los que puedes mirar. Con las <b>flechas</b>, con <b>WASD</b> o <b>deslizando el dedo</b>.</p>

                <div class="tut-mesa">
                    <div class="tut-seat eqA s-t"><b>Tu pareja</b><small><span class="tut-key">↑</span> <span class="tut-key">W</span></small></div>
                    <div class="tut-seat eqB s-l"><b>Rival</b><small><span class="tut-key">←</span> <span class="tut-key">A</span></small></div>
                    <div class="tut-mesa-centro s-c">sólo ves<br>a uno a la vez</div>
                    <div class="tut-seat eqB s-r"><b>Rival</b><small><span class="tut-key">→</span> <span class="tut-key">D</span></small></div>
                    <div class="tut-seat yo s-b"><b>Tus cartas</b><small><span class="tut-key">↓</span> <span class="tut-key">S</span></small></div>
                </div>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Se lee a quién mira cada uno</span>
                        <p>En la cara que ves, las <b>pupilas</b> se desplazan y la cabeza se inclina hacia su objetivo. Si te está mirando a ti, <b>la cara se enciende en oro</b>.</p>
                    </div>
                    <div class="tut-box" style="--tc:#4c566a;">
                        <span class="tt">La vista vagabundea sola</span>
                        <p>Si no tocas nada, tu mirada se pasea sola entre el frente y los dos lados — nunca hacia tus cartas: mirarlas es siempre decisión tuya.</p>
                    </div>
                </div>

                <span class="tut-nota">Hay un botón <b>?</b> junto a «Con señas», al crear la partida, que repasa estos mandos.</span>
            `
        },
        {
            title: "La regla de oro: la más alta",
            content: `
                <p class="tut-lead">El botón de <b>Seña</b> no te deja elegir: sale <b>la seña más alta que permita tu mano</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Una seña nunca miente</span>
                        <p>Con tres reyes no puedes señalar «dos reyes» para disimular: saldrá <b>tres reyes</b>. Lo que decides es <b>cuándo</b> señalar y <b>si</b> te arriesgas, no qué dices.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">El orden de prioridad</span>
                        <p>solomillo · duples · 31 · tres reyes · tres ases · medias · dos reyes · dos ases · 30 · ciego</p>
                        <p>Manda la primera de la lista que cumpla tu mano. Con tres reyes y un as sale <b>solomillo</b>, que es la mejor noticia que puedes dar.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Una cada 3 segundos</span>
                        <p>El botón se recarga: no se puede repetir la seña sin parar hasta que alguien mire.</p>
                    </div>
                </div>

                <div class="tut-tip">Recuerda que los <b>3 valen como reyes</b> y los <b>2 como ases</b>: la mano <b>Rey · 3 · 7 · 6</b> lleva dos reyes.</div>
            `
        },
        {
            title: "Las señas fuertes",
            content: () => `
                <p class="tut-lead">Las cinco que cuentan las mejores manos. Las caras hacen el gesto en bucle.</p>
                ${tutListaSenas([
                    ['solomillo',  'Solomillo',  'Tres reyes y un as',            'un beso'],
                    ['duples',     'Duples',     'Dos parejas (o cuatro iguales)', 'levantar las cejas'],
                    ['31',         '31',         'Juego de 31 justo',             'un guiño'],
                    ['tres_reyes', 'Tres reyes', 'Tres reyes (los 3 cuentan)',    'morderse un lado del labio'],
                    ['tres_ases',  'Tres ases',  'Tres ases (los 2 cuentan)',     'sacar la lengua de lado'],
                ])}
            `
        },
        {
            title: "Las demás señas",
            content: () => `
                <p class="tut-lead">Y las cinco que quedan, hasta el <b>ciego</b> — que también es información.</p>
                ${tutListaSenas([
                    ['medias',    'Medias',    'Trío de cualquier otra cosa',  'torcer la boca'],
                    ['dos_reyes', 'Dos reyes', 'Dos reyes (los 3 cuentan)',   'morderse el centro del labio'],
                    ['dos_ases',  'Dos ases',  'Dos ases (los 2 cuentan)',    'sacar la lengua'],
                    ['30',        '30',        'Suma de 30, sin llegar a 31', 'encoger los hombros'],
                    ['ciego',     'Ciego',     'Nada de lo anterior',         'cerrar los ojos'],
                ])}
                <span class="tut-nota">Los gestos son los tradicionales, salvo el solomillo, que es de la casa.</span>
            `
        },
        {
            title: "Cuándo se puede señalar",
            content: `
                <p class="tut-lead">El botón de <b>Seña</b> no está siempre vivo.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Sí: en el mus y en las apuestas</span>
                        <p>Que son los momentos en los que tu pareja puede hacer algo con lo que le cuentes.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">No: durante el descarte</span>
                        <p>Mientras se descarta, <b>tu foco se clava en tus cartas</b> y no se puede mover: hay que verlas para elegir, y así nadie señala mientras los demás están a otra cosa.</p>
                    </div>
                    <div class="tut-box" style="--tc:#4c566a;">
                        <span class="tt">No: en el recuento</span>
                        <p>Con las cuatro manos sobre la mesa el juego de mirar <b>se apaga entero</b>: no hay caras, no se puede denunciar y <b>tus cartas se destapan</b> como las demás. Ya no hay nada que esconder.</p>
                    </div>
                </div>
            `
        },
        {
            title: "«¡Te he visto!»",
            content: `
                <p class="tut-lead">Si pillas a un rival haciendo una seña, puedes <b>denunciarla</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Cómo se hace</span>
                        <p>Toca al rival en la mesa y elige de la lista qué seña le has visto. Sólo se puede denunciar a un <b>rival</b>: a tu pareja no, claro.</p>
                    </div>
                    <div class="tut-box" style="--tc:#b48ead;">
                        <span class="tt">Esa lista es la chuleta</span>
                        <p>Cada opción enseña su gesto animándose en bucle. Si dudas de cuál era, ábrela y compara.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">No da ni quita puntos</span>
                        <p>Es puro tanteo social: sale un aviso en la mesa que nombra al acusado («¡Le he visto DOS REYES a Marta!») y poco más. Pero a partir de ahí ya sabes que te miran… y ellos, que les miras.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Cuatro trucos",
            content: `
                <p class="tut-lead">Lo que separa a una pareja que se entiende de otra que sólo hace muecas.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Señala cuando la cara esté en oro</span>
                        <p>Es la única señal de que tu pareja te está mirando de verdad. Señalar al aire no cuenta.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">Apartar la vista no te salva del todo</span>
                        <p>Durante <b>un segundo</b> después de dejar de mirar a alguien, sigues viéndole. Los rivales también: señalar justo cuando apartan la mirada no es tan seguro como parece.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">El ciego también dice algo</span>
                        <p>Avisar de que no llevas nada le ahorra a tu pareja envidar por los dos.</p>
                    </div>
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Los bots también señalan</span>
                        <p>Mueven los ojos y hacen su seña una vez por mano. Si les miras a tiempo, se les pilla igual que a cualquiera.</p>
                    </div>
                </div>
            `
        }
    ],

    en: [
        {
            title: "What signs are",
            content: `
                <p class="tut-lead">Signs are the gestures you use to tell your partner what you are holding — and the ones your opponents try to catch.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">2 vs 2 only</span>
                        <p>They are switched on when creating the game, with the <b>"With signs"</b> toggle. Without it, the table is the usual one.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">You look at one player at a time</span>
                        <p>With signs you <b>don't see the whole table</b>: you turn your head and only see the face — and therefore the sign — of whoever you are looking at. Your cards lie face down except while you look at them.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">And that is the risk</span>
                        <p>For your partner to see your sign they must be looking at you <b>exactly when you make it</b>. And if an opponent is watching you, you are caught.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Looking is half the game",
            content: `
                <p class="tut-lead">There are four places you can look at. With the <b>arrows</b>, with <b>WASD</b> or by <b>swiping</b>.</p>

                <div class="tut-mesa">
                    <div class="tut-seat eqA s-t"><b>Your partner</b><small><span class="tut-key">↑</span> <span class="tut-key">W</span></small></div>
                    <div class="tut-seat eqB s-l"><b>Opponent</b><small><span class="tut-key">←</span> <span class="tut-key">A</span></small></div>
                    <div class="tut-mesa-centro s-c">one face<br>at a time</div>
                    <div class="tut-seat eqB s-r"><b>Opponent</b><small><span class="tut-key">→</span> <span class="tut-key">D</span></small></div>
                    <div class="tut-seat yo s-b"><b>Your cards</b><small><span class="tut-key">↓</span> <span class="tut-key">S</span></small></div>
                </div>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">You can read where they look</span>
                        <p>On the face you see, the <b>pupils</b> shift and the head tilts towards their target. If they are looking at you, <b>the face lights up gold</b>.</p>
                    </div>
                    <div class="tut-box" style="--tc:#4c566a;">
                        <span class="tt">Your gaze wanders on its own</span>
                        <p>If you don't touch anything, your view drifts between the front and the two sides — never towards your cards: looking at them is always your decision.</p>
                    </div>
                </div>

                <span class="tut-nota">There is a <b>?</b> button next to "With signs", when creating the game, that goes over these controls.</span>
            `
        },
        {
            title: "The golden rule: the highest one",
            content: `
                <p class="tut-lead">The <b>Sign</b> button doesn't let you choose: out comes <b>the highest sign your hand allows</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">A sign never lies</span>
                        <p>With three Kings you cannot sign "two Kings" to hide it: <b>three Kings</b> will come out. What you decide is <b>when</b> to sign and <b>whether</b> to risk it, not what you say.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">The priority order</span>
                        <p>solomillo · two pairs · 31 · three kings · three aces · three of a kind · two kings · two aces · 30 · blind</p>
                        <p>The first one on the list your hand matches is the one that comes out. With three Kings and an Ace you get <b>solomillo</b>, the best news you can give.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">One every 3 seconds</span>
                        <p>The button reloads: you can't spam the same sign until somebody happens to look.</p>
                    </div>
                </div>

                <div class="tut-tip">Remember that <b>3s count as Kings</b> and <b>2s as Aces</b>: the hand <b>King · 3 · 7 · 6</b> holds two Kings.</div>
            `
        },
        {
            title: "The strong signs",
            content: () => `
                <p class="tut-lead">The five that announce the best hands. The faces play each gesture on a loop.</p>
                ${tutListaSenas([
                    ['solomillo',  'Solomillo',      'Three Kings and an Ace',       'a kiss'],
                    ['duples',     'Two pairs',      'Two pairs (or four alike)',    'raise both eyebrows'],
                    ['31',         '31',             'A game of exactly 31',         'a wink'],
                    ['tres_reyes', 'Three kings',    'Three Kings (3s count too)',   'bite one side of your lip'],
                    ['tres_ases',  'Three aces',     'Three Aces (2s count too)',    'stick your tongue out sideways'],
                ])}
            `
        },
        {
            title: "The rest of the signs",
            content: () => `
                <p class="tut-lead">And the remaining five, down to <b>blind</b> — which is information too.</p>
                ${tutListaSenas([
                    ['medias',    'Three of a kind', 'Three of anything else',    'twist your mouth'],
                    ['dos_reyes', 'Two kings',       'Two Kings (3s count too)',  'bite the middle of your lip'],
                    ['dos_ases',  'Two aces',        'Two Aces (2s count too)',   'stick your tongue out'],
                    ['30',        '30',              'A sum of 30, short of 31',  'shrug your shoulders'],
                    ['ciego',     'Blind',           'None of the above',      'close your eyes'],
                ])}
                <span class="tut-nota">The gestures are the traditional ones, except the solomillo, which is ours.</span>
            `
        },
        {
            title: "When you may sign",
            content: `
                <p class="tut-lead">The <b>Sign</b> button is not always live.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Yes: during Mus and betting</span>
                        <p>Which are the moments when your partner can actually do something with what you tell them.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">No: while discarding</span>
                        <p>During the discard <b>your focus is locked on your own cards</b> and cannot move: you need to see them to choose, and this way nobody signs while the others are busy.</p>
                    </div>
                    <div class="tut-box" style="--tc:#4c566a;">
                        <span class="tt">No: at the showdown</span>
                        <p>With all four hands on the table the looking game <b>shuts down entirely</b>: no faces, no accusations, and <b>your cards are revealed</b> like everyone else's. There is nothing left to hide.</p>
                    </div>
                </div>
            `
        },
        {
            title: "\"I saw that!\"",
            content: `
                <p class="tut-lead">If you catch an opponent signing, you can <b>call them out</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">How it works</span>
                        <p>Tap the opponent at the table and pick from the list which sign you saw. You can only accuse an <b>opponent</b>: not your partner, obviously.</p>
                    </div>
                    <div class="tut-box" style="--tc:#b48ead;">
                        <span class="tt">That list is the cheat sheet</span>
                        <p>Every option plays its gesture on a loop. If you are not sure which one it was, open it and compare.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">It scores nothing either way</span>
                        <p>It is pure table talk: a notice pops up naming the accused ("I caught Marta signing TWO KINGS!") and little else. But from then on you know they are watching you… and they know you are watching them.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Four tips",
            content: `
                <p class="tut-lead">What separates a pair that understands each other from one that just pulls faces.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Sign when the face turns gold</span>
                        <p>It is the only proof that your partner is really looking at you. Signing into thin air counts for nothing.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">Looking away doesn't fully save you</span>
                        <p>For <b>one second</b> after you stop looking at somebody, you still see them. So do your opponents: signing right as they turn away is not as safe as it looks.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Blind says something too</span>
                        <p>Telling your partner you have nothing saves them from bidding for the two of you.</p>
                    </div>
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Bots sign as well</span>
                        <p>They move their eyes and make their sign once per hand. Look at them in time and they get caught like anyone else.</p>
                    </div>
                </div>
            `
        }
    ],

    eu: [
        {
            title: "Zer diren keinuak",
            content: `
                <p class="tut-lead">Keinuak zure bikotekideari zer daukazun adierazteko egiten dituzun imintzioak dira — eta aurkariek harrapatzen saiatzen direnak.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">2 aurka 2 jokoan bakarrik</span>
                        <p>Partida sortzean aktibatzen dira, <b>«Keinuekin»</b> etengailuarekin. Hori gabe, mahaia betikoa da.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Mahaia banan-banan begiratzen da</span>
                        <p>Keinuekin <b>ez duzu mahai osoa ikusten</b>: burua biratzen duzu eta begiratzen ari zarenaren aurpegia —eta beraz keinua— baino ez duzu ikusten. Zure kartak ahoz behera daude, begiratzen dituzun bitartean izan ezik.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">Eta horregatik dago arriskua</span>
                        <p>Zure bikotekideak zure keinua ikusteko, <b>egiten duzun une berean</b> egon behar du zuri begira. Eta aurkari bat begira badago, harrapatu zaitu.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Begiratzea joko erdia da",
            content: `
                <p class="tut-lead">Lau toki daude begiratzeko. <b>Gezien</b> bidez, <b>WASD</b> bidez edo <b>hatza irristatuz</b>.</p>

                <div class="tut-mesa">
                    <div class="tut-seat eqA s-t"><b>Zure bikotekidea</b><small><span class="tut-key">↑</span> <span class="tut-key">W</span></small></div>
                    <div class="tut-seat eqB s-l"><b>Aurkaria</b><small><span class="tut-key">←</span> <span class="tut-key">A</span></small></div>
                    <div class="tut-mesa-centro s-c">bat bakarrik ikusten<br>duzu aldiko</div>
                    <div class="tut-seat eqB s-r"><b>Aurkaria</b><small><span class="tut-key">→</span> <span class="tut-key">D</span></small></div>
                    <div class="tut-seat yo s-b"><b>Zure kartak</b><small><span class="tut-key">↓</span> <span class="tut-key">S</span></small></div>
                </div>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Bakoitzak nori begiratzen dion irakur daiteke</span>
                        <p>Ikusten duzun aurpegian, <b>begininiak</b> mugitu egiten dira eta burua bere helburuaren aldera makurtzen da. Zuri begira badago, <b>aurpegia urrez pizten da</b>.</p>
                    </div>
                    <div class="tut-box" style="--tc:#4c566a;">
                        <span class="tt">Begirada bakarrik ibiltzen da</span>
                        <p>Ezer ukitzen ez baduzu, zure begirada bakarrik ibiltzen da aurrearen eta bi alboen artean — inoiz ez zure kartetarantz: haiei begiratzea beti da zure erabakia.</p>
                    </div>
                </div>

                <span class="tut-nota">Partida sortzean, <b>?</b> botoi bat dago «Keinuekin» ondoan, aginte hauek errepasatzen dituena.</span>
            `
        },
        {
            title: "Urrezko araua: altuena",
            content: `
                <p class="tut-lead"><b>Keinua</b> botoiak ez dizu aukeratzen uzten: <b>zure eskuak onartzen duen keinurik altuena</b> ateratzen da.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Keinu batek ez du inoiz gezurrik esaten</span>
                        <p>Hiru erregerekin ezin duzu «bi errege» keinatu disimulatzeko: <b>hiru errege</b> aterako da. Erabakitzen duzuna <b>noiz</b> keinatu eta <b>arriskatzen zaren</b> da, ez zer esaten duzun.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Lehentasun-ordena</span>
                        <p>solomiloa · duplak · 31 · hiru errege · hiru as · mediak · bi errege · bi as · 30 · itsua</p>
                        <p>Zerrendako zure eskuak betetzen duen lehenengoak agintzen du. Hiru errege eta as batekin <b>solomiloa</b> ateratzen da, eman dezakezun berririk onena.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Bat 3 segundoro</span>
                        <p>Botoia birkargatu egiten da: ezin da keinua etengabe errepikatu norbaitek begiratu arte.</p>
                    </div>
                </div>

                <div class="tut-tip">Gogoratu <b>3ak errege gisa</b> eta <b>2ak as gisa</b> balio dutela: <b>Errege · 3 · 7 · 6</b> eskuak bi errege ditu.</div>
            `
        },
        {
            title: "Keinu indartsuak",
            content: () => `
                <p class="tut-lead">Eskurik onenak kontatzen dituzten bostak. Aurpegiek keinua etengabe egiten dute.</p>
                ${tutListaSenas([
                    ['solomillo',  'Solomiloa',  'Hiru errege eta as bat',          'musu bat'],
                    ['duples',     'Duplak',     'Bi pare (edo lau berdin)',        'bekainak altxatzea'],
                    ['31',         '31',         '31 zehatzeko jokoa',              'begi-keinu bat'],
                    ['tres_reyes', 'Hiru errege', 'Hiru errege (3ak balio dute)',   'ezpainaren alde bat haginkatzea'],
                    ['tres_ases',  'Hiru as',    'Hiru as (2ak balio dute)',        'mihia alboka ateratzea'],
                ])}
            `
        },
        {
            title: "Gainerako keinuak",
            content: () => `
                <p class="tut-lead">Eta gelditzen diren bostak, <b>itsua</b> arte — hori ere informazioa baita.</p>
                ${tutListaSenas([
                    ['medias',    'Mediak',     'Beste edozeren hirukotea',      'ahoa okertzea'],
                    ['dos_reyes', 'Bi errege',  'Bi errege (3ak balio dute)',    'ezpainaren erdia haginkatzea'],
                    ['dos_ases',  'Bi as',      'Bi as (2ak balio dute)',        'mihia ateratzea'],
                    ['30',        '30',         '30eko batura, 31ra iritsi gabe', 'sorbaldak uzkurtzea'],
                    ['ciego',     'Itsua',      'Aurrekoetatik ezer ez',         'begiak ixtea'],
                ])}
                <span class="tut-nota">Keinuak tradizionalak dira, solomiloa izan ezik, etxekoa baita.</span>
            `
        },
        {
            title: "Noiz keinatu daitekeen",
            content: `
                <p class="tut-lead"><b>Keinua</b> botoia ez dago beti bizirik.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Bai: musean eta apustuetan</span>
                        <p>Horiek baitira zure bikotekideak kontatzen diozunarekin zerbait egin dezakeen uneak.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">Ez: deskartean</span>
                        <p>Deskartatzen den bitartean, <b>zure fokua zure kartetan iltzatzen da</b> eta ezin da mugitu: ikusi behar dituzu aukeratzeko, eta horrela inork ez du keinurik egiten besteak beste zerbaitetan dabiltzan bitartean.</p>
                    </div>
                    <div class="tut-box" style="--tc:#4c566a;">
                        <span class="tt">Ez: zenbaketan</span>
                        <p>Lau eskuak mahai gainean daudela, begiratzeko jokoa <b>erabat itzaltzen da</b>: ez dago aurpegirik, ezin da salatu eta <b>zure kartak azaltzen dira</b> besteak bezala. Jada ez dago ezer ezkutatzeko.</p>
                    </div>
                </div>
            `
        },
        {
            title: "«Ikusi zaitut!»",
            content: `
                <p class="tut-lead">Aurkari bat keinu bat egiten harrapatzen baduzu, <b>sala dezakezu</b>.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Nola egiten den</span>
                        <p>Ukitu aurkaria mahaian eta aukeratu zerrendatik zein keinu ikusi diozun. <b>Aurkari</b> bat baino ezin da salatu: zure bikotekidea ez, jakina.</p>
                    </div>
                    <div class="tut-box" style="--tc:#b48ead;">
                        <span class="tt">Zerrenda hori da xuleta</span>
                        <p>Aukera bakoitzak bere keinua erakusten du etengabe animatuta. Zein zen zalantzarik baduzu, ireki eta konparatu.</p>
                    </div>
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Ez du punturik ematen ez kentzen</span>
                        <p>Tanteo soziala baino ez da: mahaian ohar bat ateratzen da salatua izendatuz («BI ERREGE ikusi dizkiot Martari!») eta gutxi gehiago. Baina hortik aurrera badakizu begira zaituztela… eta haiek, begira dituzula.</p>
                    </div>
                </div>
            `
        },
        {
            title: "Lau truku",
            content: `
                <p class="tut-lead">Elkar ulertzen duen bikote bat imintzioak baino egiten ez dituen batetik bereizten duena.</p>

                <div class="tut-col">
                    <div class="tut-box" style="--tc:#ebcb8b;">
                        <span class="tt">Keinatu aurpegia urrez dagoenean</span>
                        <p>Zure bikotekidea benetan begira dagoen seinale bakarra da. Airera keinatzeak ez du balio.</p>
                    </div>
                    <div class="tut-box" style="--tc:#bf616a;">
                        <span class="tt">Begirada kentzeak ez zaitu erabat salbatzen</span>
                        <p>Norbaiti begiratzeari utzi eta <b>segundo batez</b> ikusten jarraitzen duzu. Aurkariek ere bai: begirada kentzen duten unean bertan keinatzea ez da ematen duen bezain segurua.</p>
                    </div>
                    <div class="tut-box" style="--tc:#88c0d0;">
                        <span class="tt">Itsuak ere zerbait esaten du</span>
                        <p>Ezer ez daukazula abisatzeak bien alde envidatzea aurrezten dio zure bikotekideari.</p>
                    </div>
                    <div class="tut-box" style="--tc:#a3be8c;">
                        <span class="tt">Botek ere keinatzen dute</span>
                        <p>Begiak mugitzen dituzte eta beren keinua behin egiten dute esku bakoitzeko. Garaiz begiratzen badiezu, edonor bezala harrapatzen dira.</p>
                    </div>
                </div>
            `
        }
    ]
};

// ==========================================
// EL ÍNDICE: las tres pistas
// ==========================================
const PISTAS = ['1v1', '2v2', 'senas'];

const CONTENIDO = {
    '1v1': dictTut1v1,
    '2v2': dictTut2v2,
    'senas': dictTutSenas,
};

const dictIndice = {
    es: {
        title: "Cómo se juega",
        intro: "Tres caminos. Empieza por donde te haga falta.",
        pistas: {
            '1v1': { color: '#a3be8c', icono: '⚔️', nombre: '1 contra 1',
                     sub: 'El mus desde cero: la baraja, los cuatro lances, las apuestas y el recuento.' },
            '2v2': { color: '#81a1c1', icono: '👥', nombre: '2 contra 2',
                     sub: 'Lo que cambia al jugar por parejas: equipos, declaraciones y premios que se suman.' },
            'senas': { color: '#ebcb8b', icono: '☞', nombre: 'Las señas',
                     sub: 'Los diez gestos, cuándo se pueden hacer y cómo se pillan.' },
        },
        nota: "El 1 contra 1 explica las reglas del mus; las otras dos pistas las dan por sabidas.",
    },
    en: {
        title: "How to play",
        intro: "Three paths. Start wherever you need to.",
        pistas: {
            '1v1': { color: '#a3be8c', icono: '⚔️', nombre: '1 vs 1',
                     sub: 'Mus from scratch: the deck, the four phases, the betting and the showdown.' },
            '2v2': { color: '#81a1c1', icono: '👥', nombre: '2 vs 2',
                     sub: 'What changes with partners: teams, declarations and bonuses that add up.' },
            'senas': { color: '#ebcb8b', icono: '☞', nombre: 'The signs',
                     sub: 'The ten gestures, when you may use them and how you get caught.' },
        },
        nota: "The 1 vs 1 track explains the rules of Mus; the other two take them for granted.",
    },
    eu: {
        title: "Nola jokatzen den",
        intro: "Hiru bide. Hasi behar duzun tokitik.",
        pistas: {
            '1v1': { color: '#a3be8c', icono: '⚔️', nombre: '1 aurka 1',
                     sub: 'Musa hutsetik: karta-sorta, lau lanceak, apustuak eta zenbaketa.' },
            '2v2': { color: '#81a1c1', icono: '👥', nombre: '2 aurka 2',
                     sub: 'Bikoteka jokatzean aldatzen dena: taldeak, deklarazioak eta batzen diren sariak.' },
            'senas': { color: '#ebcb8b', icono: '☞', nombre: 'Keinuak',
                     sub: 'Hamar keinuak, noiz egin daitezkeen eta nola harrapatzen diren.' },
        },
        nota: "1 aurka 1 bideak musaren arauak azaltzen ditu; beste biek jakintzat ematen dituzte.",
    }
};

// Etiquetas de los botones de navegación (fuera de las slides).
const tutBtns = {
    es: { next: "Siguiente &rarr;", prev: "&larr; Anterior", finish: "Finalizar",
          indice: "&larr; Índice", volver: "Volver al índice" },
    en: { next: "Next &rarr;",      prev: "&larr; Prev",     finish: "Finish",
          indice: "&larr; Index",  volver: "Back to the index" },
    eu: { next: "Hurrengoa &rarr;", prev: "&larr; Aurrekoa", finish: "Amaitu",
          indice: "&larr; Aurkibidea", volver: "Aurkibidera itzuli" }
};

// Devuelve el contenido del idioma activo (fallback a español).
function getIndice() {
    return dictIndice[langActual] || dictIndice.es;
}

// Diapositivas de la pista abierta ([] en el índice).
function getSlides() {
    if (!pistaActual) return [];
    const pista = CONTENIDO[pistaActual];
    return pista[langActual] || pista.es;
}

// Devuelve las etiquetas de botones del idioma activo (fallback a español).
function getTutBtns() {
    return tutBtns[langActual] || tutBtns.es;
}

let pistaActual = null;         // null = índice; si no, '1v1' | '2v2' | 'senas'
let currentSlideIndex = 0;
let openedFromGame = false;

// En la pista del 1v1, la diapositiva 8 invita a practicar: no pinta nada
// enseñarla a quien ya está jugando, así que se salta al abrir desde la mesa.
const IDX_PRACTICA_1V1 = 8;

function saltaPractica(i) {
    return openedFromGame && pistaActual === '1v1' && i === IDX_PRACTICA_1V1;
}

// Variables del DOM
const modalTutorial = document.getElementById('modal-tutorial');
const tutorialContent = document.getElementById('tutorial-content');
const btnPrev = document.getElementById('tut-prev');
const btnNext = document.getElementById('tut-next');
const btnIndice = document.getElementById('btn-tutorial-indice');
const dotsContainer = document.getElementById('tut-dots');
const navTutorial = document.getElementById('tut-nav');

/** El índice: las tres pistas, cada una con su color. */
function renderIndice() {
    const idx = getIndice();
    const botones = PISTAS.map(id => {
        const p = idx.pistas[id];
        return `
            <button class="tut-hub-btn" data-tut-pista="${id}" style="--tc:${p.color};">
                <span class="tut-hub-ico">${p.icono}</span>
                <span><b>${p.nombre}</b><small>${p.sub}</small></span>
            </button>`;
    }).join('');

    tutorialContent.innerHTML = `
        <h2 class="tut-titulo" style="color: #a3be8c; font-size: 1.8em; margin-bottom: 8px; margin-top: 0;">${idx.title}</h2>
        <p style="color: #d8dee9; font-size: 0.98em; margin: 0 0 22px;">${idx.intro}</p>
        <div class="tut-hub">${botones}</div>
        <span class="tut-nota">${idx.nota}</span>
    `;

    // En el índice la barra de abajo no pinta nada: se quita entera.
    dotsContainer.innerHTML = '';
    if (navTutorial) navTutorial.classList.add('hidden');
    if (btnIndice) btnIndice.classList.add('hidden');
}

// Inicializar el carrusel
function renderSlide(index) {
    const slides = getSlides();
    const btns = getTutBtns();
    const slide = slides[index];
    if (!slide) return renderIndice();

    // El contenido puede ser una función (las señas, que necesitan la cara SVG).
    const cuerpo = (typeof slide.content === 'function') ? slide.content() : slide.content;

    // Inyectar HTML
    tutorialContent.innerHTML = `
        <h2 class="tut-titulo" style="color: #a3be8c; font-size: 1.8em; margin-bottom: 20px; margin-top: 0;">${slide.title}</h2>
        <div>${cuerpo}</div>
    `;

    if (btnIndice) btnIndice.classList.remove('hidden');
    if (navTutorial) navTutorial.classList.remove('hidden');
    btnNext.style.visibility = 'visible';

    // En la primera diapositiva, "atrás" devuelve al índice.
    btnPrev.style.visibility = 'visible';
    btnPrev.innerHTML = index === 0 ? btns.indice : btns.prev;

    if (index === slides.length - 1) {
        btnNext.innerHTML = btns.finish;
        btnNext.style.backgroundColor = "#ebcb8b";
    } else {
        btnNext.innerHTML = btns.next;
        btnNext.style.backgroundColor = "#a3be8c";
    }

    // Actualizar puntitos
    dotsContainer.innerHTML = '';
    slides.forEach((_, i) => {
        // Omitimos el puntito de la diapositiva de práctica si venimos del juego
        if (saltaPractica(i)) return;

        const dot = document.createElement('div');
        dot.style.width = '10px';
        dot.style.height = '10px';
        dot.style.borderRadius = '50%';
        dot.style.backgroundColor = i === index ? '#88c0d0' : '#4c566a';
        dot.style.transition = '0.3s';
        dotsContainer.appendChild(dot);
    });
}

/** Pinta lo que toque: el índice o la diapositiva en la que estemos. */
function renderTutorial() {
    if (pistaActual) renderSlide(currentSlideIndex);
    else renderIndice();
}

/** Abre una pista por su nombre. La usan el índice, los enlaces entre pistas y
 *  la ayuda de las señas del menú (`window.tutorialAbrirPista`). */
function irAPista(id, index) {
    if (!CONTENIDO[id]) return;
    pistaActual = id;
    currentSlideIndex = index || 0;
    if (saltaPractica(currentSlideIndex)) currentSlideIndex++;
    tutorialContent.scrollTop = 0;
    renderSlide(currentSlideIndex);
}

function volverAlIndice() {
    pistaActual = null;
    tutorialContent.scrollTop = 0;
    renderIndice();
}

// Eventos de botones con salto inteligente
btnNext.addEventListener('click', () => {
    if (!pistaActual) return;
    if (currentSlideIndex < getSlides().length - 1) {
        currentSlideIndex++;

        // Si venimos del juego, la diapositiva de práctica se salta.
        if (saltaPractica(currentSlideIndex)) currentSlideIndex++;

        tutorialContent.scrollTop = 0;
        renderSlide(currentSlideIndex);
    } else {
        cerrarTutorial();
    }
});

btnPrev.addEventListener('click', () => {
    if (!pistaActual) return;
    if (currentSlideIndex === 0) { volverAlIndice(); return; }

    currentSlideIndex--;
    if (saltaPractica(currentSlideIndex)) currentSlideIndex--;

    tutorialContent.scrollTop = 0;
    renderSlide(currentSlideIndex);
});

if (btnIndice) btnIndice.addEventListener('click', volverAlIndice);

// Los botones que llevan de una pista a otra viven dentro del contenido.
tutorialContent.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-tut-pista]');
    if (btn) irAPista(btn.dataset.tutPista);
});

document.getElementById('btn-cerrar-tutorial').addEventListener('click', cerrarTutorial);

/** Deja el tutorial a la vista (y esconde lo demás). No decide qué se pinta. */
function abrirTutorial() {
    document.getElementById('modal-overlay').style.display = 'flex';
    document.getElementById('modal-overlay').classList.remove('hidden');

    // Ocultar resto de modales
    document.getElementById('modal-login').classList.add('hidden');
    document.getElementById('modal-signup').classList.add('hidden');
    const ml = document.getElementById('modal-leaderboard'); if(ml) ml.classList.add('hidden');
    const mp = document.getElementById('modal-privacy'); if(mp) mp.classList.add('hidden');
    const mj = document.getElementById('modal-play'); if(mj) mj.classList.add('hidden');

    modalTutorial.classList.remove('hidden');
}

// Abrir desde el menú principal: siempre por el índice.
document.getElementById('btn-tutorial').addEventListener('click', () => {
    openedFromGame = false;
    abrirTutorial();
    volverAlIndice();
});

function cerrarTutorial() {
    modalTutorial.classList.add('hidden');
    document.getElementById('modal-overlay').style.display = 'none';
    document.getElementById('modal-overlay').classList.add('hidden');
}

// Exponer la función para que los botones dentro del HTML puedan usarla
// (los ejemplos del 1v1 saltan con ella desde la diapositiva de práctica).
window.goToSlide = function(index) {
    if (index >= 0 && index < getSlides().length) {
        currentSlideIndex = index;
        tutorialContent.scrollTop = 0;
        renderSlide(currentSlideIndex);
    }
};

/** Abre el tutorial directamente en una pista. La usa menu.js desde la ayuda
 *  de las señas. */
window.tutorialAbrirPista = function(id, index) {
    openedFromGame = false;
    abrirTutorial();
    irAPista(id, index);
};

// Re-renderizar el tutorial cuando se cambia de idioma (si está abierto).
// app.js registra su listener de #btn-lang ANTES que este, por lo que cuando
// se ejecuta este callback `langActual` ya tiene el nuevo valor.
const btnLangTut = document.getElementById('btn-lang');
if (btnLangTut) {
    btnLangTut.addEventListener('click', () => {
        if (modalTutorial && !modalTutorial.classList.contains('hidden')) {
            renderTutorial();
        }
    });
}

// ==========================================
// CAPTURA DE EVENTOS (BOTONES GLOBALES DEL TUTORIAL)
// ==========================================
document.addEventListener('click', function(e) {

    // 1. Botón de "Start Practising" -> Partida contra bot al mejor de 1
    if (e.target && e.target.id === 'btn-start-interactive') {
        cerrarTutorial();

        const btnBot = document.getElementById('btn-jugar-bot');
        const inMejorDe = document.getElementById('in-mejor-de');

        if (btnBot) {
            // Guardamos el valor que el usuario tuviera puesto
            const valorOriginal = inMejorDe ? inMejorDe.value : "3";

            // Forzamos al mejor de 1
            if (inMejorDe) inMejorDe.value = "1";

            // Simulamos el clic para lanzar toda la maquinaria de app.js
            btnBot.click();

            // Devolvemos el selector a su estado original
            if (inMejorDe) inMejorDe.value = valorOriginal;
        }
    }

    // 2. Botón de ayuda durante la partida [?] — abre la pista del modo que se
    //    esté jugando. Desde la mesa NO se enseña la diapositiva de práctica.
    const btnAyuda = e.target && e.target.closest
        ? e.target.closest('#btn-help-game, #btn-help-game-4') : null;
    if (btnAyuda) {
        openedFromGame = true;
        abrirTutorial();

        const pistaDelJuego = (btnAyuda.id === 'btn-help-game-4') ? '2v2' : '1v1';
        // Si ya estaba en esa pista, se sigue donde se dejó.
        if (pistaActual === pistaDelJuego) {
            if (saltaPractica(currentSlideIndex)) currentSlideIndex++;
            renderSlide(currentSlideIndex);
        } else {
            irAPista(pistaDelJuego);
        }
    }
});




// ==========================================
// GESTOR INTERACTIVO DE ZOOM PARA MÓVILES
// ==========================================
document.getElementById('tutorial-content').addEventListener('click', function(e) {
    // Buscamos si el clic se ha realizado dentro de un grupo de cartas zoomable
    const group = e.target.closest('.tut-cards-group');

    if (group) {
        // Solo actuamos si estamos en una pantalla móvil o tablet
        if (window.innerWidth <= 768) {
            const yaAmpliando = group.classList.contains('tut-mobile-zoom');

            // Limpiamos cualquier otra carta que estuviera ampliada en la diapositiva
            document.querySelectorAll('.tut-cards-group').forEach(g => g.classList.remove('tut-mobile-zoom'));

            // Si no estaba ampliada, la ampliamos ahora
            if (!yaAmpliando) {
                group.classList.add('tut-mobile-zoom');
            }
        }
    } else {
        // Si el usuario toca en cualquier otra parte de la pantalla, replegamos el zoom activo
        document.querySelectorAll('.tut-cards-group').forEach(g => g.classList.remove('tut-mobile-zoom'));
    }
});
