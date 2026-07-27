# CallMus — Registro de cambios (log)

Historial cronológico de cambios relevantes del proyecto. El más reciente arriba.

---

## 2026-07-27 — Se acabó la baraja: ahora se avisa (Roadmap #14)

Cuando muchas rondas de mus seguidas agotaban el mazo, el motor rebarajaba los
descartes **sin decir nada**: las cartas seguían saliendo y más de uno pensaba que
algo se había roto. Ahora sale un aviso breve, y el turno sigue como si nada.

- **Motor (`mus_mecanicas.py`).** `robar()` marca `baraja_agotada_aviso = True` en la
  rama del rebarajado; `iniciar_ronda()` lo apaga. Es una bandera **de la mesa**, no
  de cada jugador, así que el aviso llega a los dos aunque el rebarajado ocurra en
  mitad de los descartes. Viaja en `_CAMPOS_ESCALARES`, de modo que `fork()`,
  `to_state()` y `from_state()` la conservan (partidas guardadas y reconexiones).
- **Servidor (`server.py`).** `enviar_estado_a_jugadores` lee la bandera **una vez**
  antes del bucle de jugadores, la manda como `aviso_baraja` en el estado de todos y
  la apaga al terminar la difusión: un aviso por rebarajado, ni uno más.
- **Cliente (`static/app.js`).** `msg_baraja_agotada` en los tres diccionarios
  (ES/EN/EU) y aviso flotante con el mismo `mostrarToastPartida` de siempre, que se
  va solo. **No** se ha usado el canal de `mensaje_transicion`: ese exige pulsar para
  continuar y este aviso no debe cortar la partida.
- **El 2v2 ya lo tenía** (`mus_mecanicas_4.py`, `server_mus4.py`, `static/app4.js`)
  con este mismo diseño; se ha comprobado que funciona y el 1v1 se ha escrito igual.
- **Comprobado** levantando el servidor con una baraja recortada: en la mesa contra
  la IA (1v1) y en una mesa de cuatro personas (2v2) el aviso salta justo al
  rebarajar, una sola vez, a todos los de la mesa, y la mano continúa sin tocar nada.

---

## 2026-07-27 — El móvil: deslizar sin que se mueva la página, y la pantalla completa del iPhone

Las señas se juegan deslizando el dedo, pero el navegador entendía ese mismo gesto
como suyo: movía la página, rebotaba o la recargaba de un tirón hacia abajo. Sólo a
pantalla completa se jugaba bien… y en el iPhone la pantalla completa no llegaba a
funcionar, porque **Safari no tiene la API de pantalla completa para webs**. Se
arreglan las dos cosas, y la de fondo primero: que no haga falta.

- **Modo mesa (`static/pantalla.js`, nuevo).** Mientras se ve una mesa, el
  documento se congela: `<html>` lleva `.modo-mesa` y el body pasa a `position:
  fixed` (lo único que Safari respeta de verdad), sin desbordamiento, sin rebote y
  sin el doble toque para acercar. Un `touchmove` **no pasivo** cancela cualquier
  arrastre que no caiga dentro de algo que de verdad se pueda desplazar — el
  recuento largo del 1v1, la chuleta de señas o el tutorial siguen bajando; la
  mesa, no. **Se juega igual de bien con y sin pantalla completa.**
- **Las señas ya no dependen del navegador.** `senas4.js` escucha los gestos en la
  pantalla de 2v2 entera (antes sólo en la retícula) y llama a `preventDefault()`
  en cuanto el dedo se mueve 8 px; `senas.css` le pone `touch-action: none` a la
  mesa. El toque de denuncia se atiende ahora en `touchend` además de en `click`,
  porque al cancelar el desplazamiento hay navegadores que ya no mandan el `click`.
- **Pantalla completa, en un solo sitio.** El bloque suelto de `app.js` se va a
  `pantalla.js`, ahora con los prefijos de cada navegador, el botón ⛶ repintándose
  al entrar y salir, y escondiéndose solo si la web ya se abrió desde la pantalla
  de inicio.
- **Entrada automática al empezar la partida**, en el clic de *crear* / *unirse* /
  *jugar contra la IA* (la API exige un gesto, y la mesa se abre mucho después,
  cuando lo dice el servidor). No entra si falta el nombre o el código, que sólo
  daría un aviso. Se sale siempre a mano con el ⛶. Interruptor del administrador:
  **`pantalla_completa_auto`** (por defecto 1).
- **iPhone.** Donde no hay API, el ⛶ abre una ventanita que explica *Compartir →
  Añadir a pantalla de inicio*, que es la única pantalla completa de verdad que da
  Safari, y aclara que la mesa ya funciona sin ella. Se añaden las etiquetas
  `apple-mobile-web-app-*` y `viewport-fit=cover`, y se rellena el
  `site.webmanifest`, que estaba **sin nombre y con las rutas de los iconos rotas**
  (apuntaban a la raíz, no a `static/favicon_io/`).
- De propina: la mesa de 2v2 se mide en `dvh` en vez de `vh` (la fila de abajo se
  iba por debajo de la barra del navegador) y los tapetes y los botones de las
  esquinas esquivan la muesca y la barra de gestos con `env(safe-area-inset-*)`.

---

## 2026-07-27 — El tutorial, en tres pistas (1v1, 2v2 y señas)

El tutorial era un carrusel único que solo contaba el mus a dos, y ni el juego por
parejas ni las señas se explicaban en ninguna parte.

- **Un índice y tres caminos.** *Cómo se juega* abre ahora en un índice con tres
  botones: **1 contra 1** (las 13 diapositivas de siempre, intactas), **2 contra 2**
  (9 nuevas) y **Las señas** (8 nuevas). Cada pista es su propio array por idioma
  (`dictTut1v1` / `dictTut2v2` / `dictTutSenas`), así que los índices internos —el
  salto de la diapositiva de práctica, por ejemplo— siguen valiendo. Se vuelve al
  índice con el ☰ de la esquina o con *Anterior* en la primera diapositiva, y hay
  botones que enlazan una pista con otra (del 2v2 al repaso del 1v1 y a las señas).
- **La pista del 2v2 cuenta solo lo que cambia:** los equipos y el asiento de
  enfrente, que el mus solo sigue si lo quieren los cuatro, que Pares y Juego se
  declaran en voz alta, que responde la pareja entera (tu «no quiero» no cierra el
  lance hasta que tu compañero también dice que no) y que en el recuento los
  premios de las dos manos del equipo **se suman**. Con dos ejemplos con cartas.
- **La pista de las señas enseña los diez gestos animándose en bucle**, con la
  misma cara de la mesa: `senas4.js` exporta ahora `Senas4.svgCara()` y el tutorial
  la reutiliza con las clases de siempre, de modo que un gesto nuevo se anima solo
  en los tres sitios (mesa, chuleta de denuncia y tutorial). Además: la regla de
  que sale la seña **más alta** y no se elige, cuándo está vivo el botón, la
  denuncia y cuatro trucos.
- **Un `?` junto a *Con señas*, al crear la partida de cuatro.** Abre una ventanita
  flotante que explica la **mecánica** —las cuatro regiones de foco con sus teclas,
  flechas/WASD/deslizar, la cara que se enciende en oro, el vagabundeo y sus 2,5 s,
  el corte de 1 s y el solape de 1 s, y cuándo se puede señalar— y lleva al
  tutorial para ver los gestos. El interruptor pasa a vivir en una `.cm-switch-fila`
  para que el botón no cuente como parte de la etiqueta.
- De propina, el contenido del tutorial deja de recortarse **por arriba** cuando no
  cabe (`justify-content: safe center`), y en móvil los puntitos y los botones de
  la barra de abajo caben enteros.

