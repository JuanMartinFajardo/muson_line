// ==========================================================================
// CallMus · medición de audiencia (Roadmap #24)
// --------------------------------------------------------------------------
// NO guarda NADA en el dispositivo: ni cookie propia, ni localStorage, ni
// sessionStorage, ni huella. Lo único que hace es mandar al PROPIO servidor
// cuánto tiempo ha estado la pestaña visible y qué botones de menú se han
// pulsado. Por eso el sitio no necesita banner de cookies (ver la cabecera de
// analitica.py y el punto de la política de privacidad en app.js).
//
// El tiempo se cuenta SOLO con la pestaña visible: una pestaña abierta y
// olvidada durante dos horas no cuenta como dos horas de uso.
// ==========================================================================
(function () {
  'use strict';

  var LATIDO_MS = 30000;       // cada cuánto se manda lo acumulado
  var url = function (r) { return '/api/a/' + r; };

  var acumulado = 0;           // segundos visibles aún sin mandar
  var ultimo = Date.now();
  var visible = !document.hidden;

  function acumular() {
    var ahora = Date.now();
    if (visible) acumulado += (ahora - ultimo) / 1000;
    ultimo = ahora;
  }

  function enviar(final) {
    acumular();
    var seg = Math.round(acumulado);
    if (seg <= 0 && !final) return;
    acumulado -= seg;
    var cuerpo = JSON.stringify({ activo: seg });
    // Al cerrar la pestaña, fetch() no llega: sendBeacon sí.
    if (final && navigator.sendBeacon) {
      try {
        navigator.sendBeacon(url('latido'), new Blob([cuerpo], { type: 'application/json' }));
        return;
      } catch (e) { /* seguimos con fetch */ }
    }
    fetch(url('latido'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      keepalive: true,
      body: cuerpo
    }).catch(function () { /* la analítica jamás molesta al jugador */ });
  }

  document.addEventListener('visibilitychange', function () {
    acumular();
    visible = !document.hidden;
    ultimo = Date.now();
    if (document.hidden) enviar(false);
  });

  window.addEventListener('pagehide', function () { enviar(true); });
  setInterval(function () { enviar(false); }, LATIDO_MS);

  // ------------------------------------------------------------------
  // Eventos de interfaz. Se instrumenta por delegación sobre los ids que
  // ya existen en index.html: así app.js no se toca y añadir o quitar un
  // botón nunca puede romper el juego por culpa de la analítica.
  // El servidor solo acepta los tipos de esta lista.
  // ------------------------------------------------------------------
  var BOTONES = {
    'btn-play': 'menu_jugar',
    'btn-show-leaderboard': 'menu_ranking',
    'btn-settings': 'menu_ajustes',
    'btn-tutorial': 'menu_tutorial',
    'btn-help-game': 'menu_tutorial',
    'btn-help-game-4': 'menu_tutorial',
    'btn-decks': 'menu_barajas',
    'btn-show-signup': 'registro_abierto',
    'btn-show-login': 'login_abierto',
    'btn-amigos': 'amigos_abierto',
    // Ko-fi es un <a target="_blank">: la pestaña actual no se descarga, así
    // que el fetch normal llega de sobra. La etiqueta («tras jugar» / «sin
    // jugar») la decide el servidor, aquí no se manda nada más.
    'btn-kofi': 'kofi'
  };

  function evento(tipo, etiqueta) {
    try {
      fetch(url('evento'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ tipo: tipo, etiqueta: etiqueta || null })
      }).catch(function () {});
    } catch (e) { /* ignorado a propósito */ }
  }

  document.addEventListener('click', function (ev) {
    var el = ev.target && ev.target.closest ? ev.target.closest('button,a') : null;
    if (!el || !el.id) return;
    var tipo = BOTONES[el.id];
    if (tipo) evento(tipo);
  }, true);

  // Cambio de idioma: lo emite settings.js/app.js sobre <html lang>.
  var idiomaPrevio = document.documentElement.lang;
  new MutationObserver(function () {
    var l = document.documentElement.lang;
    if (l && l !== idiomaPrevio) { idiomaPrevio = l; evento('idioma', l); }
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });

  // Único punto de entrada público, por si algún día conviene marcar algo a mano.
  window.Analitica = { evento: evento };
})();
