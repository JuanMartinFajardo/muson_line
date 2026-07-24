# CallMus — Registro de cambios (log)

Historial cronológico de cambios relevantes del proyecto. El más reciente arriba.

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