---

## 2026-07-27 — 2v2: pares y juego son de cada uno, y quién canta qué se lee

Dos arreglos de la mesa de cuatro.

- **No se apuesta a Pares/Juego sin la jugada, aunque la tenga tu compañero.** El
  motor ya lo sabía (`PartidaMus4.acciones_legales` lo aplica desde la Fase 0 y es
  lo que consumen los bots), pero por el camino de las personas nadie lo miraba:
  `procesar_accion_4` solo comprobaba el turno y la fase, y el cliente pintaba el
  panel de apuestas entero a quien tuviera la palabra. Resultado: sin pares podías
  envidar —o echar un órdago— a unos pares que no llevabas. Ahora
  `procesar_accion_4` rechaza toda apuesta que no esté en `acciones_legales(seat)`
  (misma lista, mismo juez para bots y personas) y el payload de
  `actualizar_mesa_4` la incluye, así que `mostrarPanelApuesta4` enciende solo los
  botones que el servidor va a aceptar: sin la jugada queda **Paso** (o **No
  quiero** si te han envidado) y un aviso en el centro de la mesa explicando que
  en ese lance apuesta tu compañero (ES/EN). De paso, el envite deja de ofrecerse
  cuando ya no cabe antes de 40, que también salía de la lista.
- **El rótulo de lo que canta cada jugador, junto a su nombre.** `.accion-burbuja`
  se anclaba al borde superior del *asiento*, y los asientos de los lados ocupan
  toda la altura de la mesa: la plaquita salía a media pantalla de distancia del
  jugador y no se sabía de quién era. Nombre, chips y cartas van ahora dentro de
  un `.seat-cuerpo`, que mide lo que ocupa el jugador y es el ancla del rótulo.
  Además sube lo justo para **no tapar el nombre** (antes se le montaba encima, y
  la plaquita es opaca), el asiento de arriba gana el hueco que necesita para no
  pisar el marcador, y el anclaje al borde de fuera de las columnas laterales pasa
  a ser cosa **solo del móvil** (≤640 px), que es donde una columna de 60 px lo
  pedía; en pantalla ancha va centrado sobre el jugador.

---

## 2026-07-27 — El botón de Ko-fi, medido (Roadmap #24)

