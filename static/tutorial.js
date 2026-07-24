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
`;
document.head.appendChild(tutStyles);



// ==========================================
// MOTOR DEL TUTORIAL DE MUS (BILINGÜE ES/EN)
// ==========================================
// El contenido vive en `dictTutorial`, indexado por la variable global
// `langActual` que define app.js (única fuente de verdad del idioma; se
// persiste en localStorage con la clave 'callmus_lang'). Ambos arrays (es/en)
// tienen el MISMO número de slides y el mismo orden, para que los índices
// (slide 8 = práctica, slide 9 = Ejemplo 1) sean idénticos en los dos idiomas.

const dictTutorial = {
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
    ]
};

// Etiquetas de los botones de navegación (fuera de las slides).
const tutBtns = {
    es: { next: "Siguiente &rarr;", prev: "&larr; Anterior", finish: "Finalizar" },
    en: { next: "Next &rarr;",      prev: "&larr; Prev",     finish: "Finish"   }
};

// Devuelve el array de slides del idioma activo (fallback a español).
function getSlides() {
    return dictTutorial[langActual] || dictTutorial.es;
}

// Devuelve las etiquetas de botones del idioma activo (fallback a español).
function getTutBtns() {
    return tutBtns[langActual] || tutBtns.es;
}

let currentSlideIndex = 0;
let openedFromGame = false;

// Variables del DOM
const modalTutorial = document.getElementById('modal-tutorial');
const tutorialContent = document.getElementById('tutorial-content');
const btnPrev = document.getElementById('tut-prev');
const btnNext = document.getElementById('tut-next');
const dotsContainer = document.getElementById('tut-dots');

// Inicializar el carrusel
function renderSlide(index) {
    const slides = getSlides();
    const btns = getTutBtns();
    const slide = slides[index];

    // Inyectar HTML
    tutorialContent.innerHTML = `
        <h2 style="color: #a3be8c; font-size: 1.8em; margin-bottom: 20px; margin-top: 0;">${slide.title}</h2>
        <div>${slide.content}</div>
    `;

    // Actualizar visibilidad y texto de botones (localizado)
    btnPrev.style.visibility = index === 0 ? 'hidden' : 'visible';
    btnPrev.innerHTML = btns.prev;

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
        if (openedFromGame && i === 8) return;

        const dot = document.createElement('div');
        dot.style.width = '10px';
        dot.style.height = '10px';
        dot.style.borderRadius = '50%';
        dot.style.backgroundColor = i === index ? '#88c0d0' : '#4c566a';
        dot.style.transition = '0.3s';
        dotsContainer.appendChild(dot);
    });
}

// Eventos de botones con salto inteligente
btnNext.addEventListener('click', () => {
    if (currentSlideIndex < getSlides().length - 1) {
        currentSlideIndex++;

        // Si venimos del juego y toca la slide 8, saltamos directo a la 9 (Ejemplo 1)
        if (openedFromGame && currentSlideIndex === 8) {
            currentSlideIndex++;
        }

        renderSlide(currentSlideIndex);
    } else {
        cerrarTutorial();
    }
});

btnPrev.addEventListener('click', () => {
    if (currentSlideIndex > 0) {
        currentSlideIndex--;

        // Si venimos del juego y retrocedemos a la slide 8, saltamos directo a la 7
        if (openedFromGame && currentSlideIndex === 8) {
            currentSlideIndex--;
        }

        renderSlide(currentSlideIndex);
    }
});

document.getElementById('btn-cerrar-tutorial').addEventListener('click', cerrarTutorial);

// Abrir desde el menú principal
document.getElementById('btn-tutorial').addEventListener('click', () => {
    openedFromGame = false;
    document.getElementById('modal-overlay').style.display = 'flex';
    document.getElementById('modal-overlay').classList.remove('hidden');

    // Ocultar resto de modales
    document.getElementById('modal-login').classList.add('hidden');
    document.getElementById('modal-signup').classList.add('hidden');
    const ml = document.getElementById('modal-leaderboard'); if(ml) ml.classList.add('hidden');
    const mp = document.getElementById('modal-privacy'); if(mp) mp.classList.add('hidden');

    modalTutorial.classList.remove('hidden');

    // Empezar desde el principio siempre
    currentSlideIndex = 0;
    renderSlide(currentSlideIndex);
});

function cerrarTutorial() {
    modalTutorial.classList.add('hidden');
    document.getElementById('modal-overlay').style.display = 'none';
    document.getElementById('modal-overlay').classList.add('hidden');
}

// Exponer la función para que los botones dentro del HTML puedan usarla
window.goToSlide = function(index) {
    if (index >= 0 && index < getSlides().length) {
        currentSlideIndex = index;
        renderSlide(currentSlideIndex);
    }
};

// Re-renderizar el tutorial cuando se cambia de idioma (si está abierto).
// app.js registra su listener de #btn-lang ANTES que este, por lo que cuando
// se ejecuta este callback `langActual` ya tiene el nuevo valor.
const btnLangTut = document.getElementById('btn-lang');
if (btnLangTut) {
    btnLangTut.addEventListener('click', () => {
        if (modalTutorial && !modalTutorial.classList.contains('hidden')) {
            renderSlide(currentSlideIndex);
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

    // 2. Botón de ayuda durante la partida [?]
    if (e.target && (e.target.id === 'btn-help-game' || e.target.closest('#btn-help-game'))) {
        openedFromGame = true; // Desde el juego NO se muestra la slide de práctica
        const overlay = document.getElementById('modal-overlay');
        const modalTut = document.getElementById('modal-tutorial');

        if (overlay && modalTut) {
            overlay.style.display = 'flex';
            overlay.classList.remove('hidden');

            const modalesAOcultar = ['modal-login', 'modal-signup', 'modal-leaderboard', 'modal-privacy'];
            modalesAOcultar.forEach(id => {
                const m = document.getElementById(id);
                if (m) m.classList.add('hidden');
            });

            modalTut.classList.remove('hidden');

            // Si estaba en la slide de práctica por el menú, lo movemos a la siguiente por seguridad
            if (currentSlideIndex === 8) {
                currentSlideIndex = 9;
            }
            renderSlide(currentSlideIndex);
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
