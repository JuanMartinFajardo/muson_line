// sorteo.js — El sorteo de la Mano: la ruleta de pintas que se ve al empezar
// una partida (1v1 y 2v2), antes de repartir.
//
// Cada jugador recibe pinta(s): en el 1v1 dos al azar, en el 2v2 una sola,
// repartidas en sentido antihorario (oros → copas → espadas → bastos) desde un
// jugador cualquiera. En el centro giran las cuatro pintas como el adorno del
// menú (menu.css, `cm-orn-oro`): el oro corre deprisa y va frenando hasta
// pararse. Donde para, ése es Mano.
//
// El reparto y la parada los decide el SERVIDOR y viajan en el `sorteo` de
// `iniciar_partida` / `iniciar_partida_4`: así los dos (o cuatro) clientes ven
// exactamente el mismo sorteo, y la parada siempre cae en una pinta de quien el
// motor ya había echado a suertes como Mano.
//
// Uso:  SorteoMano.jugar({ jugadores: [{slot, nombre, palos:[…]}], parada, texto })
//       → Promise que se resuelve cuando el telón se levanta.
// Se carga después de app.js: usa `dict`, `t`, `t_dinamico` y `escHtml`.

const SorteoMano = (function () {

    const PALOS = ['oros', 'copas', 'espadas', 'bastos'];

    const GIRO_MS = 2000;   // lo que dura la ruleta, de principio a parada
    const POSO_MS = 1100;   // lo que se queda el resultado en pantalla
    const TELON_MS = 380;   // el desvanecido final
    const VUELTAS = 6;      // vueltas completas antes de la parada

    Object.assign(dict.es, {
        sorteo_titulo: '¿Quién es Mano?',
        sorteo_es_mano: '{nombre} es Mano',
        sorteo_eres_mano: 'Eres Mano',
    });
    Object.assign(dict.en, {
        sorteo_titulo: 'Who deals first?',
        sorteo_es_mano: '{nombre} is Mano',
        sorteo_eres_mano: 'You are Mano',
    });
    Object.assign(dict.eu, {
        sorteo_titulo: 'Nor da eskua?',
        sorteo_es_mano: '{nombre} da eskua',
        sorteo_eres_mano: 'Zu zara eskua',
    });

    function sinMovimiento() {
        return window.matchMedia
            && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    function svgPinta(palo, clase) {
        return `<svg class="pinta ${clase}" data-palo="${palo}" aria-hidden="true">`
             + `<use href="#pinta-${palo}"></use></svg>`;
    }

    function construir(op) {
        const capa = document.createElement('div');
        capa.className = 'sorteo';
        capa.setAttribute('role', 'status');

        const sitios = (op.jugadores || []).map(j => `
            <div class="sorteo-sitio" data-slot="${j.slot}">
                <div class="sorteo-palos">${j.palos.map(p => svgPinta(p, 'sorteo-palo')).join('')}</div>
                <div class="sorteo-nombre">${escHtml(j.nombre || '')}</div>
            </div>`).join('');

        capa.innerHTML = `
            <div class="sorteo-centro">
                <p class="sorteo-titulo">${t('sorteo_titulo')}</p>
                <div class="sorteo-ruleta">
                    ${PALOS.map(p => svgPinta(p, 'sorteo-pinta')).join('')}
                </div>
                <p class="sorteo-resultado"></p>
            </div>${sitios}`;
        return capa;
    }

    // Los tiempos de cada paso: empieza rapidísimo y se va estirando (potencia
    // cúbica), pero el total es siempre GIRO_MS pase lo que pase, porque al
    // final se reescalan. Así la animación dura lo mismo aunque cambien las
    // vueltas o la pinta donde para.
    function tiempos(pasos) {
        const crudos = [];
        for (let i = 0; i < pasos; i++) {
            crudos.push(1 + 11 * Math.pow((i + 1) / pasos, 3));
        }
        const suma = crudos.reduce((a, b) => a + b, 0);
        return crudos.map(x => x * GIRO_MS / suma);
    }

    function jugar(op) {
        return new Promise(resolve => {
            const objetivo = PALOS.indexOf(op.parada);
            if (objetivo < 0) { resolve(); return; }

            const capa = construir(op);
            document.body.appendChild(capa);
            const pintas = capa.querySelectorAll('.sorteo-pinta');
            const rotulo = capa.querySelector('.sorteo-resultado');

            const encender = (i) => {
                pintas.forEach((el, k) => el.classList.toggle('encendida', k === i));
            };

            const rematar = () => {
                pintas[objetivo].classList.add('parada');
                // La pinta ganadora también se enciende en el sitio de su dueño.
                capa.querySelectorAll(`.sorteo-palo[data-palo="${op.parada}"]`)
                    .forEach(el => el.closest('.sorteo-sitio').classList.add('ganador'));
                rotulo.textContent = op.texto || '';
                rotulo.classList.add('visible');
                setTimeout(() => {
                    capa.classList.add('telon');
                    setTimeout(() => { capa.remove(); resolve(); }, TELON_MS);
                }, POSO_MS);
            };

            // Sin animación (ajuste del sistema): se enseña el resultado y ya.
            if (sinMovimiento()) {
                encender(objetivo);
                rematar();
                return;
            }

            encender(0);
            // Vueltas completas + lo que falte para caer en la pinta de la Mano.
            const pasos = VUELTAS * PALOS.length + ((objetivo % PALOS.length) + PALOS.length) % PALOS.length;
            const ms = tiempos(pasos);
            let paso = 0;
            const siguiente = () => {
                paso++;
                encender(paso % PALOS.length);
                if (paso >= pasos) { rematar(); return; }
                setTimeout(siguiente, ms[paso]);
            };
            setTimeout(siguiente, ms[0]);
        });
    }

    // ---- Armadores de la carga que manda el servidor ----------------------

    // 1v1: dos pintas por jugador. Yo abajo, el rival arriba.
    function jugar2p(s) {
        if (!s || !s.parada) return Promise.resolve();
        return jugar({
            parada: s.parada,
            texto: s.soy_mano ? t('sorteo_eres_mano')
                              : t_dinamico('sorteo_es_mano', { nombre: s.nombre_mano }),
            jugadores: [
                { slot: 'top', nombre: s.nombre_rival, palos: s.palos_rival || [] },
                { slot: 'bottom', nombre: t('txt_tu'), palos: s.palos_yo || [] },
            ],
        });
    }

    // 2v2: una pinta por asiento. Los asientos se colocan como en la mesa
    // (table4.js: `slotDeAsiento4`), con el mío siempre abajo.
    function jugar4p(s, miAsiento) {
        if (!s || !s.parada) return Promise.resolve();
        const slots = ['bottom', 'left', 'top', 'right'];
        const mio = (miAsiento === null || miAsiento === undefined) ? 0 : miAsiento;
        const jugadores = [];
        for (let a = 0; a < 4; a++) {
            const palo = s.palos[a] || s.palos[String(a)];
            const nombre = (s.nombres || {})[a] || (s.nombres || {})[String(a)] || '';
            jugadores.push({
                slot: slots[((a - mio) + 4) % 4],
                nombre: (a === mio) ? t('txt_tu') : nombre,
                palos: palo ? [palo] : [],
            });
        }
        return jugar({
            parada: s.parada,
            texto: (s.mano === mio) ? t('sorteo_eres_mano')
                                    : t_dinamico('sorteo_es_mano', {
                                          nombre: (s.nombres || {})[s.mano]
                                               || (s.nombres || {})[String(s.mano)] || '' }),
            jugadores,
        });
    }

    return { jugar, jugar2p, jugar4p };
})();
