// table4.js — Renderizador de la mesa de Mus a 4 jugadores (2v2).
// Se carga ANTES de app4.js. Reutiliza los globales de app.js (t, t_dinamico,
// langActual). app4.js llama a renderMesa4(prev, next); aquí solo pintamos la
// vista (no hay sockets). La selección de cartas para el descarte vive aquí.

// Estado compartido con app4.js (var: sin TDZ, accesible desde el otro script).
var cartasSeleccionadas4 = [];
var TURNO_SEGUNDOS_4 = 30;   // debe coincidir con server_mus4.TURNO_SEGUNDOS

// Asigna a cada asiento su hueco visual, relativo al espectador:
//   bottom = yo, top = compañero (+2), left = (+1), right = (+3).
function slotDeAsiento4(miAsiento, asiento) {
    const rel = ((asiento - miAsiento) + 4) % 4;
    return ['bottom', 'left', 'top', 'right'][rel];
}

function cartaBackHTML4() {
    return `<div class="carta-4"><img src="/static/img/card_back.webp" draggable="false" oncontextmenu="return false;"></div>`;
}

function renderChips4(seatInfo, fase) {
    const chips = [];
    if (seatInfo.descartes_hechos > 0 && (fase === 'mus' || fase === 'descarte')) {
        chips.push(`<span class="chip descartes">↺ ${seatInfo.descartes_hechos}</span>`);
    }
    if (seatInfo.pares_dec !== null && seatInfo.pares_dec !== undefined) {
        chips.push(seatInfo.pares_dec
            ? `<span class="chip si">${t('pares_si')}</span>`
            : `<span class="chip no">${t('pares_no')}</span>`);
    }
    if (seatInfo.juego_dec !== null && seatInfo.juego_dec !== undefined) {
        chips.push(seatInfo.juego_dec
            ? `<span class="chip si">${t('juego_si')}</span>`
            : `<span class="chip no">${t('juego_no')}</span>`);
    }
    return chips.join('');
}

// Pinta las cartas de un asiento (mías clicables; rivales/compañero al dorso;
// todas boca arriba en el recuento).
function renderCartasAsiento4(el, seatInfo, next, esYo, animarDeal, animarFlip) {
    const cont = el.querySelector('.seat-cards');
    cont.innerHTML = '';

    if (esYo) {
        const cartas = next.mis_cartas || [];
        cartas.forEach((carta, index) => {
            const div = document.createElement('div');
            div.className = 'carta-4';
            if (animarDeal) div.classList.add('deal-anim');
            div.innerHTML = `<img src="${carta.img}" alt="${carta.texto || ''}" draggable="false" oncontextmenu="return false;">`;
            if (cartasSeleccionadas4.includes(index)) div.classList.add('seleccionada');
            div.onclick = () => {
                if (next.fase === 'descarte' && !next.mis_descartes_listos) {
                    const pos = cartasSeleccionadas4.indexOf(index);
                    if (pos === -1) { cartasSeleccionadas4.push(index); div.classList.add('seleccionada'); }
                    else { cartasSeleccionadas4.splice(pos, 1); div.classList.remove('seleccionada'); }
                    const btn = document.getElementById('btn-descartar-4');
                    if (btn) { btn.innerText = `${t('btn_descartar')} (${cartasSeleccionadas4.length})`; btn.disabled = cartasSeleccionadas4.length === 0; }
                }
            };
            cont.appendChild(div);
        });
        return;
    }

    if (next.fase === 'recuento' && seatInfo.cartas) {
        seatInfo.cartas.forEach(c => {
            const div = document.createElement('div');
            div.className = 'carta-4';
            if (animarFlip) div.classList.add('flip-anim');
            div.innerHTML = `<img src="${c.img}" alt="${c.texto || ''}" draggable="false" oncontextmenu="return false;">`;
            cont.appendChild(div);
        });
        return;
    }

    if (next.fase === 'espera_reparto') return;   // aún sin repartir
    // Resto de fases: 4 dorsos.
    cont.innerHTML = cartaBackHTML4().repeat(4);
}

function renderSeat4(next, seatInfo, animarDeal, animarFlip) {
    const slot = slotDeAsiento4(next.mi_asiento, seatInfo.asiento);
    const el = document.getElementById('seat-' + slot);
    if (!el) return;
    const esYo = (seatInfo.asiento === next.mi_asiento);

    el.className = 'seat-4 equipo-' + seatInfo.equipo;
    if (seatInfo.asiento === next.turno_de && next.fase !== 'recuento') el.classList.add('turno-activo');
    if (!seatInfo.presente) el.classList.add('ausente');

    let etiqueta = '';
    if (esYo) etiqueta = `<span class="you-tag">${t('txt_tu')}</span>`;
    else if (slot === 'top') etiqueta = `<span class="partner-tag">${t('tu_pareja')}</span>`;
    // Quien es mano lleva un rótulo en oro (antes era un emoji de corona, que
    // desentonaba con el resto de la mesa).
    const manoBadge = seatInfo.es_mano ? `<span class="mano-badge" title="${t('eres_mano')}">${t('txt_mano')}</span>` : '';
    // El nombre lo elige el jugador: se escapa antes de meterlo en el HTML.
    el.querySelector('.seat-name').innerHTML = `${escHtml(seatInfo.nombre)}${manoBadge}${etiqueta}`;
    el.querySelector('.seat-chips').innerHTML = renderChips4(seatInfo, next.fase);

    renderCartasAsiento4(el, seatInfo, next, esYo, animarDeal, animarFlip);
}

