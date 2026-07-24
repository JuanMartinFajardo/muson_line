# CallMus — Registro de cambios (log)

Historial cronológico de cambios relevantes del proyecto. El más reciente arriba.

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
