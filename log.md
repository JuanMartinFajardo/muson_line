# CallMus — Registro de cambios (log)

Historial cronológico de cambios relevantes del proyecto. El más reciente arriba.

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