function renderScores4(next) {
    const a = document.getElementById('score-team-a');
    const b = document.getElementById('score-team-b');
    if (!a || !b) return;
    a.querySelector('.pts').innerText = next.puntos.A;
    b.querySelector('.pts').innerText = next.puntos.B;
    // Las partidas ganadas, en piedras (pintarPiedras vive en app.js).
    pintarPiedras(a.querySelector('.team-games'), next.partidas.A, next.al_mejor_de);
    pintarPiedras(b.querySelector('.team-games'), next.partidas.B, next.al_mejor_de);
    a.classList.toggle('mi-equipo', next.mi_equipo === 'A');
    b.classList.toggle('mi-equipo', next.mi_equipo === 'B');
    const md = document.getElementById('score-mejor-de-4');
    if (md) md.innerText = `${t('al_mejor_de')} ${next.al_mejor_de}`;
}

// Rejilla de botes Grande/Chica/Pares/Juego (reutiliza el estilo del cliente 2p).
function renderBettingLog4(next) {
    const logDiv = document.getElementById('betting-log-4');
    if (!logDiv) return;
    if (next.fase !== 'apuestas' && next.fase !== 'recuento') { logDiv.classList.add('hidden'); return; }
    logDiv.classList.remove('hidden');

    const ap = next.apuestas || {};
    let fAct = ap.fase_actual || '';
    if (next.mensaje_transicion && next.mensaje_transicion.fase) fAct = next.mensaje_transicion.fase;

    // La apuesta en el aire: sin apuesta, la caja se queda vacía y el CSS la
    // colapsa (ver .cm-aire en static/game.css).
    let enAire = '<div class="cm-aire">';
    if (ap.subida > 0 || ap.subida === 'ÓRDAGO') {
        const cant = ap.subida === 'ÓRDAGO' ? t('un_ordago') : ap.subida;
        const texto = ap.mi_equipo_sube ? t('has_subido') + cant : t('te_suben') + cant;
        enAire += `<p class="cm-aire-vista">${t('info_apuesta_vista')} <b>${ap.apuesta_vista}</b></p>`;
        enAire += `<p class="cm-aire-sube${ap.mi_equipo_sube ? ' es-mia' : ''}">${texto}</p>`;
    }
    enAire += '</div>';

    // El tanteador de los cuatro lances es el mismo que en la mesa de 1v1
    // (htmlTanteador vive en app.js); aquí el deje lo gana "mi equipo".
    logDiv.innerHTML = enAire + htmlTanteador(ap, fAct, (fase, apuestas) => {
        const deje = apuestas.dejes && apuestas.dejes[fase];
        return deje ? { valor: deje.valor, gano: deje.gano_mi_equipo } : null;
    });
}

// ---------- Animaciones sobre deltas ----------
function animarPuntos4(prev, next) {
    if (!prev) return;
    ['A', 'B'].forEach(eq => {
        const delta = next.puntos[eq] - (prev.puntos ? prev.puntos[eq] : 0);
        if (delta > 0) {
            const badge = document.getElementById('score-team-' + eq.toLowerCase());
            if (!badge) return;
            const float = document.createElement('div');
            float.className = 'puntos-flotantes';
            float.style.color = eq === 'A' ? 'var(--equipo-a)' : 'var(--equipo-b)';
            float.innerText = `+${delta}`;
            const r = badge.getBoundingClientRect();
            float.style.left = (r.left + r.width / 2 - 15) + 'px';
            float.style.top = (r.top - 10) + 'px';
            document.body.appendChild(float);
            setTimeout(() => float.remove(), 950);
        }
    });
}

function animarOrdago4() {
    const mesa = document.getElementById('mesa-4');
    if (mesa) { mesa.classList.remove('ordago-shake'); void mesa.offsetWidth; mesa.classList.add('ordago-shake'); }
    const flash = document.createElement('div');
    flash.id = 'ordago-flash-4';
    document.body.appendChild(flash);
    setTimeout(() => flash.remove(), 500);
}

// ---------- Punto de entrada ----------
function renderMesa4(prev, next) {
    const animarDeal = prev && prev.fase === 'espera_reparto' && next.fase === 'mus';
    const animarFlip = next.fase === 'recuento' && (!prev || prev.fase !== 'recuento');

    // Reinicia la selección de descarte al cambiar de fase/reparto.
    if (!prev || prev.fase !== 'descarte' || next.fase !== 'descarte') {
        if (next.fase !== 'descarte' || !next.mis_descartes_listos) cartasSeleccionadas4 = [];
    }

    (next.seats || []).forEach(seatInfo => renderSeat4(next, seatInfo, animarDeal, animarFlip));
    renderScores4(next);
    renderBettingLog4(next);

    // Órdago: al pasar la subida a 'ÓRDAGO'.
    const prevOrdago = prev && prev.apuestas && prev.apuestas.subida === 'ÓRDAGO';
    const nowOrdago = next.apuestas && next.apuestas.subida === 'ÓRDAGO';
    if (nowOrdago && !prevOrdago) animarOrdago4();

    animarPuntos4(prev, next);
}