La analítica ya cuenta el interés por el enlace de apoyo. Detalles en
[Analytics](wiki/Analytics.md#the-ko-fi-button).

- **Qué se mide.** Dos cosas distintas a propósito: *visitas que pulsan* (de ahí sale
  el CTR) y *clics totales*, porque una misma visita puede pulsar dos veces. Ambas se
  agregan por día, por valor de cada dimensión y por cuenta, así que el desglose
  responde a «qué origen de tráfico apoya de verdad el proyecto» y la tabla por
  usuario enseña quién lo hizo.
- **Antes o después de jugar.** La etiqueta del evento la pone **el servidor**,
  ignorando lo que mande el cliente: `tras jugar` si la visita ya había empezado una
  partida, `sin jugar` si no. Es el nuevo desglose «Ko-fi», y es el número que dice si
  la gente apoya el juego después de disfrutarlo o de pasada.
- **Lo que no se puede saber, y se dice.** Si el clic acabó en donación, y de cuánto.
  Eso pasa en ko-fi.com, un tercero con el que este servidor no habla. Añadido al
  punto de *Medición de audiencia* de la política de privacidad (ES y EN) y a la caja
  de privacidad del panel.
- **Sin tocar nada del juego.** `#btn-kofi` es un `<a>` normal a un sitio externo: lo
  recoge el mismo listener delegado que los demás botones de menú. Cero widgets, cero
  scripts y cero píxeles de Ko-fi en la página, así que el argumento de «sin banner de
  cookies» sigue intacto.
- **Esquema con migración.** `analitica.py` gana un `_migrar()` (`PRAGMA table_info` +
  `ALTER TABLE`, el patrón de `base_datos.py`): una `analitica.db` que ya existiera se
  actualiza sin perder el histórico. Verificado sobre una base con el esquema anterior.
- **Arreglado de paso:** el `<tbody id="an-usuarios">` de la analítica chocaba con el
  `<input id="an-usuarios">` de los destinatarios de un anuncio, así que
  `$('an-usuarios').value` era `undefined` y **no se podía enviar un aviso a jugadores
  concretos**. La tabla pasa a `an-tabla-usuarios`.
- **Pruebas:** `tools/test_analitica.py` sube a 39 comprobaciones (clics vs. visitas,
  CTR, el corte tras jugar / sin jugar, atribución a la cuenta y descarte de la
  etiqueta que manda el cliente).

---

## 2026-07-26 — Analítica de uso en el panel (Roadmap #24)

Un «Search Console» propio dentro de `/admin`: cuánta gente entra, de dónde viene,
cuánto se queda, cuántos llegan a jugar y cuántos se quedan. Documentado en
[Analytics](wiki/Analytics.md).

- **Sin banner de cookies, y por diseño.** Lo que obliga a pedir consentimiento no es
  la palabra «analítica», es *guardar o leer algo en el dispositivo*. Así que no se
  guarda nada: ni cookie de analítica, ni `localStorage`, ni huella. La visita se
  agrupa con `sha256(sal + IP + user-agent)` donde **la sal es aleatoria, vive solo en
  memoria y rota cada día** — la IP en crudo no se almacena nunca y el mapeo no lo
  puede recomponer después nadie, tampoco el dueño. Ese es el perfil de «medición de
  audiencia» que la AEPD y la CNIL dejan fuera del consentimiento previo. Lo único
  obligatorio sí se ha hecho: `privacy_p3` de `static/app.js` tiene un punto nuevo de
  *Medición de audiencia* en ES y EN, y el de cookies ahora dice «ni de analítica».
  El precio aceptado: un visitante sin cuenta solo es reconocible dentro del mismo día,
  así que la retención entre días es exacta solo para cuentas — y el panel lo dice al
  lado del número en vez de disimularlo.
- **`analitica.py` + `analitica.db` (nuevos).** Módulo aditivo (patrón `admin.py`) con
  base propia en WAL: es el mayor volumen de escritura del proyecto y no debe competir
  con las partidas ni engordar la copia de `mus.db` que se descarga del panel.
- **Nunca estorba.** Las visitas vivas están en memoria y un greenlet vuelca cada 5 s;
  `analitica.evento()` se traga cualquier excepción a propósito — una métrica rota no
  puede tumbar una mano. Y el panel **solo lee agregados diarios** (el día en curso se
  reconsolida al vuelo), así que una consulta de 12 meses cuesta lo mismo que una de
  una semana. Lo crudo se purga a los 90 días.
- **Recogida.** `before_request` cuenta las cargas de página (fuera estáticos, `/api`,
  `/socket.io` y `/admin`); `static/analitica.js` late cada 30 s **solo con la pestaña
  visible** (más un `sendBeacon` al cerrar), así que una pestaña olvidada no infla el
  tiempo de permanencia. Los eventos de interfaz se instrumentan por delegación sobre
  los ids que ya existían: **`app.js` no se ha tocado**. Los eventos de juego los emite
  el servidor, no el cliente, así que un cliente parcheado no los puede falsear.
- **El panel** (`/admin` → Analítica): barra de periodo con export CSV; 12 tarjetas con
  la variación contra el periodo anterior *y* una línea explicando cómo se cuenta cada
  una; gráfico de evolución en SVG a mano con métrica conmutable (sin librerías);
  embudo visita→interacción→juego→partida terminada→cuenta; «ahora mismo» leído de
  memoria; desgloses por origen, medio, campaña, país, idioma, dispositivo, navegador,
  sistema, modo de juego, baraja, página de entrada y evento; retención por cohortes
  semanales de alta; y tabla por usuario ordenable, buscable y con detalle por día.
- **Borrado.** `olvidar_usuario()` está enganchado en **los dos** caminos de borrado de
  cuenta (el del jugador y el del panel), así que una petición de supresión no necesita
  ningún paso extra; más un botón de «borrar toda la analítica», auditado.
- **Sutileza de atribución que conviene recordar:** un evento se apunta a la visita que
  hace la petición, y eso es falso cuando el clic de uno arranca algo para otro (quien
  se une a una sala arranca la partida de los dos asientos). Para eso está
  `evento(..., por_usuario=True)`, que busca la visita por cuenta en vez de por
  petición. Sin ello las dos partidas se le cargaban a quien pulsó; hay una prueba de
  regresión justo de eso.
- **Límites asumidos:** el país sale de la cabecera `CF-IPCountry`, así que pone
  `desconocido` hasta que haya Cloudflare delante (#16) — meter una base GeoIP o llamar
  a un servicio externo tiraría por tierra todo el argumento de privacidad. Y pasados
  90 días se pueden seguir viendo todas las cifras, pero ya no se pueden inventar
  cruces nuevos (país × dispositivo, por ejemplo).
- **Verificación:** 30 comprobaciones automáticas (conteo de visitas con crawlers y
  estáticos fuera, rebote y tasa de juego, las nueve dimensiones, embudo, en vivo,
  atribución a cuenta y su borrado, atribución cruzada, retención, CSV, mantenimiento,
  lectura de un día de hace 200 días solo desde agregados, y rechazo de eventos
  falsificados y latidos absurdos), incluyendo la afirmación explícita de que **ninguna
  IP ni ningún user-agent llegan a la base de datos**. En navegador, contra un juego de
  datos sembrado de 57 días, se comprobó que todo pinta y que cada control (periodo,
  métrica, dimensión, orden) vuelve a consultar bien. Y contra el servidor real, que
  una carga de página, un referer, un latido y un evento de socket acaban en
  `analitica.db`.

---

## 2026-07-26 — Fase 1 del bot 2v2: log v2, motor rápido y arnés de medición

Infraestructura de la que dependen todas las fases de entrenamiento siguientes
([Bot-AI-4p-Roadmap](wiki/Bot-AI-4p-Roadmap.md) Fase 1). No cambia cómo juegan los
bots; cambia lo que se puede medir y con qué datos se puede entrenar. Documentado en
[Bot-AI](wiki/Bot-AI.md) §4.

- **Log v2 con *event sourcing*** (`mus_log.py`, nuevo): un solo módulo para los dos
  motores, un fichero por match en `logs/v2/`. Se registran HECHOS (reparto, robos,
  decisiones, declaraciones, resolución por lance), no features: cualquier variable de
  entrenamiento se deriva luego RE-JUGANDO el log. Eso es lo que el v1 no permitía —
  congelaba un conjunto fijo de features al escribir, así que mejorar el encoder no
  servía de nada para los datos viejos. Los ficheros v1 (`logs/*.jsonl`) quedan
  congelados y se borra el camino `registrar_movimiento_ia`. Dos desvíos deliberados
  del esquema del borrador: los valores de carta se guardan CRUDOS (sin normalizar 3→12
  y 2→1, que es irreversible y rompería la re-jugada) y los descartes guardan los
  ÍNDICES tirados en vez de los valores.
- **Re-jugada** (`mus_replay.py`, nuevo): el motor solo tiene una fuente de azar, la
  baraja, y la re-jugada la sustituye por las cartas que dicta el log.
  `tools/log_verify.py` usa esto en su forma fuerte: re-juega el match, REGENERA el
  flujo de eventos y lo compara evento a evento con el fichero. Cuando coinciden se
  demuestran dos cosas de golpe: el log basta para reconstruir la partida, y el motor
  de hoy sigue resolviendo el mus como el día del registro (test de regresión gratis
  sobre tráfico real). `tools/selftest_log.py` lo automatiza jugando al azar entre las
  acciones legales, que es lo que recorre los rincones raros.
- **Clonado rápido del motor** (`fork()` / `to_state()` / `from_state()` en los dos
  motores): las cartas son inmutables en la práctica, así que el fork copia solo los
  contenedores y las comparte. Se cambia `copy.deepcopy` en `mus_env.py`. De paso, dos
  optimizaciones que salieron del perfil: evaluar pares/juego sin `collections.Counter`
  (~170.000 objetos por 120 travesías) y no construir el dict de `vista()` en cada
  `step()`. `to_state()` es JSON-able, así que también resuelve gratis la
  serialización que pedía Roadmap #18 capa 2.
- **Puerta de rendimiento superada** (`bench_env.py`, nuevo): 2p 38,2 → 490,3
  traversals/s y 2v2 47,5 → 545,4 (11,5× el peor caso, puerta ≥10×). Contra el código
  anterior a la Fase 1 el "antes vs después" real en 2p es 22,7 → 490,3 = **21,6×**,
  que sí alcanza el objetivo de 20×. Queda pendiente para la Fase 2 agrupar consultas
  a la red y los workers de multiprocessing: no se pueden afinar sin una red de verdad
  en el bucle.
- **Encoder único** (`encoder.py`, nuevo): 71 dimensiones en bloques A–E, la MISMA
  función para entrenar, servir y exportar datasets. Es la corrección de raíz del
  desajuste entrenamiento/servicio. El bloque E (señas) queda reservado a cero desde
  hoy para que el ajuste fino de la Fase 6 continúe desde el checkpoint sin señas en
  vez de reentrenar.
- **Gimnasio 2v2** (`mus_env4.py`, nuevo): recompensa = delta de puntos de la mano por
  equipo (no el marcador absoluto) y muestreo de estados REALES sacados de los logs v2
  en vez de marcadores uniformes inventados. Sin corpus todavía cae a un prior
  explícito y lo dice (`env.dist.origen`), para que nadie confunda "sin datos" con
  "medido".
- **Arnés de medición**: `tools/arena4.py` (asientos permutados, repartos sembrados,
  puntos por mano ± error estándar en vez de winrate de match) y `tools/lbr_probe.py`
  (Local Best Response para 2p: cota INFERIOR de explotabilidad).
- **Comprobado**: 8 matches al mejor de 3 por el camino real de `server_mus4` re-juegan
  byte a byte; ~1.160 matches al azar en ambos motores, todos byte-exactos;
  `MusBettingEnv4` con 10.000 manos y 59.133 decisiones sin un solo estado ilegal;
  arena4 da heurístico vs aleatorio +14,66 ± 2,81 puntos/mano; LBR saca +12,8 al
  aleatorio y **0,0** al heurístico calibrado con tablas (la sonda no encuentra
  explotación — que NO es lo mismo que decir que ese bot sea fuerte).
- Se añade `LOG_V2` en `server_mus4.py` como interruptor (los soaks lo apagan para no
  ensuciar el corpus) y la descarga de logs del panel de admin recorre ya todo el árbol
  `logs/`.

## 2026-07-25 — Estrategia ML del bot 2v2 (análisis y hoja de ruta) — solo documentación

Dos páginas nuevas en la wiki, sin cambios de código:

- **[Bot-AI-4p-ML-Strategy](wiki/Bot-AI-4p-ML-Strategy.md)** — análisis en profundidad
  del bot profesional para mus 2v2: viabilidad de Deep CFR en juego de equipos
  (suma cero entre dos equipos, TMECor; comparación con el repo de Deep CFR para
  hold'em de 6 jugadores), combinación con RL (best responses, reward shaping por
  probabilidad de ganar la partida, DREAM/R-NaD), cómo medir la distancia a Nash
  (explotabilidad, LBR, ancla tabular exacta en 2p), interpretabilidad (PCA,
  importancia por permutación, SHAP, clustering de estrategias), rediseño del formato
  de logs (v2, *event sourcing* reproducible — hoy `mus_mecanicas_4.py` **no registra
  nada**), otras técnicas (clonación de comportamiento, modelado de oponentes,
  destilación) y el plan para señas (bloques de entrada reservados desde ya).
- **[Bot-AI-4p-Roadmap](wiki/Bot-AI-4p-Roadmap.md)** — plan por fases: P0 bot heurístico
  jugable ya + fontanería de asientos, P1 logs v2 + motor rápido (`fork()` en vez de
  `deepcopy`, puerta de ≥10×) + arnés de medición, P1.5 CFR tabular 2p como ancla
  exacta, P2 reglas 2v2 completas + primera generación Deep CFR (`4g1`), P3 programa
  de fuerza, P4 capas explotadora y humana (bot paramétrico con diales), P5 programa
  de interpretabilidad, P6 señas. Decisiones del propietario incorporadas: nube de
  pago OK (presupuesto pequeño; el análisis estima $5–15 por tanda en CPU alquilada),
  reglas tradicionales completas, ruptura limpia del formato de logs, y bot final
  paramétrico (near-Nash + explotador + humano). Sustituye a Roadmap #7/#8 y absorbe
  la parte de IA de #20.

También se corrige de paso una imprecisión de [Bot-AI](wiki/Bot-AI.md): la red de
regrets **sí** se reinicializa en cada iteración de `train_cfr.py`.

---

## 2026-07-25 — Panel de administración online (Roadmap #13)

Gestionar el juego desde el navegador en vez de por SSH: cuentas, salas en curso,
descargas, variables globales, soporte a los jugadores y avisos.

### Dónde vive y qué hace falta para desplegarlo

**No hace falta desplegar nada aparte.** El panel es un módulo más (`admin.py`) que se
engancha en el mismo proceso Flask, el mismo puerto y la misma sesión que el juego, con
el patrón de `social.py` (`init_admin(app, socketio, ctx)`). Basta con abrir `/admin`.
Lo único nuevo en el entorno es `ADMIN_USERNAME`: la cuenta que se promueve a
administradora al arrancar el servidor. Es la única forma de crear el **primer**
administrador; a partir de ahí el acceso se otorga desde el propio panel y la variable
se puede dejar vacía.

### Permisos

Columnas nuevas en `Usuarios`: `is_admin`, `banned`, `ban_motivo`, `ban_en` (migración
idempotente como siempre). El decorador `admin_requerido` cierra todo `/admin/**`; los
no administradores reciben 403, nunca una pista de si la ruta existe. Un baneo actúa en
tres sitios: `/auth/login` lo rechaza con motivo, `/auth/sesion` vacía la cookie de una
sesión ya abierta, y el handler `connect` de `social.py` devuelve `False`, que rechaza
el socket antes de crearlo (es el único `connect` del servidor, por el límite de un
handler por evento de Flask-SocketIO 5.x). Al banear, además, se cierran al momento las
conexiones vivas de esa cuenta y se la saca de su sala.

### Qué se puede hacer desde `/admin`

- **Resumen:** cuentas, altas de hoy, partidas 1v1 y 2v2, salas vivas y conexiones.
- **Cuentas:** búsqueda por nombre, correo o `#código`; banear/desbanear con motivo;
  corregir ELO, victorias y derrotas; dar o quitar administrador; borrar la cuenta
  (reusa `anonimizar_usuario`, así que el historial de los rivales se conserva); y
  "enviar código de contraseña", que **no** fija ninguna contraseña: manda al correo del
  usuario el mismo código de recuperación que el flujo de "he olvidado mi contraseña",
  de modo que el administrador nunca llega a conocer la contraseña de nadie.
- **Salas:** instantánea unificada de `salas` (2p) y `salas4` (4p) con estado, fase,
  ocupantes, edad e inactividad, y un botón para cerrar una sala atascada. Sustituye a
  `/api/debug/salas`, que se queda como está para depuración sin sesión.
- **Datos:** copia de `mus.db` hecha con la API de *backup* de SQLite (se puede
  descargar con el servidor en marcha) y zip de `logs/*.jsonl` filtrable por fechas.
- **Variables y bot:** tabla `Config` (clave→valor) editable en caliente. Hoy están
  conectadas `bot_checkpoint`, `bot_delay`, `mantenimiento_activo` y
  `mantenimiento_texto`; se pueden crear claves libres para el futuro, y la tabla marca
  cuáles tienen quien las lea.
- **Auditoría:** tabla `AdminAudit` con fecha, administrador, acción, objetivo, detalle
  e IP (respetando `X-Forwarded-For` para cuando llegue el proxy de #16). Toda acción de
  administración queda registrada y no se puede borrar desde el panel.

### Checkpoint del bot elegible sin reiniciar

`bot_ml` carga el modelo **una sola vez por proceso** y lo comparte entre todas las
salas (antes cada `SmartBot` releía el `.pth` del disco: cada partida contra la IA
pagaba la carga entera). `ruta_checkpoint_activa()` lee `bot_checkpoint` de la tabla
`Config`, acepta solo un nombre de archivo dentro de `learn/cfr` (nunca una ruta) y cae
al de por defecto si no existe. El panel llama a `invalidar_modelo_cacheado()` al
guardar, así que el siguiente bot nace con el modelo nuevo.

### Soporte con conversación

Botón **Soporte y contacto** dentro de Ajustes (visible con y sin cuenta; sin cuenta
explica que hace falta una para poder contestar). Tablas `SupportTickets` y
`SupportMessages`: el jugador abre una incidencia con tipo y asunto, y el hilo va y
viene hasta que alguno lo da por resuelto. El estado se mueve solo — a `respondido`
cuando contesta el administrador y a `abierto` cuando escribe el jugador —, de forma que
la bandeja del panel siempre enseña lo que falta atender. Contador de respuestas sin
leer sobre el botón ⚙ y notificación en vivo por el canal `notificacion` de #3.

### Avisos a los jugadores

Tabla `Anuncios` con dos formas: **notificación** (llega una vez, sale en un popup y se
marca leída en `AnuncioLeido`, de modo que quien estaba desconectado la ve al volver) y
**mensaje fijado**, que se queda en el menú principal hasta que caduque o se retire.
Audiencia: todos, un grupo de #3, o una lista de nombres/`#códigos`. El cartel de
mantenimiento sale del par de variables `mantenimiento_*` y lo ve todo el mundo,
incluidos los invitados.

### Dos fallos ajenos encontrados por el camino

- `enviar_estado_a_jugadores` repetía `import base_datos` dentro de la función, lo que
  convertía el nombre en local de todo el cuerpo: cualquier otro uso del módulo dentro
  de esa función reventaba con `UnboundLocalError` y mataba el greenlet — el bot dejaba
  de mover y la partida se quedaba congelada. Import redundante eliminado.
- `mus_mecanicas.py` usaba `json.dumps` para volcar `logs/<match_id>.jsonl` sin tener
  `json` importado a nivel de módulo: **todos los archivos de log se creaban vacíos**.
  Con el `import json` puesto, una partida completa contra la IA escribe sus ~10 KB.
  Sin esto, la descarga de logs del panel bajaba archivos vacíos.

**Verificación:** ciclo completo probado contra el servidor real — permisos (403 sin
sesión y con cuenta normal), baneo (login, sesión abierta, socket vivo expulsado y
reconexión rechazada), protecciones (no banear a un administrador, no quedarse sin
ningún administrador), edición de estadísticas, hilo de soporte de ida y vuelta con
aislamiento entre usuarios, anuncios de los tres alcances con lectura y retirada,
validaciones de `bot_delay` y `bot_checkpoint` (incluido un intento de ruta con `../`),
descarga de la copia de la BD y del zip de logs con filtro de fechas, listado y cierre
forzado de una sala, y auditoría de todo lo anterior. En el navegador: cartel de
mantenimiento como invitado, ventana de soporte y conversación, popup de aviso en vivo,
y las siete pestañas del panel. Regresión: una partida completa contra la IA hasta 40.

---

## 2026-07-25 — Código de jugador permanente y "entrar con Google" no registra (Roadmap #23)

Tres cosas encadenadas, todas a raíz de un informe: *crear cuenta con Google, borrarla,
pulsar Entrar… y aparecer dentro sin haberse registrado.*

### Por qué pasaba

`Entrar con Google` y `Registrarse con Google` iban al mismo sitio y hacían lo mismo:
`registrar_o_loguear_google()` creaba la cuenta si no la encontraba. Al borrar la cuenta
se le quitaba el `google_id`, así que al volver a pulsar Entrar no la encontraba y la
creaba otra vez — y como el borrado también dejaba libre el nombre, salía con el mismo
nombre de antes. Parecía que la cuenta había resucitado.

Ahora `/auth/google/login` acepta `?intent=login|signup`, guardado en la sesión de Flask
(no en la URL de vuelta, para que no se pueda forzar desde fuera). Solo el botón de
registrarse autoriza a crear; el de entrar recibe `None` y el callback redirige a
`/?auth_error=google_sin_cuenta`, que el cliente traduce y acompaña abriendo el registro.
Sin `intent` se asume "entrar", que es la opción prudente.

### Código público permanente (`#A7K2QX`)

Columna nueva `Usuarios.codigo`: 6 caracteres de un alfabeto sin `0/O` ni `1/I/L` (está
pensado para dictarlo y teclearlo), índice único parcial, asignado al registrarse y
rellenado por la migración en las cuentas que ya existían. **No cambia nunca y no se
recicla:** sobrevive a un cambio de nombre y sobrevive al borrado de la cuenta, así que
el índice único basta para garantizar que nadie hereda el identificador de otro.

Se enseña en la ventana de ajustes (se copia con un click) y junto a cada nombre en la
clasificación mundial. `/api/friends/request` y la invitación a grupos aceptan tanto el
nombre como el `#código`, resueltos por `social._resolver_objetivo()`.

### Borrar la cuenta libera el nombre

Antes la fila anonimizada se quedaba llamándose `EliminadoNN`, que es un nombre
perfectamente registrable y por tanto ocupado para siempre. Ahora pasa a llamarse
`#CODIGO` — imposible de registrar, porque el regex de alta solo admite `[A-Za-z0-9_]` —
y se marca con `eliminada_en`. El nombre original queda libre para otro jugador, y si
alguien lo coge no hay confusión posible: son códigos distintos.

Una fila marcada queda fuera de la clasificación, de `obtener_usuario`,
`obtener_id_usuario`, `verificar_login`, de las dos búsquedas de Google y de la búsqueda
por código: no se puede entrar en ella, ni encontrarla, ni pedirle amistad. Para cuando
haya pantalla de historial de partidas (Roadmap #19), `obtener_jugador_publico(id)`
devuelve `{codigo, eliminada, username=None}` para que se pinte como cuenta eliminada y
no como quien ahora se llama igual. Las cuentas borradas con el esquema anterior las
convierte una migración de una sola pasada.

De propina, `/auth/sesion` ahora vacía la cookie cuando la cuenta a la que apunta ya no
existe, en vez de dejarla señalando a la nada.

**Verificación:** dos suites nuevas (44 comprobaciones) sobre la migración y su
idempotencia, la unicidad de los códigos, su supervivencia a un renombrado, los efectos
del borrado, la reutilización del nombre por otra persona y los cuatro caminos de Google
(incluido borrar → entrar → *no hay cuenta* y borrar → registrarse → *código nuevo*).
Comprobado además en el navegador (código en ajustes en ES/EN, clasificación, añadir por
código en minúsculas) y con las suites de #21 y #22, que siguen pasando.

---

## 2026-07-25 — Menú de ajustes y arreglo del estado de sesión (Roadmap #22)

Dos cosas: el bug de "inicio sesión y sigo apareciendo fuera hasta que refresco" (y su
simétrico al cerrar sesión), y una ventana de ajustes que sustituye al botón EN/ES.

### El bug de la sesión

Tenía dos causas y se han cerrado las dos:

- **`/auth/sesion` viajaba sin cabeceras de caché.** Sin `Cache-Control`, algunos
  navegadores (Safari es el caso típico) reutilizan la respuesta anterior de un GET: si
  la guardada decía "no hay sesión", al entrar seguías apareciendo fuera; si decía que
  sí, al salir y recargar volvías a aparecer dentro. Es exactamente el síntoma descrito.
  El `after_request` manda ahora `no-store, no-cache, must-revalidate` (más `Pragma` y
  `Expires`) en todo `/auth/*` y `/api/*`, y el cliente pide la sesión con
  `cache: 'no-store'`.
- **El cliente solo pintaba la rama "logueado".** Si `/auth/sesion` decía que no, no se
  tocaba nada y la pantalla se quedaba como estuviera. `comprobarSesion()` deriva ahora
  la interfaz de la respuesta en los dos sentidos (nueva
  `actualizarInterfazDeslogueado()`), se vuelve a comprobar en `pageshow` cuando el
  navegador restaura la página desde la bfcache, y al cerrar sesión se pinta la salida
  *antes* de recargar, no después.

### Ventana de ajustes (`static/settings.js`, `#modal-settings`)

El botón EN/ES de la esquina pasa a ser un ⚙ que abre la ventana. Existe con cuenta y
sin ella (para un invitado no había ningún ajuste útil aparte del idioma, así que se le
añaden también su nombre en la mesa y accesos a entrar/registrarse).

- El botón de idioma conserva el id `btn-lang` dentro de la ventana: `app.js` y
  `tutorial.js` ya escuchaban ahí y siguen funcionando sin tocarlos.
- **Cerrar sesión** se ha quitado de la barra superior y vive ahora aquí.
- Con cuenta hay cuatro secciones `<details>`: cambiar nombre, cambiar correo, cambiar
  contraseña y eliminar la cuenta.

### Cuenta (nuevos `POST /auth/cuenta/*`)

- **Autorización:** `_autorizar_cambio()` acepta la contraseña actual **o** un código de
  un solo uso enviado al correo. Las cuentas creadas con Google no tienen contraseña
  utilizable (columna nueva `tiene_password`, a 0 al crearlas y en la migración para las
  filas con `google_id`), así que sus paneles van por código y les ofrecen *crear* una.
- **Correo en dos pasos:** el código va a la dirección NUEVA (es lo que demuestra que es
  suya) y a la vieja le llega un aviso de que alguien ha pedido el cambio. El correo no
  se escribe hasta confirmar.
- **Nombre de usuario:** mismas reglas que en el registro y un cambio cada 30 días
  (`DIAS_ESPERA_CAMBIO_USERNAME`, columna `username_cambiado_en`). Renombrar es seguro
  porque amigos, grupos, mensajes e historial guardan `Usuarios.id`, nunca el nombre; se
  recarga la página después porque el socket abierto todavía lleva el nombre viejo en su
  copia de la sesión.
- **Borrado de cuenta = anonimización.** `anonimizar_usuario()` borra correo, país,
  fecha de nacimiento y `google_id`, renombra a `EliminadoNN`, deja una contraseña
  inservible, elimina amistades y mensajes (directos y de grupo) y sale de todos los
  grupos reutilizando `salir_del_grupo()` (la propiedad pasa al miembro más antiguo, o
  el grupo desaparece si se queda vacío). La fila se conserva porque `Partidas` y
  `Partidas4` apuntan a su id: borrarla dejaría a los rivales con un historial y un ELO
  falseados. Además hay que teclear el propio nombre de usuario para confirmar.
- Las respuestas llevan `{exito, codigo, mensaje}`: `codigo` es una clave del
  diccionario para que el cliente la enseñe en su idioma, y `mensaje` el castellano de
  respaldo.

### Verificación

Probado en el navegador (ventana de invitado y de cuenta, cambio de idioma, renombrado y
su periodo de espera, cambio de contraseña, borrado) y con una batería de pruebas que
cubre el ida y vuelta del correo, la credencial por código de las cuentas de Google
(incluido que es de un solo uso), el periodo de espera, los efectos del borrado sobre las
tablas sociales, los 401 sin sesión y las cabeceras anti-caché.

---

## 2026-07-25 — Salas fantasma: corrección de los 6 vectores (Roadmap #21)

Cerrados todos los agujeros por los que quedaban salas y jugadores "fantasma" en memoria
(salas muertas anunciadas en el vestíbulo, `jugadores` con entradas huérfanas, partidas
congeladas por una excepción a mitad de reparto). Todo el trabajo es en `server.py` salvo
un caso en `social.py`. El modo de 4 jugadores no se ha tocado: ya tenía su propio
barredor y ahora el de 2p lo respeta explícitamente.

### Salas que no morían (bug 1)

- **`emitir_lista_publicas` ya no anuncia salas sin nadie vivo dentro.** Nuevo helper
  `_sid_vivo(sid)` (no `None`, no `BOT_`, y todavía presente en `jugadores`). Antes una
  sala cuyo creador se había caído se publicaba con `creador_sid: None` y se quedaba en
  el vestíbulo indefinidamente.
- **`limpiar_sala_huerfana`** (el temporizador de 2 min) comprueba ahora que no quede
  ningún asiento *vivo*, en vez de exigir que todos sean `None`, y destruye la sala con
  `_destruir_sala_2p`.
- **Barredor periódico nuevo `_barredor_2p`** (cada 5 min, espejo del de `server_mus4`),
  extraído en `_pasada_barredor()` para poder probarlo. Entierra: salas en espera sin
  nadie vivo (con 2 min de gracia vía `vacia_desde`, por si es un refresco), salas en
  espera de más de 30 min, partidas sin actividad más de 2 h, y pausas o ventanas de
  sustitución vencidas cuyo temporizador puntual se hubiera perdido.

### Rastros huérfanos (bugs 2 y 3)

- **`_destruir_sala_2p`** ya no limpia solo los asientos actuales: recorre `jugadores`
  entero eliminando todo lo que apunte a esa sala (sids remapeados tras una reconexión,
  el sid falso `BOT_<código>`) y llama a `close_room`.
- **`abandonar_sala_limpiamente`** se extrajo a `_salir_de_sala_2p(sid)`: ahora hace
  `leave_room`, libera el asiento y su token, borra la entrada de `jugadores` y, si se
  invoca con una partida viva, deriva a `_abrir_hueco_2p` para que al rival se le
  ofrezca esperar sustituto en lugar de quedarse mirando una mesa congelada.
- El barredor elimina además las entradas de `jugadores` cuya sala no existe ni en
  `salas` ni en `salas4` (comprobado: no toca a los jugadores de partidas 4p).

### Carrera de asientos (bug 4)

- En `unirse_sala`, `sids` se normaliza a **dos huecos fijos antes** de elegir, la
  asignación es `sids[i] = sid` (nunca `append`) y se revalida la ocupación justo antes
  de sentar. Dos `unirse_sala` solapados ya no pueden dejar una sala de tres asientos: el
  segundo recibe `error_sala`.

### Partidas congeladas (bug 5)

- `enviar_estado_a_jugadores` es a prueba de `KeyError`: si un asiento tiene un sid que
  el motor ya no conoce se omite con un aviso, el estado del rival se lee de un
  `estado_rival` con valores por defecto, y `partidas_ganadas` y el log usan `.get()`.
- La tarea de fondo del bot va envuelta en `try/except`: una excepción suya ya no puede
  matar el greenlet dejando la mesa a medio actualizar.

### Observabilidad (bug 6)

- Las salas llevan `creada_en` y `ultima_actividad` (se sella en
  `procesar_accion_interna`, al entrar, al reanudar y al sentar a un sustituto).
- Nuevo `GET /api/debug/salas?token=…`: estado, edad, inactividad, asientos con su
  vitalidad, fase y ronda de cada sala, más el recuento de huérfanos. **Devuelve 404 si
  no hay `DEBUG_TOKEN` en el entorno** (añadido a `.env.example`). Será la fuente de
  datos del panel de administración (#13).

### Amigos (`social.py`)

- `invitar_amigo` creaba la sala de la invitación aunque el anfitrión ya estuviera
  sentado en otra: `jugadores[sid]` se sobrescribía y la sala anterior quedaba de
  fantasma. Ahora se le desaloja antes mediante el hook `salir_de_sala` del contexto.
- La sala de invitación recibe `tokens`, `creada_en` y `ultima_actividad` como las
  demás, así que el anfitrión puede reanudarla si refresca y el barredor la ve.

### Verificación

- **Soak test** con clientes Socket.IO reales sobre la matriz completa: crear/abandonar
  por botón, caída brusca en espera, vs IA (abandono y caída), 1v1 (arranque, caída,
  reanudación por token, abandono con oferta de sustituto) y dos `unirse_sala`
  simultáneos. `salas` y `jugadores` quedan vacíos salvo partidas vivas y el vestíbulo
  nunca lista una sala muerta.
- **Prueba directa del barredor** con salas envejecidas a mano: las cinco reglas de
  caducidad, la gracia de 2 min, la purga de huérfanos (incluido `BOT_`) y la garantía
  de que no toca las salas 4p.
- **Regresión 2p:** partida completa contra la IA jugada hasta el final del match sin
  campos nulos ni claves perdidas en el payload de `actualizar_mesa`.

---

## 2026-07-24 — Mus a 4 jugadores (2v2, online, sin bots) (Roadmap #6)

Nuevo modo de juego completo para 4 jugadores humanos en una sala (2 equipos, compañeros
enfrentados: A = asientos {0,2}, B = {1,3}). Todo **aditivo y en paralelo** siguiendo
`wiki/Implementing-Mus-4-Players.md`: no se tocaron `PartidaMus`, `bot_ml.py` ni el
pipeline de entrenamiento; el juego de 2p queda intacto (verificado por regresión).

### Backend

- **`mus_core.py`** (nuevo): capa fina que *reexporta* las funciones puras de
  `mus_mecanicas.py` (sin moverlas) y añade `mejor_hand_equipo` para reducir un equipo a
  su mano representativa reutilizando los comparadores por pares del motor de 2p.
- **`mus_mecanicas_4.py`** (nuevo): motor `PartidaMus4`, indexado por **asiento** (no por
  sid) y con puntos/apuestas **por equipo**. Mus con acuerdo de los cuatro, descartes,
  apuestas equipo-vs-equipo (responde un único asiento rival por turno, simplificación v1
  documentada), salto/auto-adjudicación de Pares/Juego con declaraciones automáticas,
  recuento con **bonus por cada mano cualificada** del equipo ganador y desempates por
  cercanía a la mano, rotación de mano por ronda y logging JSONL con `modo:'4p'`.
- **`base_datos.py`**: tabla `Partidas4` (ambos equipos + marcador final del match, p. ej.
  2-1) y columnas 4p en `Usuarios` (`victorias_4p`, `derrotas_4p`, `juegos_4p`) vía
  migración idempotente; `registrar_partida_4()` guarda la partida y suma a cada jugador
  los juegos ganados por su equipo. No toca el ELO 1v1.
- **`server_mus4.py`** (nuevo, patrón `init_mus4(socketio, jugadores, salas)` como
  `social.py`): registro `salas4` separado, mapeo asiento↔sid, eventos `*_4`
  (`crear_sala_4`, `unirse_sala_4`, `accion_juego_4`, `pedir_publicas_4`,
  `abandonar_sala_4`, `reanudar_partida_4`), `enviar_estado_4` (reparto ciego por
  asiento, nunca cartas del compañero salvo en recuento), **temporizador de turno
  autoritativo** (auto-pasa/no-ve/no-mus por token monótono), **gracia de reconexión**
  (pausa 90 s + reanudar por asiento gracias al motor seat-keyed) y barredor de salas
  fantasma. El `disconnect` se invoca desde el handler único de `server.py`
  (`server_mus4.disconnect_4()`), no se registra otro (Flask-SocketIO admite uno por
  evento). `server.py`: solo `import server_mus4` + `init_mus4(...)` + una línea en
  `disconnect`.

### Frontend

- **`static/style4.css`**, **`static/table4.js`** (render con diffing + animaciones de
  reparto/giro de showdown/órdago/puntos flotantes, respeta `prefers-reduced-motion`) y
  **`static/app4.js`** (controlador: eventos socket, sala de espera con selector de
  asiento por equipo, botones, barra de cuenta atrás, reconexión por token en
  `localStorage`). Reutiliza `socket`/`dict`/`t` de `app.js`; solo añade claves i18n
  nuevas (es+en). `index.html`: botón **👥 Mus 4 jugadores**, modal de creación/espera,
  pantalla `#game-screen-4` (4 asientos relativos al espectador: yo abajo, compañero
  arriba, rivales a los lados) y nota en el Leaderboard explicando el registro 4p.

**Verificación:** motor validado con 300 matches simulados; test de integración con 4
clientes Socket.IO reales jugando un match completo (a 1 y a 3) con registro en
`Partidas4`; pausa por desconexión + reanudación por token OK; regresión 2p (aviso de
`rival_desconectado` tras caída) OK; render de mesa y recuento verificados en el
navegador en ES y EN.

---

## 2026-07-24 — Amigos, mensajería, grupos y clasificación de grupo (Roadmap #3)

Capa social completa para usuarios registrados: añadir amigos, chatear (en vivo y
offline), formar grupos, chat de grupo, clasificación ELO solo del grupo e invitar a
un amigo directamente a una partida. Todo aditivo — no se tocaron los manejadores del
juego. Arquitectura: persistencia + REST (fuente de la verdad en SQLite) con una capa
de presencia/notificaciones Socket.IO por encima (entrega en vivo, nunca la verdad).

### Backend

- **`base_datos.py`**
  - Nuevas tablas en `init_db()` (todas `CREATE TABLE IF NOT EXISTS`): `Friendships`
    (con orden canónico `user_low`/`user_high` para que una amistad sea una sola fila),
    `Messages` (DMs y mensajes de grupo), `Groups`, `GroupMembers` (con `last_read_id`
    como cursor de no-leídos por usuario). Índices para DMs y grupos.
  - Conjunto de funciones de datos: amistades (enviar/responder/eliminar/bloquear
    solicitud, `listar_amigos`, `son_amigos`…), DMs (`enviar_mensaje_dm`,
    `obtener_conversacion` que marca leídos, `contar_no_leidos`), grupos (crear, invitar,
    salir con transferencia de propiedad, listar, mensajes) y `leaderboard_grupo` (mismo
    formato que `obtener_leaderboard()`). Límites: 200 amigos, 50 grupos, mensajes ≤ 500.
- **`social.py`** (nuevo módulo, se engancha con `init_social(app, socketio, ctx)` desde
  `server.py` una vez definidos `socketio`, `salas`, `jugadores` y helpers)
  - Rutas HTTP con sesión (`@login_requerido`): `/api/friends*`, `/api/messages/<id>`,
    `/api/groups*` (detalle, invitar, salir, mensajes, `leaderboard`). La identidad "yo"
    siempre sale de la sesión, nunca del cuerpo de la petición.
  - **Presencia:** `usuarios_conectados = {username: set(sids)}`. Se registra un handler
    `connect` propio; el `disconnect` del juego en `server.py` llama a
    `social.presencia_disconnect()` (Flask-SocketIO 5.x no permite dos handlers para el
    mismo evento, así que se enlaza por llamada). Se avisa a los amigos al conectar/salir.
  - **Notificaciones** (`socketio.emit('notificacion', …, room=sid)`): tipos `mensaje`,
    `mensaje_grupo`, `solicitud_amistad`, `amistad_aceptada`, `presencia`,
    `invitacion_grupo`, `invitacion_partida`. Siempre se persiste primero.
  - **Invitación a partida:** evento socket `invitar_amigo {friend_id, al_mejor_de}` crea
    una sala **privada** reutilizando el flujo de `crear_sala` (asiento 0 = anfitrión) y
    manda el código al amigo; el invitado se une con el `unirse_sala` normal. Sin cambios
    en el motor de juego.
  - Rate-limit en memoria por usuario para mensajes y solicitudes; DMs solo entre amigos;
    comprobación de pertenencia/rol en toda ruta de grupo (403 si no).
- **`server.py`**: `import social` + `social.init_social(...)` al final; llamada a
  `presencia_disconnect()` dentro de `handle_disconnect`.

### Frontend

- **`index.html`**: botón **👥 Amigos** (con insignia de no-leídos) en la barra de usuario
  logueado; modal `#modal-social` con pestañas Amigos/Grupos; toast flotante y popup de
  invitación a partida entrante.
- **`static/social.js`** (nuevo): toda la UI social — lista de amigos con punto de
  presencia, solicitudes, añadir amigo, chat DM y de grupo (mismo componente),
  crear/abrir grupos, invitar, salir, clasificación de grupo y gestión de las
  notificaciones en vivo. Los cuerpos de mensaje se pintan con `textContent` (nunca
  `innerHTML`) para evitar XSS.
- **`static/app.js`**: claves i18n de la capa social en `dict.es` y `dict.en`;
  `cerrarModales()` también oculta `#modal-social`.

### Ajustes posteriores (mismo día, tras revisión)

- **Clasificación PROPIA del grupo (no la global filtrada):** se añadió la tabla
  `Partidas(id, fecha, ganador_id, perdedor_id, vs_bot)` y `registrar_partida_completa`
  ahora inserta una fila por cada partida humano-vs-humano entre usuarios registrados.
  `leaderboard_grupo` se reescribió: reproduce en orden cronológico solo las partidas
  jugadas **entre miembros del grupo** y únicamente las disputadas **después de que ambos
  se unieran** (`fecha >= joined_at` de los dos); cada jugador arranca de 1200. Así, si A
  ya le ganó 30-1 a B antes de que B entrara al grupo, esas partidas no cuentan en la
  clasificación del grupo (sí en la global). Un botón sutil `ⓘ` en la cabecera de la
  clasificación muestra un tooltip ligero que lo explica (aparece al pasar el ratón y se
  oculta al salir en escritorio; el clic lo alterna en móvil).
- **Roles de grupo:** admins/owner pueden ascender miembros a admin y degradar admins a
  miembro (`cambiar_rol_miembro`), y expulsar miembros (`expulsar_miembro`) — nunca sobre
  el **propietario original** (intocable). Nuevos endpoints
  `POST /api/groups/<id>/members/<uid>/role` y `.../remove`; botones por miembro en la UI.
- **Permiso de invitación configurable:** columna `Groups.invite_policy` (`'admins'`|`'all'`)
  con migración idempotente; solo admins la editan (`POST /api/groups/<id>/settings`).
  `añadir_miembro` respeta la política (`puede_invitar`). Selector "Quién puede añadir" en
  la vista de grupo para admins.
- **Fix de alternancia:** el botón *Clasificación del grupo* ahora es un toggle — al
  volver a pulsarlo se oculta la tabla y reaparece la lista de miembros.

### Verificación

- Probado end-to-end (localhost:5001, clientes REST + Socket.IO): solicitud/aceptación de
  amistad, DM en vivo y offline con no-leídos, presencia online/offline al conectar y
  desconectar, creación de grupo, invitación, mensajes de grupo en vivo, clasificación de
  grupo ordenada por ELO, e invitación a partida completa (anfitrión sentado → invitado
  acepta → ambos entran a un 2p normal). Casos límite rechazados en servidor: DM a
  no-amigo, añadirse a sí mismo, mensaje de 600 caracteres, leer grupo ajeno (403),
  invitar sin permiso, sin sesión (401). Sin errores en consola ni en el servidor.
- **Cuentas de prueba creadas** (para probar lo social sin la confirmación por correo,
  aún pendiente de despliegue): `test_ana`/`mustest1`, `test_beto`/`mustest2`,
  `test_carla`/`mustest3`, `test_dani`/`mustest4`, `test_eva`/`mustest5`.

---

## 2026-07-24 — Tutorial bilingüe ES/EN (Roadmap #2)

Se tradujo el tutorial y se integró en el motor de idioma existente. Ojo: la
suposición del Roadmap estaba invertida — el tutorial (~700 líneas) estaba
escrito **en inglés**, mientras la app arranca en español; el trabajo real fue
añadir el castellano y conectar el tutorial al selector de idioma.

### Frontend

- **`static/tutorial.js`**
  - Todo el contenido de las 14 diapositivas (título + HTML del cuerpo) se movió a
    un objeto `dictTutorial = {es:[...], en:[...]}`, indexado por la variable global
    `langActual` que define `app.js`. Única fuente de verdad del idioma; se reutiliza
    (no se duplica) la lógica de `localStorage['callmus_lang']`.
  - Ambos arrays (es/en) mantienen el mismo número y orden de slides, para que el
    salto de la diapositiva de práctica (índice 8) y el enlace `goToSlide(9)` sigan
    siendo válidos.
  - `getSlides()` / `getTutBtns()` devuelven las slides y las etiquetas de los botones
    (Siguiente/Anterior/Finalizar) del idioma activo; `renderSlide()` las usa y
    localiza también los botones de navegación.
  - **Re-render en vivo:** un listener en `#btn-lang` vuelve a pintar el tutorial si el
    modal está abierto (app.js cambia `langActual` primero, así que el tutorial ya lee
    el nuevo valor).
  - Terminología fiel a la del juego: Grande, Chica, Pares, Juego, Órdago, Mano, Postre,
    Pedrete y La Real quedan como nombres propios; verbos de apuesta en castellano
    (envidar/paso/quiero/no quiero); niveles de pares como Pares/Medias/Duples.
- **`static/app.js`**: nueva clave `btn_tutorial` en `dict.es` y `dict.en`.
- **`index.html`**: el botón *Cómo Jugar (Tutorial)* ahora se traduce con
  `data-i18n="btn_tutorial"`.

### Verificación

- Comprobado en el navegador (localhost:5001): el tutorial se abre en inglés en modo
  EN y en español en modo ES; al pulsar el botón de idioma con el tutorial abierto,
  el contenido cambia al vuelo ("The Spanish Deck" ↔ "La Baraja Española", botón ↔
  "Siguiente →") sin cerrar el modal. Sin errores en consola.

---

## 2026-07-24 — Autenticación completa (Roadmap #1)

Se completó la implementación del sistema de login (paso 1 del Roadmap). Antes solo
funcionaba usuario + contraseña; ahora hay registro con correo verificado,
recuperación de contraseña y acceso con Google.

### Backend

- **`base_datos.py`**
  - Nueva migración automática (`_migrar_columnas`): añade las columnas `email` y
    `google_id` a bases de datos antiguas sin perder datos, con índices únicos
    (case-insensitive para el email, parciales para no chocar con NULLs).
  - `registrar_usuario()` ahora guarda el `email`.
  - `verificar_login()` acepta **usuario O correo** y devuelve el username canónico.
  - Nuevas funciones: `existe_usuario()` (pre-chequeo de duplicados),
    `email_registrado()`, `actualizar_password()` (reset) y
    `registrar_o_loguear_google()` (crea o vincula cuenta por `google_id`/email).
- **`server.py`**
  - Secretos movidos a variables de entorno / `.env`: `SECRET_KEY`, `SMTP_USER`,
    `SMTP_PASS`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`. Avisos en el arranque si
    faltan. Cargador de `.env` propio (sin dependencia obligatoria de python-dotenv).
  - Envío de correos por SMTP SSL (Gmail) con `enviar_correo()` genérico.
  - Nuevos endpoints: `/auth/solicitar_codigo`, `/auth/solicitar_reset`, `/auth/reset`,
    `/auth/google/login`, `/auth/google/callback`. `/auth/registro` ahora verifica el
    código y auto-loguea; `/auth/login` acepta usuario o correo.
  - Códigos con caducidad de 15 min y límite de 3 solicitudes por correo y hora.
  - Validación de servidor: usuario 3–20 caracteres, email válido, contraseña ≥ 6.
  - OAuth de Google con Authlib, activado solo si hay credenciales.
- **`requirements.txt`**: añadidos `Authlib` y `requests`.

### Frontend

- Toda la lógica de autenticación se movió a **`static/auth.js`** (antes estaba
  duplicada e inline en `app.js`; ese bloque se eliminó). `index.html` ahora carga
  `auth.js` después de `app.js`.
- **`index.html`**: campo de correo en el registro; botón "Continuar con Google" en
  login y registro; enlace "¿Olvidaste tu contraseña?"; nuevos modales de
  verificación de código, recuperación y nueva contraseña.
- **i18n**: todos los textos nuevos pasan por `t()` con claves en `es` y `en`.
- Política de privacidad actualizada (se guarda el correo; la contraseña ahora se
  puede restablecer; mención al acceso con Google).

### Configuración / infra

- Nuevo **`.env.example`** con todas las variables y cómo obtenerlas.
- `.gitignore`: se ignoran `.env`, `.muslab`, `.obsidian`, `.DS_Store`.
- Nuevo `static/img/google_logo.svg`.

### Pendiente de que lo haga el propietario

- Crear la **contraseña de aplicación** de Gmail para `callmus.contact@gmail.com`
  (requiere verificación en 2 pasos) → `SMTP_PASS`.
- Crear las credenciales **OAuth 2.0** en Google Cloud Console → `GOOGLE_CLIENT_ID`
  y `GOOGLE_CLIENT_SECRET`, con los redirect URIs de producción y localhost.
- Definir un `SECRET_KEY` aleatorio en producción.
