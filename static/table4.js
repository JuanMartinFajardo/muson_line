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
    if (esYo) etiqueta = `<span class="you-tag">(${t('txt_tu')})</span>`;
    else if (slot === 'top') etiqueta = `<span class="partner-tag">(${t('tu_pareja')})</span>`;
    const manoBadge = seatInfo.es_mano ? `<span class="mano-badge" title="${t('eres_mano')}">👑</span>` : '';
    el.querySelector('.seat-name').innerHTML = `${seatInfo.nombre}${manoBadge}${etiqueta}`;
    el.querySelector('.seat-chips').innerHTML = renderChips4(seatInfo, next.fase);

    renderCartasAsiento4(el, seatInfo, next, esYo, animarDeal, animarFlip);
}

function renderScores4(next) {
    const a = document.getElementById('score-team-a');
    const b = document.getElementById('score-team-b');
    if (!a || !b) return;
    a.querySelector('.pts').innerText = next.puntos.A;
    b.querySelector('.pts').innerText = next.puntos.B;
    a.querySelector('.team-games').innerText = next.partidas.A;
    b.querySelector('.team-games').innerText = next.partidas.B;
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

    const colStyle = (activo) => activo
        ? 'color:#000;background:#fff;font-weight:bold;border-radius:3px;padding:2px 5px;text-align:center;letter-spacing:1px;'
        : 'color:#888;padding:2px 5px;text-align:center;letter-spacing:1px;';

    let enAire = `<div style="min-height:52px;display:flex;flex-direction:column;justify-content:center;align-items:center;margin-bottom:8px;border-bottom:1px dashed rgba(255,255,255,0.2);padding-bottom:8px;">`;
    if (ap.subida > 0 || ap.subida === 'ÓRDAGO') {
        const cant = ap.subida === 'ÓRDAGO' ? t('un_ordago') : ap.subida;
        const texto = ap.mi_equipo_sube ? t('has_subido') + cant : t('te_suben') + cant;
        const color = ap.mi_equipo_sube ? '#fff' : '#aaa';
        enAire += `<p style="font-size:1em;margin:0 0 4px 0;">${t('info_apuesta_vista')} <span class="highlight">${ap.apuesta_vista}</span></p>`;
        enAire += `<p style="font-size:1.1em;font-weight:bold;color:${color};margin:0;">${texto}</p>`;
    }
    enAire += `</div>`;

    const boteTexto = (fase) => {
        if (ap.dejes && ap.dejes[fase]) { const d = ap.dejes[fase]; return d.gano_mi_equipo ? `${d.valor}(+)` : `${d.valor}(-)`; }
        return (ap.botes && ap.botes[fase]) || 0;
    };
    const labelJuego = ap.juego_es_punto ? t('fase_punto') : t('fase_juego');
    const cols = [['Grande', t('fase_grande')], ['Chica', t('fase_chica')], ['Pares', t('fase_pares')], ['Juego', labelJuego]];
    let botes = `<div style="display:flex;justify-content:space-around;width:100%;">`;
    cols.forEach(([key, label]) => {
        botes += `<div style="display:flex;flex-direction:column;flex:1;">
            <div style="${colStyle(fAct === key)}">${label}</div>
            <div style="text-align:center;font-size:1.15em;">${boteTexto(key)}</div></div>`;
    });
    botes += `</div>`;
    logDiv.innerHTML = enAire + botes;
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
