// senas4.js — Señas del Mus a 4 jugadores (2v2).
//
// Se carga DESPUÉS de table4.js y app4.js. Reutiliza los globales de app.js
// (`socket`, `dict`, `t`, `t_dinamico`, `aplicarTraduccion`, `escHtml`).
//
// De qué va: en una mesa con señas tus cartas están boca abajo. Con las flechas,
// WASD o deslizando el dedo giras la cabeza hacia tu pareja (arriba), hacia cada
// rival (izquierda/derecha) o hacia tus cartas (abajo). Sólo ves la cara —y por
// tanto la seña— de quien estás mirando en ese momento.
//
// Reparto de responsabilidades:
//   · El SERVIDOR decide quién ve qué. Aquí se avisa de a dónde miras y se pinta
//     lo que llega; una seña que no te corresponde no llega nunca al cliente.
//   · El foco se aplica de forma optimista (para que responda al instante) y el
//     servidor confirma o rechaza; si rechaza, se vuelve donde se estaba.
//
// window.Senas4 lo usan app4.js (sincronizar/salir) y table4.js (misCartasVisibles).

(function () {
    'use strict';

    // ==========================================
    // 1. i18n
    // ==========================================
    Object.assign(dict.es, {
        senas_boton: 'Seña',
        senas_hecha: 'Has hecho: {sena}',
        senas_denuncia_titulo: '¿Qué le has visto a <b>{nombre}</b>?',
        senas_denuncia_cerrar: 'Cancelar',
        senas_visto: '¡Te he visto <b>{sena}</b>!',
        senas_ayuda: 'Flechas, WASD o desliza para mirar · toca a un rival si le pillas una seña',
        sena_solomillo: 'Solomillo',
        sena_duples: 'Duples',
        sena_31: '31',
        sena_tres_reyes: 'Tres reyes',
        sena_tres_ases: 'Tres ases',
        sena_medias: 'Medias',
        sena_dos_reyes: 'Dos reyes',
        sena_dos_ases: 'Dos ases',
        sena_30: '30',
        sena_ciego: 'Ciego',
        play_senas_on: 'con señas',
    });
    Object.assign(dict.en, {
        senas_boton: 'Sign',
        senas_hecha: 'You signed: {sena}',
        senas_denuncia_titulo: 'What did you catch <b>{nombre}</b> signing?',
        senas_denuncia_cerrar: 'Cancel',
        senas_visto: 'I saw you sign <b>{sena}</b>!',
        senas_ayuda: 'Arrows, WASD or swipe to look · tap a rival if you catch a sign',
        sena_solomillo: 'Solomillo',
        sena_duples: 'Two pairs',
        sena_31: '31',
        sena_tres_reyes: 'Three kings',
        sena_tres_ases: 'Three aces',
        sena_medias: 'Three of a kind',
        sena_dos_reyes: 'Two kings',
        sena_dos_ases: 'Two aces',
        sena_30: '30',
        sena_ciego: 'Blind',
        play_senas_on: 'with signs',
    });
    aplicarTraduccion();

    // Orden de la CHULETA (el de la ventana de denunciar). El orden de prioridad
    // con el que se elige la seña al señalar lo decide el servidor y es otro:
    // es editable desde /admin y aquí no hace falta conocerlo.
    const SENAS = ['solomillo', 'duples', '31', 'tres_reyes', 'tres_ases',
                   'medias', 'dos_reyes', 'dos_ases', '30', 'ciego'];

    const nombreSena = (s) => t('sena_' + s);

    // ==========================================
    // 2. Estado
    // ==========================================
    let activo = false;
    let miAsiento = null;
    let fase = null;
    let region = 'frente';          // dónde miro ahora
    let regionDesde = 0;
    let regionPrevia = null;        // a quién sigo viendo durante el solape
    let previaHasta = 0;
    let manualHasta = 0;            // hasta cuándo respeto mi elección a mano
    let cambioHasta = 0;            // vagabundeo: cuándo toca cambiar solo
    let clavadoAbajo = false;       // descarte: el foco no se mueve de mis cartas
    let miradas = {};               // asiento -> a quién mira (o 'abajo')
    let ultimaSenaLocal = 0;
    let bucle = null;
    let gestoHasta = 0;             // ignora el "click" que deja un deslizamiento
    let intencion = null;           // foco pedido a mano que aún no se ha podido aplicar
    let ayudaVista = false;
    let nombres = {};               // asiento -> nombre visible

    let ajustes = {
        foco_cooldown_ms: 1000,
        foco_solape_ms: 1000,
        foco_manual_ms: 2500,
        sena_cooldown_ms: 3000,
    };

    const SALTOS = { frente: 2, izquierda: 1, derecha: 3 };
    const SLOTS = { frente: 'top', izquierda: 'left', derecha: 'right', abajo: 'bottom' };
    const VAGABUNDEO = ['frente', 'izquierda', 'derecha'];

    const ahora = () => Date.now();
    const asientoDeRegion = (r) => (r === 'abajo' || miAsiento === null) ? 'abajo' : (miAsiento + SALTOS[r]) % 4;

    // ==========================================
    // 3. La cara (SVG)
    // ==========================================
    function svgCara() {
        // Un solo trozo de SVG para todo: caras de la mesa y muestras de la
        // chuleta. Las clases son las que mueve senas.css.
        return `
<svg class="cara" viewBox="0 0 64 74" aria-hidden="true">
  <g class="cara-hombros"><path d="M7 73 C13 62 23 56.5 32 56.5 C41 56.5 51 62 57 73"/></g>
  <g class="cara-cabeza">
    <circle class="cara-piel" cx="32" cy="30" r="21"/>
    <path class="ceja ceja-i" d="M17 19.5 q6 -3.2 12 0"/>
    <path class="ceja ceja-d" d="M35 19.5 q6 -3.2 12 0"/>
    <g class="ojo ojo-i">
      <circle class="ojo-bola" cx="23" cy="28" r="4.8"/>
      <circle class="pupila" cx="23" cy="28" r="2.2"/>
      <path class="parpado" d="M18.2 28 q4.8 3.6 9.6 0"/>
    </g>
    <g class="ojo ojo-d">
      <circle class="ojo-bola" cx="41" cy="28" r="4.8"/>
      <circle class="pupila" cx="41" cy="28" r="2.2"/>
      <path class="parpado" d="M36.2 28 q4.8 3.6 9.6 0"/>
    </g>
    <path class="boca boca-normal" d="M25 41 q7 5 14 0"/>
    <path class="boca boca-linea" d="M25 42 h14"/>
    <ellipse class="boca boca-beso" cx="32" cy="42.5" rx="3.2" ry="4"/>
    <path class="lengua" d="M28.5 42 q3.5 7.5 7 0 z"/>
  </g>
</svg>`;
    }

    /** Coordenadas en pantalla (0-1) de cada asiento visto desde el mío: sirven
     *  para saber si alguien mira a su izquierda o a su derecha. */
    function puntoDeAsiento(asiento) {
        if (asiento === 'abajo' || asiento === null || asiento === undefined) return null;
        const rel = ((asiento - miAsiento) + 4) % 4;
        return [{ x: 0.5, y: 1 }, { x: 0, y: 0.5 }, { x: 0.5, y: 0 }, { x: 1, y: 0.5 }][rel];
    }

    /** Orienta la cara de `asiento` hacia donde esté mirando, en MI marco. */
    function pintarMirada(svg, asiento) {
        if (!svg) return;
        const mira = miradas[asiento];
        const meMira = (mira === miAsiento && mira !== undefined && mira !== null);
        svg.classList.toggle('te-mira', !!meMira);

        let gx = 0, gy = 0, tilt = 0;
        if (meMira) {
            gx = 0; gy = 0;                       // clavado en ti
        } else if (mira === 'abajo') {
            gy = 2.2;                             // mirándose las cartas
        } else if (mira !== undefined && mira !== null) {
            const yo = puntoDeAsiento(asiento);
            const el = puntoDeAsiento(mira);
            if (yo && el) {
                const dx = Math.max(-1, Math.min(1, el.x - yo.x));
                const dy = Math.max(-1, Math.min(1, el.y - yo.y));
                gx = dx * 2.3;
                gy = dy * 1.6;
                tilt = dx * 5;
            }
        }
        svg.style.setProperty('--gx', gx.toFixed(2) + 'px');
        svg.style.setProperty('--gy', gy.toFixed(2) + 'px');
        svg.style.setProperty('--tilt', tilt.toFixed(1) + 'deg');
    }

    /** Lanza la animación de una seña en la cara de un asiento. */
    function animarSena(asiento, sena) {
        const el = elementoAsiento(asiento);
        const svg = el && el.querySelector('.cara');
        if (!svg) return;
        SENAS.forEach(s => svg.classList.remove('sena-' + s));
        void svg.offsetWidth;                     // reinicia la animación
        svg.classList.add('sena-' + sena);
        setTimeout(() => svg.classList.remove('sena-' + sena), 1400);
    }

    // ==========================================
    // 4. Montaje sobre la mesa
    // ==========================================
    function elementoAsiento(asiento) {
        if (asiento === null || asiento === undefined || miAsiento === null) return null;
        const rel = ((asiento - miAsiento) + 4) % 4;
        return document.getElementById('seat-' + ['bottom', 'left', 'top', 'right'][rel]);
    }

    function montar() {
        // Una cara en cada asiento que no sea el mío (a uno mismo no se le mira).
        ['top', 'left', 'right'].forEach(slot => {
            const el = document.getElementById('seat-' + slot);
            if (!el || el.querySelector('.seat-cara')) return;
            const cont = document.createElement('div');
            cont.className = 'seat-cara';
            cont.innerHTML = svgCara();
            el.appendChild(cont);
        });

        if (!document.getElementById('btn-sena-4')) {
            const btn = document.createElement('button');
            btn.id = 'btn-sena-4';
            // Con data-i18n el cambio de idioma lo aplica aplicarTraduccion(),
            // igual que en el resto de la mesa, sin esperar al siguiente estado.
            btn.innerHTML = `<span class="sena-icono">☞</span><span class="sena-txt" data-i18n="senas_boton">${t('senas_boton')}</span>`;
            btn.addEventListener('click', hacerSena);
            document.getElementById('game-screen-4').appendChild(btn);

            const aviso = document.createElement('div');
            aviso.id = 'sena-hecha-4';
            document.getElementById('game-screen-4').appendChild(aviso);

            const ayuda = document.createElement('div');
            ayuda.id = 'senas-ayuda';
            ayuda.setAttribute('data-i18n', 'senas_ayuda');
            ayuda.innerText = t('senas_ayuda');
            document.getElementById('game-screen-4').appendChild(ayuda);
        }
        montarDenuncia();
    }

    // ==========================================
    // 5. Foco
    // ==========================================
    function pedirFoco(nuevaRegion, manual) {
        if (!activo || clavadoAbajo) return;
        const t0 = ahora();
        if (nuevaRegion === region) {
            if (manual) { manualHasta = t0 + ajustes.foco_manual_ms; intencion = null; }
            return;
        }
        if (t0 - regionDesde < ajustes.foco_cooldown_ms) {
            // Aún no toca. Si lo has pedido tú, se guarda y se reintenta en
            // cuanto venza el cooldown: si no, pulsar justo después de que el
            // vagabundeo mueva la vista parecería que el mando no responde.
            if (manual) { intencion = nuevaRegion; manualHasta = t0 + ajustes.foco_manual_ms; }
            return;
        }

        intencion = null;
        aplicarFoco(nuevaRegion, t0);
        if (manual) manualHasta = t0 + ajustes.foco_manual_ms;
        socket.emit('foco_4', { region: nuevaRegion });
    }

    function aplicarFoco(nuevaRegion, t0) {
        regionPrevia = region;
        previaHasta = (t0 || ahora()) + ajustes.foco_solape_ms;
        region = nuevaRegion;
        regionDesde = t0 || ahora();
        // El vagabundeo vuelve a mirar a otro sitio pasado un rato al azar.
        cambioHasta = regionDesde + 1000 + Math.random() * 1500;
        pintar();
    }

    /** Durante el descarte el foco se clava en las cartas: hay que verlas para
     *  elegir, y así nadie señala mientras los demás están a otra cosa. */
    function clavarAbajo(valor) {
        clavadoAbajo = valor;
        if (valor && region !== 'abajo') {
            aplicarFoco('abajo', ahora());
            socket.emit('foco_4', { region: 'abajo' });
        }
    }

    function vagabundear() {
        if (!activo || clavadoAbajo) return;
        const t0 = ahora();
        // Lo que pediste tú manda sobre el vagabundeo: se sirve en cuanto se puede.
        if (intencion) {
            if (t0 - regionDesde >= ajustes.foco_cooldown_ms) {
                const r = intencion;
                intencion = null;
                pedirFoco(r, true);
            }
            return;
        }
        if (t0 < manualHasta || t0 < cambioHasta) return;
        if (t0 - regionDesde < ajustes.foco_cooldown_ms) return;
        // Sólo se pasea por lo que hay delante y a los lados: mirarse las cartas
        // es siempre una decisión tuya.
        const opciones = VAGABUNDEO.filter(r => r !== region);
        pedirFoco(opciones[Math.floor(Math.random() * opciones.length)], false);
    }

    // ==========================================
    // 6. Pintado
    // ==========================================
    function pintar() {
        if (!activo || miAsiento === null) return;
        const t0 = ahora();
        const enSolape = regionPrevia && t0 < previaHasta && regionPrevia !== region;
        const slotActivo = SLOTS[region];
        const slotSaliente = enSolape ? SLOTS[regionPrevia] : null;

        ['top', 'left', 'right', 'bottom'].forEach(slot => {
            const el = document.getElementById('seat-' + slot);
            if (!el) return;
            const esActivo = (slot === slotActivo);
            const esSaliente = (slot === slotSaliente);
            el.classList.toggle('enfocado', esActivo && slot !== 'bottom');
            el.classList.toggle('enfocado-saliente', esSaliente && slot !== 'bottom');
            el.classList.toggle('desenfocado', !esActivo && !esSaliente);
        });

        // Mis cartas: sólo mientras las miro (y el segundo de solape).
        const veoMisCartas = (region === 'abajo') || (enSolape && regionPrevia === 'abajo');
        const abajo = document.getElementById('seat-bottom');
        if (abajo) abajo.classList.toggle('mano-oculta', !veoMisCartas);

        // Orientación de las caras visibles.
        [region, enSolape ? regionPrevia : null].forEach(r => {
            if (!r || r === 'abajo') return;
            const asiento = asientoDeRegion(r);
            const el = elementoAsiento(asiento);
            const svg = el && el.querySelector('.cara');
            if (svg) pintarMirada(svg, asiento);
        });

        pintarBotonSena();
    }

    function pintarBotonSena() {
        const btn = document.getElementById('btn-sena-4');
        if (!btn) return;
        const puede = activo && (fase === 'mus' || fase === 'apuestas');
        btn.classList.toggle('visible', puede);
        btn.disabled = !puede || (ahora() - ultimaSenaLocal < ajustes.sena_cooldown_ms);
    }

    // ==========================================
    // 7. Hacer una seña
    // ==========================================
    function hacerSena() {
        if (!activo) return;
        const t0 = ahora();
        if (t0 - ultimaSenaLocal < ajustes.sena_cooldown_ms) return;
        // No se elige la seña: el servidor mira tus cartas y hace la más alta.
        socket.emit('sena_4');
    }

    function marcarSenaHecha(sena) {
        ultimaSenaLocal = ahora();
        const btn = document.getElementById('btn-sena-4');
        if (btn) {
            btn.style.setProperty('--cd', (ajustes.sena_cooldown_ms / 1000) + 's');
            btn.classList.remove('enfriando');
            void btn.offsetWidth;
            btn.classList.add('enfriando');
            btn.disabled = true;
            setTimeout(() => { btn.classList.remove('enfriando'); pintarBotonSena(); },
                       ajustes.sena_cooldown_ms);
        }
        const aviso = document.getElementById('sena-hecha-4');
        if (aviso) {
            aviso.innerText = t_dinamico('senas_hecha', { sena: nombreSena(sena) });
            aviso.classList.add('visible');
            setTimeout(() => aviso.classList.remove('visible'), 2200);
        }
    }

    // ==========================================
    // 8. Denunciar una seña ("te he visto")
    // ==========================================
    let acusado = null;

    function montarDenuncia() {
        if (document.getElementById('senas-denuncia')) return;

        const velo = document.createElement('div');
        velo.id = 'senas-velo';
        velo.addEventListener('click', cerrarDenuncia);
        document.body.appendChild(velo);

        const panel = document.createElement('div');
        panel.id = 'senas-denuncia';
        panel.innerHTML = `<p class="den-titulo"></p><div class="den-lista"></div>
            <button class="den-cerrar">${t('senas_denuncia_cerrar')}</button>`;
        document.body.appendChild(panel);
        panel.querySelector('.den-cerrar').addEventListener('click', cerrarDenuncia);

        // La chuleta: cada opción enseña la seña haciéndose en bucle.
        const lista = panel.querySelector('.den-lista');
        SENAS.forEach(sena => {
            const op = document.createElement('button');
            op.className = 'den-op';
            op.dataset.sena = sena;
            op.innerHTML = `<span class="seat-cara">${svgCara()}</span><span class="den-nombre">${nombreSena(sena)}</span>`;
            const svg = op.querySelector('.cara');
            svg.classList.add('sena-' + sena, 'en-bucle');
            op.addEventListener('click', () => {
                if (acusado !== null) socket.emit('denuncia_sena_4', { asiento: acusado, sena });
                cerrarDenuncia();
            });
            lista.appendChild(op);
        });
    }

    /** Repasa los textos que se montan una sola vez y no llevan data-i18n: la
     *  lista de señas de la chuleta, que se construye desde JS. */
    function refrescarTextos() {
        const panel = document.getElementById('senas-denuncia');
        if (!panel) return;
        panel.querySelectorAll('.den-op').forEach(op => {
            const n = op.querySelector('.den-nombre');
            if (n) n.innerText = nombreSena(op.dataset.sena);
        });
        const cerrar = panel.querySelector('.den-cerrar');
        if (cerrar) cerrar.innerText = t('senas_denuncia_cerrar');
    }

    function abrirDenuncia(asiento) {
        montarDenuncia();
        refrescarTextos();
        acusado = asiento;
        const panel = document.getElementById('senas-denuncia');
        panel.querySelector('.den-titulo').innerHTML =
            t_dinamico('senas_denuncia_titulo', { nombre: escHtml(nombres[asiento] || '') });
        panel.classList.add('abierta');
        document.getElementById('senas-velo').classList.add('abierto');
    }

    function cerrarDenuncia() {
        acusado = null;
        const panel = document.getElementById('senas-denuncia');
        if (panel) panel.classList.remove('abierta');
        const velo = document.getElementById('senas-velo');
        if (velo) velo.classList.remove('abierto');
    }

    function mostrarDenuncia(d) {
        const el = elementoAsiento(d.de);
        if (el) {
            const burbuja = document.createElement('div');
            burbuja.className = 'sena-burbuja';
            burbuja.innerHTML = t_dinamico('senas_visto', { sena: nombreSena(d.sena) });
            el.appendChild(burbuja);
            setTimeout(() => burbuja.remove(), 3400);
        }
        const acu = elementoAsiento(d.a);
        if (acu) {
            acu.classList.remove('acusado');
            void acu.offsetWidth;
            acu.classList.add('acusado');
            setTimeout(() => acu.classList.remove('acusado'), 3400);
        }
    }

    // ==========================================
    // 9. Controles (teclado, deslizamiento y toque)
    // ==========================================
    const TECLAS = {
        ArrowUp: 'frente', KeyW: 'frente',
        ArrowLeft: 'izquierda', KeyA: 'izquierda',
        ArrowRight: 'derecha', KeyD: 'derecha',
        ArrowDown: 'abajo', KeyS: 'abajo',
    };

    document.addEventListener('keydown', (e) => {
        if (!activo) return;
        const etiqueta = (e.target && e.target.tagName) || '';
        if (/^(INPUT|TEXTAREA|SELECT)$/.test(etiqueta)) return;   // escribiendo
        const r = TECLAS[e.code];
        if (!r) return;
        e.preventDefault();
        pedirFoco(r, true);
    });

    let toque = null;
    function montarGestos() {
        const mesa = document.getElementById('mesa-4');
        if (!mesa || mesa.dataset.senasGestos) return;
        mesa.dataset.senasGestos = '1';

        mesa.addEventListener('touchstart', (e) => {
            if (e.touches.length !== 1) { toque = null; return; }
            toque = { x: e.touches[0].clientX, y: e.touches[0].clientY, t: ahora() };
        }, { passive: true });

        mesa.addEventListener('touchend', (e) => {
            if (!toque || !activo) { toque = null; return; }
            const fin = e.changedTouches && e.changedTouches[0];
            if (!fin) { toque = null; return; }
            const dx = fin.clientX - toque.x;
            const dy = fin.clientY - toque.y;
            const dist = Math.hypot(dx, dy);
            const dur = ahora() - toque.t;
            toque = null;
            // Por debajo de 40 px es un toque (seleccionar carta, denunciar);
            // por encima de 700 ms ya no es un gesto, es arrastrar sin querer.
            if (dist < 40 || dur > 700) return;
            gestoHasta = ahora() + 400;           // que el "click" no cuente
            const r = Math.abs(dx) > Math.abs(dy)
                ? (dx > 0 ? 'derecha' : 'izquierda')
                : (dy > 0 ? 'abajo' : 'frente');
            pedirFoco(r, true);
        }, { passive: true });

        // Tocar a un RIVAL abre la ventana de denuncia (a la pareja no: no vas a
        // denunciar a quien le haces las señas).
        mesa.addEventListener('click', (e) => {
            if (!activo || ahora() < gestoHasta) return;
            const asientoEl = e.target.closest && e.target.closest('.seat-4');
            if (!asientoEl) return;
            const slot = asientoEl.dataset.slot;
            if (slot !== 'left' && slot !== 'right') return;   // los rivales
            const asiento = asientoDeRegion(slot === 'left' ? 'izquierda' : 'derecha');
            abrirDenuncia(asiento);
        });
    }

    // ==========================================
    // 10. Eventos del servidor
    // ==========================================
    socket.on('foco_4', (d) => {
        if (!d) return;
        if (d.rechazado) {
            // El servidor no aceptó el cambio: se vuelve a donde estábamos y,
            // si el cambio lo habías pedido tú, se reintenta al vencer el corte.
            if (region !== d.region) intencion = region;
            region = d.region;
            regionDesde = ahora();
            regionPrevia = null;
            pintar();
            return;
        }
        if (d.miradas) {
            Object.keys(d.miradas).forEach(k => { miradas[+k] = d.miradas[k]; });
        }
        pintar();
    });

    socket.on('mirada_4', (d) => {
        if (!d) return;
        miradas[d.asiento] = d.mira;
        pintar();
    });

    socket.on('sena_vista_4', (d) => {
        if (!d || !activo) return;
        animarSena(d.asiento, d.sena);
    });

    socket.on('sena_hecha_4', (d) => {
        if (d && d.sena) marcarSenaHecha(d.sena);
    });

    socket.on('denuncia_4', (d) => {
        if (d && activo) mostrarDenuncia(d);
    });

    // ==========================================
    // 11. Ciclo de vida (lo llama app4.js)
    // ==========================================
    function sincronizar(d) {
        if (!d || !d.senas) {
            if (activo) salir();
            return;
        }
        const primeraVez = !activo;
        activo = true;
        miAsiento = d.mi_asiento;
        fase = d.fase;
        if (d.senas_ajustes) ajustes = Object.assign({}, ajustes, d.senas_ajustes);
        (d.seats || []).forEach(s => { nombres[s.asiento] = s.nombre; });

        document.getElementById('game-screen-4').classList.add('con-senas');
        montar();
        montarGestos();
        refrescarTextos();

        // El descarte clava el foco en tus cartas y lo suelta al confirmar.
        clavarAbajo(d.fase === 'descarte' && !d.mis_descartes_listos);

        if (primeraVez) {
            regionDesde = ahora();
            cambioHasta = regionDesde + 1200;
            if (!bucle) bucle = setInterval(tic, 250);
            if (!ayudaVista) {
                ayudaVista = true;
                const ayuda = document.getElementById('senas-ayuda');
                if (ayuda) {
                    ayuda.classList.add('visible');
                    setTimeout(() => ayuda.classList.remove('visible'), 6500);
                }
            }
        }
        pintar();
    }

    function tic() {
        if (!activo) return;
        vagabundear();
        pintar();          // caduca el solape y refresca el botón
    }

    function salir() {
        activo = false;
        clavadoAbajo = false;
        miradas = {};
        if (bucle) { clearInterval(bucle); bucle = null; }
        cerrarDenuncia();
        const pantalla = document.getElementById('game-screen-4');
        if (pantalla) pantalla.classList.remove('con-senas');
        ['top', 'left', 'right', 'bottom'].forEach(slot => {
            const el = document.getElementById('seat-' + slot);
            if (el) el.classList.remove('enfocado', 'enfocado-saliente', 'desenfocado');
        });
        const abajo = document.getElementById('seat-bottom');
        if (abajo) abajo.classList.remove('mano-oculta');
        const btn = document.getElementById('btn-sena-4');
        if (btn) btn.classList.remove('visible');
    }

    window.Senas4 = {
        sincronizar,
        salir,
        /** table4.js pregunta esto para saber si pinta el dorso de mis cartas. */
        activas: () => activo,
    };
})();
