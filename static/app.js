// ==========================================
// PRE-CARGA SILENCIOSA DE CARTAS
// ==========================================
// Usamos setTimeout para no bloquear el hilo principal ni la conexión de WebSockets.
// Esperará 2 segundos a que la web ya esté totalmente operativa antes de bajar las cartas.
//
// Con barajas temáticas (Roadmap #5) lo que hay que precargar depende de qué
// tema tenga puesto el jugador en cada palo, así que de eso se encarga
// decks.js; aquí sólo queda la baraja clásica para cuando ese archivo no esté.
setTimeout(() => {
    if (window.Barajas) { window.Barajas.precargar(); return; }

    const palos = ['coins', 'cups', 'swords', 'clubs'];
    const valores = ['01', '02', '03', '04', '05', '06', '07', '10', '11', '12'];

    palos.forEach(palo => {
        valores.forEach(valor => {
            const img = new Image();
            img.src = `/static/img/card_${palo}_${valor}.webp`;
        });
    });
    const back = new Image();
    back.src = '/static/img/card_back.webp';

    console.log("Cartas cacheadas en segundo plano.");
}, 2000);

// ==========================================
// PIEL DE LAS CARTAS (Roadmap #5)
// ------------------------------------------
// El servidor manda la identidad lógica de la carta y su `img` de la baraja
// clásica; estas dos funciones la traducen al tema que el jugador tenga puesto
// en ese palo. Si decks.js no ha cargado, se juega con la baraja de siempre.
//
// Cada carta se pinta con la baraja de SU DUEÑO: para las de otro jugador se
// pasa la suya, que llega en el estado de la mesa. Sin ese dato (cliente o
// servidor viejo) se cae a la propia, que es como funcionaba antes.
// ==========================================
function imgCarta(carta, baraja) {
    return window.Barajas ? window.Barajas.rutaCarta(carta, baraja)
                          : (carta && carta.img) || '/static/img/card_back.webp';
}

function imgDorso(baraja) {
    return window.Barajas ? window.Barajas.rutaDorso(baraja) : '/static/img/card_back.webp';
}

// ==========================================
// 0. CONEXIÓN AL SERVIDOR
// ==========================================


const socket = io({ closeOnBeforeunload: false });

let miNombre = "";
let faseJuego = 'espera';
let cartasSeleccionadas = [];
let subfaseApuestasActual = "";
let apuestaVistaActual = 0; // CORREGIDO: V mayúscula
let enPartida = false;
// Partida contra la IA: al salir no hay a quién avisar ni hueco que ofrecer, así
// que el texto de confirmación es distinto (se pierde la partida sin más).
let esPartidaContraBot = false;
let recuentoTimeout;
// Al mejor de N: lo guardamos para poder pintar las piedras (los amarrakos) en
// el recuento, donde el paquete del servidor no siempre lo repite.
let alMejorDeActual = 3;
// Baraja del rival (Roadmap #5): sus cartas se pintan con la suya, no con la
// mía. Llega en cada estado, y suelta si la cambia en mitad de la partida; para
// poder repintar en ese caso guardamos también el último estado recibido.
let barajaRival = null;
let ultimoEstadoMesa = null;

// PANTALLAS CORRECTAS
const menuScreen = document.getElementById('menu-screen');
const gameScreen = document.getElementById('game-screen');
const gameLog = document.getElementById('game-log');
let show_in_console = false;

// ==========================================
// 0. MOTOR DE IDIOMAS (i18n)
// ==========================================
const dict = {
    es: {
        btn_login: "Iniciar Sesión",
        btn_signup: "Registrarse",
        btn_logout: "Cerrar Sesión",
        btn_crear: "Crear partida nueva",
        btn_unirse: "Unirse con código",
        btn_show_leaderboard: "Ver Leaderboard",
        btn_tutorial: "🎓 Cómo Jugar (Tutorial)",
        btn_deal: "Repartir Cartas",
        btn_nomus: "Corto",
        btn_descartar: "Descartar",
        btn_next_round: "Siguiente ronda",
        btn_volver_menu: "Volver al Menú",
        btn_envidar: "Envidar",
        btn_pasar: "Pasar",
        btn_ordago: "Órdago",
        btn_ver: "Ver",
        btn_subir: "Subir",
        btn_nover: "No ver",
        btn_ordago_resp: "Órdago",
        al_mejor_de: "Al mejor de:",
        al_mejor_de_colname: "Mejor de",
        user_colname: "Usuario",
        action_colname: "Acción",
        public_games: "🌐 Partidas Públicas",
        esperando_rival: "Esperando a que se una el rival...",
        in_publico: "Hacer pública (visible para todos)",
        partidas: "partidas",
        mi_turno: "Tú hablas",
        my_cards: "Tus cartas aparecerán aquí",
        watermark: "Creado por Juan Martín Fajardo",
        login_remember: "Mantener la sesión iniciada",
        leaderboard_title: "🏆 Clasificación Mundial",
        elo_colname: "ELO 🔽",
        wins_colname: "Victorias ↕️",
        winrate_colname: "Winrate ↕️",
        loading_players: "Cargando jugadores…",
        codigo_sala: "Código de tu sala:",
        tu_nombre: "Tu nombre...",
        password: "Contraseña",
        signup_birth: "Fecha de nacimiento:",
        user_name: "Nombre de usuario",
        pais_nacimiento: "País de nacimiento",
        btn_cuenta: "Crear cuenta",
        opponent_speaks: "El rival habla",
        cartas_rival_ocultas: "[Cartas del rival ocultas]",
        txt_tu: "Tú",
        txt_pts: "Pts:",
        txt_partidas: "Partidas:",
        txt_rival: "Rival",
        codigo_placeholder: "Código de sala...",
        btn_next_game: "Siguiente partida",
        info_tus_cartas: "Tus cartas aparecerán aquí",
        info_esperando_rival_descarte: "Esperando a que el rival se descarte...",
        rival_siguiente_partida: "Esperando al rival para la siguiente partida...",
        info_esperando_rival_listo: "Esperando a que el rival esté listo...",
        info_rival_cambio: "El rival cambió ",
        cartas: " cartas",
        has_ganado_partida: "🏆 ¡HAS GANADO ESTA PARTIDA!",
        el_rival_ganado_partida: "💀 ¡HAS PERDIDO ESTA PARTIDA!",
        has_ganado_match: "🏆 ¡HAS GANADO EL MATCH!",
        el_rival_ganado_match: "💀 ¡HAS PERDIDO EL MATCH!",
        info_apuesta_vista: "Apuesta vista:",
        cartas_sin_repartir: "[Cartas sin repartir]",
        te_suben: "Te suben: ",
        has_subido: "Has subido: ",
        eres_mano: "(Eres Mano)",
        eres_postre: "(Eres Postre)",
        resultados_ronda: "Resultados de la ronda:",
        txt_mano: "Mano",
        txt_postre: "Postre",
        fase_grande: "GRANDE",
        fase_chica: "CHICA",
        fase_pares: "PARES",
        fase_juego: "JUEGO",
        fase_punto: "PUNTO",
        fase_mus: "MUS",
        msg_nadie_pares: "Nadie tiene Pares.",
        msg_no_pares: "El {rol} no tiene Pares.",
        msg_juego_a_punto: "Nadie tiene Juego. Se juega al Punto.",
        msg_no_juego: "El {rol} no tiene Juego.",
        msg_fase_descarte: "Fase: DESCARTE. Selecciona qué cartas quieres tirar.",
        msg_fase_apuestas: "Fase de {fase}. Turno de: {jugador}",
        msg_fase_recuento: "Fase de RECUENTO...",
        msg_fase_general: "Fase: {fase}. Turno de: {jugador}",
        msg_resultados: "Resultados de la ronda:",
        msg_recuento_nover: "(Alguien no quiso ver en {fase})",
        msg_recuento_gana_yo: "<b> Has </b> ganado {puntos} en {fase}.",
        msg_recuento_gana_rival: "<b>El rival ha</b> ganado {puntos} puntos en {fase}.",
        msg_recuento_pedrete_win_yo: "<b>Has</b> ganado la partida con un ¡Pedrete!",
        msg_recuento_pedrete_win_rival: "<b>El rival ha</b> ganado la partida con un ¡Pedrete!",
        msg_recuento_ordago_yo: "<b>Has</b> ganado el órdago a {fase}.",
        msg_recuento_ordago_rival: "<b>El rival ha</b> ganado el órdago a {fase}.",
        msg_error_ronda: "<em>(Hubo un error o la ronda no tuvo apuestas válidas)</em>",
        msg_gana_partida_yo: "🏆 ¡HAS GANADO ESTA PARTIDA!",
        msg_gana_partida_rival: "💀 ¡EL RIVAL HA GANADO ESTA PARTIDA!",
        msg_gana_match_yo: "🏆 ¡HAS GANADO EL MATCH!",
        msg_gana_match_rival: "💀 ¡EL RIVAL HA GANADO EL MATCH!",
        msg_fase_espera_reparto: "Esperando el reparto...",
        txt_tu_sala: "Tu sala",
        btn_unirse_publica: "Unirse",
        msg_no_publicas: "No hay partidas públicas ahora mismo. ¡Crea tú una!",
        txt_cartas_sin_repartir: "[Cartas sin repartir]",
        txt_hola: "Hola",
        // --- Salida de partida y sustituciones ---
        btn_salir_title: "Salir de la partida",
        salir_titulo: "¿Salir de la partida?",
        salir_texto: "Volverás al menú principal. Los demás jugadores podrán esperar a que otra persona ocupe tu sitio.",
        salir_texto_bot: "Volverás al menú principal y esta partida contra la IA se perderá.",
        salir_confirmar: "Sí, salir",
        salir_cancelar: "Seguir jugando",
        abandono_titulo: "Un jugador ha dejado la partida",
        abandono_texto: "{nombre} ha abandonado la partida. ¿Quieres esperar a que otra persona ocupe su sitio o prefieres salir?",
        abandono_texto_timeout: "{nombre} se ha desconectado y no ha vuelto a tiempo. ¿Quieres esperar a que otra persona ocupe su sitio o prefieres salir?",
        abandono_esperar: "Esperar a otro jugador",
        abandono_salir: "Salir yo también",
        espera_reemplazo_titulo: "Buscando un jugador…",
        espera_reemplazo_texto: "Tu partida aparece en la lista como partida en curso: cualquiera puede unirse y ocupar el hueco. El marcador se conserva y se repartirá una mano nueva.",
        espera_reemplazo_salir: "Dejarlo y volver al menú",
        espera_reemplazo_fin: "Nadie se ha unido a tiempo. Volviendo al menú principal.",
        reemplazo_encontrado: "{nombre} se une a la partida. ¡Mano nueva!",
        txt_en_curso: "En curso",
        txt_hueco_libre: "Hueco libre",
        txt_marcador: "Marcador",
        // --- Autenticación (auth.js) ---
        user_or_email: "Usuario o correo",
        email_label: "Correo electrónico",
        password_min: "Contraseña (mín. 6)",
        forgot_password: "¿Olvidaste tu contraseña?",
        o_bien: "o",
        continue_google: "Continuar con Google",
        verify_title: "Verifica tu correo",
        verify_intro: "Te hemos enviado un código de 6 dígitos. Introdúcelo para terminar el registro.",
        btn_verify: "Verificar y crear cuenta",
        forgot_title: "Recuperar contraseña",
        forgot_intro: "Introduce el correo de tu cuenta y te enviaremos un código para restablecer la contraseña.",
        btn_send_code: "Enviar código",
        reset_title: "Nueva contraseña",
        reset_intro: "Introduce el código que te hemos enviado y tu nueva contraseña.",
        btn_reset: "Cambiar contraseña",
        fill_all_fields: "Rellena todos los campos.",
        invalid_username: "El usuario debe tener 3-20 caracteres (letras, números o _).",
        invalid_email: "Introduce un correo electrónico válido.",
        invalid_password: "La contraseña debe tener al menos 6 caracteres.",
        sending_code: "Enviando código",
        code_sent: "¡Código enviado!",
        enter_full_code: "Introduce el código completo.",
        session_expired: "La sesión ha caducado, vuelve a empezar el registro.",
        verifying: "Verificando",
        account_created: "¡Cuenta creada! Iniciando sesión...",
        enter_user_pass: "Introduce usuario/correo y contraseña.",
        checking: "Comprobando",
        saving: "Guardando",
        password_changed: "Contraseña cambiada. Ya puedes iniciar sesión.",
        network_error: "Error de conexión. Inténtalo de nuevo.",
        google_error: "No se pudo iniciar sesión con Google. Inténtalo de nuevo.",
        google_sin_cuenta: "No hay ninguna cuenta ligada a ese Google. Regístrate para crear una.",
        btn_jugar_bot: "Jugar contra bot",
        txt_creando_partida_bot: "Creando partida contra un bot...",
        fase_espera_reparto: "Esperando el reparto...",
        msg_inserta_nombre: "Por favor, inserta un nombre para jugar.",
        btn_privacy: "Acerca de CallMus",
        privacy_title: "Acerca de CallMus (v0.1)",
        privacy_p1: "<strong>Información general</strong><br>CallMus es una aplicación web diseñada para jugar al tradicional juego de cartas Mus. La plataforma permite a los usuarios disfrutar de partidas multijugador contra otras personas o enfrentarse a un bot avanzado, entrenado mediante el algoritmo de aprendizaje profundo Deep CFR.",
        privacy_p2: "<strong>Desarrollo</strong><br>Este proyecto ha sido desarrollado en su totalidad por Juan Martín Fajardo. El código fuente es de código abierto y se distribuye bajo la licencia AGPL-3.0. Puedes consultar el repositorio oficial en GitHub a través del siguiente enlace: https://github.com/JuanMartinFajardo/muson_line. Para reportar errores o sugerencias, abre un Issue en el repositorio, en la pantalla de ajustes o envía un correo a callmus.contact@gmail.com.",
        privacy_p3: "<strong>Política de Privacidad y Cookies</strong><br><ul style='margin-top:5px; padding-left: 20px;'><li><strong>Datos personales:</strong> Guardamos tu nombre de usuario, correo electrónico, país y fecha de nacimiento para crear tu cuenta y mostrarte en la clasificación. <strong>Únicamente el nombre de usuario es público</strong>; tu correo solo se usa para verificar la cuenta y recuperar la contraseña.</li> <li><strong>Contraseña:</strong> No almacenamos tu contraseña, sino un hash. Si la olvidas, puedes restablecerla mediante un código enviado a tu correo.</li><li><strong>Acceso con Google:</strong> Si entras con Google, recibimos tu correo y nombre para crear o vincular tu cuenta; nunca vemos tu contraseña de Google.</li><li><strong>Registro de partidas:</strong> Guardamos el registro de las jugadas para el entrenamiento de futuras versiones del bot.</li><li><strong>Medición de audiencia:</strong> Contamos visitas, tiempo de permanencia, partidas y qué botones del menú se pulsan para saber cómo se usa el juego. La medición es <strong>propia y sin cookies</strong>: no guardamos nada en tu dispositivo para medir, no usamos servicios externos de analítica y <strong>nunca almacenamos tu dirección IP</strong> (solo se usa, junto a una clave aleatoria que cambia cada día y no se guarda, para agrupar las páginas de una misma visita). Los datos son agregados, no salen de nuestro servidor y los registros detallados se borran a los 90 días. Del botón de Ko-fi solo registramos que se ha pulsado; a partir de ahí sales a un sitio externo con su propia política, y no sabemos si donas ni cuánto.</li><li><strong>Cookies:</strong> Usamos cookies técnicas estrictamente necesarias para mantener tu sesión iniciada y recordar tu idioma. No usamos cookies de rastreo publicitario ni de analítica.</li></ul>",
        privacy_disclaimer: "Al registrarte aceptas las políticas de privacidad, que puedes encontrar en la sección Acerca de CallMus.",
        msg_link_copied: "¡Enlace copiado al portapapeles!",
        msg_nombre_invitacion: "Escribe tu nombre para entrar a la partida.",

        // --- Social (amigos, mensajería, grupos) ---
        btn_amigos: "👥 Amigos",
        tab_amigos: "Amigos",
        tab_grupos: "Grupos",
        add_friend_ph: "Añadir por nombre o #código…",
        btn_add_friend: "Añadir",
        friend_requests: "Solicitudes",
        sin_solicitudes: "No tienes solicitudes pendientes.",
        btn_aceptar: "Aceptar",
        btn_rechazar: "Rechazar",
        btn_chat: "💬 Chat",
        btn_invitar_juego: "🎮 Invitar",
        btn_eliminar_amigo: "✕",
        crear_grupo_ph: "Nombre del grupo…",
        btn_crear_grupo: "Crear grupo",
        group_leaderboard: "🏆 Clasificación del grupo",
        group_members: "Miembros",
        group_chat: "💬 Chat del grupo",
        group_invite_ph: "Invitar por usuario…",
        btn_group_invite: "Invitar",
        btn_salir_grupo: "Salir del grupo",
        chat_ph: "Escribe un mensaje…",
        btn_enviar: "Enviar",
        btn_volver: "← Volver",
        estado_online: "En línea",
        estado_offline: "Desconectado",
        sin_amigos: "Aún no tienes amigos. ¡Añade a alguien!",
        sin_grupos: "No perteneces a ningún grupo.",
        sin_mensajes: "No hay mensajes todavía. ¡Saluda!",
        sin_miembros_leaderboard: "Sin datos de clasificación todavía.",
        rol_owner: "Propietario",
        rol_admin: "Admin",
        rol_member: "Miembro",
        toast_nueva_solicitud: "Nueva solicitud de amistad de {nombre}",
        toast_amistad_aceptada: "{nombre} ha aceptado tu solicitud",
        toast_mensaje_nuevo: "Nuevo mensaje de {nombre}",
        toast_invitacion_grupo: "{nombre} te ha añadido al grupo {grupo}",
        invitacion_de: "{nombre} te invita a jugar (al mejor de {n})",
        confirm_eliminar_amigo: "¿Eliminar a {nombre} de tus amigos?",
        confirm_salir_grupo: "¿Seguro que quieres salir del grupo?",
        btn_aceptar_partida: "Aceptar",
        solicitud_enviada: "¡Solicitud enviada!",
        grupo_creado: "¡Grupo creado!",
        miembro_anadido: "¡Miembro añadido!",
        err_self: "No puedes añadirte a ti mismo.",
        err_no_existe: "Ese jugador no existe (comprueba el nombre o el código).",
        err_ya_amigos: "Ya sois amigos.",
        err_already_pending: "Solicitud ya enviada o pendiente.",
        err_blocked: "Usuario no disponible.",
        err_limite: "Has alcanzado el límite.",
        err_rate_limit: "Demasiadas peticiones. Espera un momento.",
        err_offline: "Ese amigo no está conectado ahora mismo.",
        err_no_amigo: "Solo puedes invitar a tus amigos.",
        err_nombre_grupo: "El nombre debe tener entre 3 y 40 caracteres.",
        err_ya_miembro: "Ese usuario ya está en el grupo.",
        err_generico: "Algo ha salido mal. Inténtalo de nuevo.",
        cargando_social: "Cargando…",
        // --- Gestión de grupo (roles, permisos, info clasificación) ---
        who_can_add: "Quién puede añadir:",
        policy_admins: "Solo admins",
        policy_all: "Todos los miembros",
        btn_hacer_admin: "⬆ Admin",
        btn_quitar_admin: "⬇ Quitar admin",
        btn_expulsar: "Expulsar",
        confirm_expulsar: "¿Expulsar a {nombre} del grupo?",
        group_info_expl: "La clasificación del grupo usa solo las partidas jugadas entre miembros, y únicamente las disputadas después de que ambos se unieran al grupo. El ELO y el winrate son propios del grupo y arrancan desde cero.",
        toast_rol_grupo: "Tu rol ha cambiado en el grupo {grupo}",
        toast_expulsado: "Has sido expulsado del grupo {grupo}",

        // --- Ajustes (Roadmap #22) ---
        ajustes_titulo: "⚙ Ajustes",
        ajustes_tooltip: "Ajustes",
        ajustes_idioma: "Idioma",
        ajustes_nombre_invitado: "Tu nombre en la mesa",
        ajustes_invitado_nota: "Crea una cuenta para guardar tu nombre, tu ELO y tus amigos.",
        ajustes_cambiar_username: "Cambiar nombre de usuario",
        ajustes_nuevo_username: "Nuevo nombre de usuario",
        ajustes_cambiar_email: "Cambiar correo electrónico",
        ajustes_nuevo_email: "Nuevo correo electrónico",
        ajustes_cambiar_password: "Cambiar contraseña",
        ajustes_crear_password: "Crear una contraseña",
        ajustes_password_repetir: "Repite la contraseña nueva",
        ajustes_password_actual: "Contraseña actual",
        ajustes_codigo_placeholder: "Código de 6 dígitos",
        ajustes_enviar_codigo: "Enviarme el código",
        ajustes_confirmar: "Confirmar",
        ajustes_guardar: "Guardar",
        ajustes_guardando: "Guardando…",
        ajustes_enviando: "Enviando…",
        ajustes_email_codigo_nota: "Escribe el código de 6 dígitos que hemos enviado a tu correo nuevo.",
        ajustes_sin_password_link: "Entré con Google o no tengo contraseña",
        ajustes_codigo_enviado_a: "Código enviado a {email}",
        ajustes_cuenta_google: "Entraste con Google. Al crear una contraseña podrás entrar también con tu nombre de usuario.",
        ajustes_espera_username: "Podrás volver a cambiar de nombre dentro de {dias} días.",
        ajustes_password_no_coincide: "Las dos contraseñas no coinciden.",
        ajustes_codigo_expl: "Tu identificador permanente: no cambia aunque cambies de nombre. Compártelo para que te añadan.",
        ajustes_codigo_copiar: "Pulsa para copiar",
        ajustes_codigo_copiado: "¡Copiado!",
        ajustes_eliminar_cuenta: "Eliminar mi cuenta",
        ajustes_eliminar_aviso: "Se borrarán tu correo, tus datos personales, tus amistades y tus mensajes. Tu nombre de usuario quedará libre para otro jugador; tus partidas jugadas se conservan de forma anónima, marcadas con tu código, para no alterar el historial de tus rivales. Esto no se puede deshacer.",
        ajustes_eliminar_confirmar: "Escribe tu nombre de usuario",
        ajustes_eliminar_boton: "Eliminar mi cuenta para siempre",

        // Respuestas del servidor (clave 'codigo' de /auth/cuenta/*)
        ok_username_cambiado: "Nombre de usuario actualizado.",
        ok_email_cambiado: "Correo actualizado.",
        ok_password_cambiada: "Contraseña actualizada.",
        ok_cuenta_eliminada: "Cuenta eliminada. Gracias por jugar.",
        ok_codigo_enviado: "Te hemos enviado un código.",
        err_sin_sesion: "Tienes que iniciar sesión.",
        err_sin_email: "Esta cuenta no tiene ningún correo asociado.",
        err_password_incorrecta: "La contraseña actual no es correcta.",
        err_falta_credencial: "Confirma la operación con tu contraseña.",
        err_sin_codigo: "No hay ningún código pendiente. Pide uno nuevo.",
        err_codigo_caducado: "El código ha caducado. Solicita uno nuevo.",
        err_codigo_incorrecto: "Código incorrecto.",
        err_demasiadas_solicitudes: "Demasiadas solicitudes. Inténtalo de nuevo en una hora.",
        err_username_invalido: "El usuario debe tener 3-20 caracteres (letras, números o _).",
        err_username_igual: "Ese ya es tu nombre de usuario.",
        err_username_en_uso: "Ese nombre de usuario ya está en uso.",
        err_username_espera: "Solo puedes cambiar de nombre cada {dias} días.",
        err_email_invalido: "Introduce un correo electrónico válido.",
        err_email_igual: "Ese ya es tu correo actual.",
        err_email_en_uso: "Ya existe una cuenta con ese correo.",
        err_password_corta: "La contraseña debe tener al menos 6 caracteres.",
        err_confirmacion_no_coincide: "Escribe tu nombre de usuario exactamente para confirmar.",
        err_cuenta_no_encontrada: "No hemos encontrado la cuenta.",
        err_red: "Error de conexión. Inténtalo de nuevo.",
        err_cuenta_baneada: "Esta cuenta está suspendida. Escribe a callmus.contact@gmail.com si crees que es un error.",

        // ===== Soporte y avisos del administrador (Roadmap #13) =====
        soporte_titulo: "Soporte y contacto",
        soporte_intro: "¿Has encontrado un fallo o necesitas ayuda? Escríbenos y te contestamos por aquí mismo.",
        soporte_invitado: "Necesitas una cuenta para abrir una incidencia; así podemos responderte. También puedes escribir a callmus.contact@gmail.com.",
        soporte_nuevo: "Abrir una incidencia",
        soporte_tipo: "Tipo",
        soporte_tipo_bug: "Fallo del juego",
        soporte_tipo_cuenta: "Problema con mi cuenta",
        soporte_tipo_sugerencia: "Sugerencia",
        soporte_tipo_abuso: "Denunciar a un jugador",
        soporte_tipo_otro: "Otra cosa",
        soporte_asunto: "Asunto",
        soporte_mensaje: "Cuéntanos qué ha pasado",
        soporte_enviar: "Enviar",
        soporte_enviado: "Incidencia enviada. Te avisaremos cuando haya respuesta.",
        soporte_mis_incidencias: "Mis incidencias",
        soporte_sin_incidencias: "Todavía no has abierto ninguna.",
        soporte_responder: "Escribe tu respuesta…",
        soporte_marcar_resuelto: "Dar por resuelta",
        soporte_volver: "← Volver",
        soporte_estado_abierto: "Esperando respuesta",
        soporte_estado_respondido: "Respondida",
        soporte_estado_resuelto: "Resuelta",
        soporte_autor_admin: "Equipo de CallMus",
        soporte_autor_yo: "Tú",
        soporte_rate_limit: "Has abierto demasiadas incidencias hoy. Inténtalo más tarde.",
        soporte_vacio: "Rellena el asunto y el mensaje.",
        soporte_largo: "El mensaje es demasiado largo.",
        toast_soporte_respuesta: "El equipo ha respondido a tu incidencia.",
        toast_anuncio: "Aviso de CallMus",
        anuncio_cerrar: "Entendido",
        mantenimiento_titulo: "Mantenimiento",
        ajustes_soporte: "Soporte y contacto",
        ajustes_panel_admin: "🛠 Panel de administración",
        recon_jugador_caido: "Un jugador se ha caído. Esperando a que vuelva…"
    },
    en: {
        btn_login: "Log In",
        btn_signup: "Sign Up",
        btn_logout: "Log Out",
        btn_crear: "Create new game",
        btn_unirse: "Join with code",
        btn_show_leaderboard: "View Leaderboard",
        btn_tutorial: "🎓 How to Play (Tutorial)",
        btn_deal: "Deal Cards",
        btn_nomus: "Cut",
        btn_descartar: "Discard",
        btn_next_round: "Next round",
        btn_volver_menu: "Return to Menu",
        btn_envidar: "Bid",
        btn_pasar: "Pass",
        btn_ordago: "Órdago",
        btn_ver: "Call",
        btn_subir: "Raise",
        btn_nover: "Fold",
        btn_ordago_resp: "Órdago",
        al_mejor_de: "Best of:",
        al_mejor_de_colname: "Best of",
        user_colname: "User",
        action_colname: "Action",
        public_games: "🌐 Public Games",
        esperando_rival: "Waiting for opponent to join...",
        in_publico: "Make public (visible to everyone)",
        partidas: "games",
        mi_turno: "Your turn",
        my_cards: "Your cards will appear here",
        watermark: "Created by Juan Martín Fajardo",
        login_remember: "Keep me logged in",
        leaderboard_title: "🏆 Global Leaderboard",
        elo_colname: "ELO 🔽",
        wins_colname: "Victorias ↕️",
        winrate_colname: "Winrate ↕️",
        loading_players: "Loading players...",
        codigo_sala: "Your room code:",
        tu_nombre: "Your name...",
        password: "Password",
        signup_birth: "Birthdate:",
        user_name: "Username",
        pais_nacimiento: "Country of birth",
        btn_cuenta: "Create account",
        opponent_speaks: "Opponent speaks",
        cartas_rival_ocultas: "[Opponent's cards hidden]",
        txt_tu: "You", 
        txt_pts: "Pts:",
        txt_partidas: "Games:",
        txt_rival: "Opponent",
        codigo_placeholder: "Room code...",
        btn_next_game: "Next game",
        info_tus_cartas: "Your cards will appear here",
        info_esperando_rival_descarte: "Waiting for opponent to discard...",
        info_esperando_rival_listo: "Waiting for opponent to be ready...",
        rival_siguiente_partida: "Waiting for opponent for the next game...",
        info_rival_cambio: "Opponent changed ",
        cartas: " cards",
        has_ganado_partida: "🏆 YOU WON THIS GAME!",
        el_rival_ganado_partida: "💀 YOU LOST THIS GAME!",
        has_ganado_match: "🏆 YOU WON THE MATCH!",
        el_rival_ganado_match: "💀 YOU LOST THE MATCH!",
        info_apuesta_vista: "Bet seen:",
        cartas_sin_repartir: "[Cards not dealt]",
        te_suben: "You are raised: ",
        has_subido: "You raised: ",
        eres_mano: "(You are Mano)",
        eres_postre: "(You are Postre)",
        resultados_ronda: "Results of the round:",
        txt_mano: "Mano",
        txt_postre: "Postre",
        fase_grande: "HIGH",
        fase_chica: "LOW",
        fase_pares: "PAIRS",
        fase_juego: "GAME",
        fase_punto: "POINT",
        fase_mus: "MUS",
        msg_nadie_pares: "No one has Pairs.",
        msg_no_pares: "The {rol} doesn't have Pairs.",
        msg_juego_a_punto: "No one has Game. Playing for Point.",
        msg_no_juego: "The {rol} doesn't have Game.",
        msg_fase_descarte: "Phase: DISCARD. Select which cards to throw.",
        msg_fase_apuestas: "Phase {fase}. {jugador}'s turn",
        msg_fase_espera_reparto: "Waiting for the deal...",
        msg_fase_recuento: "Phase COUNTING...",
        msg_fase_general: "Phase: {fase}. {jugador}'s turn",
        msg_resultados: "Results of the round:",
        msg_recuento_nover: "(Someone didn't want to see in {fase})",
        msg_recuento_gana_yo: "<b> You </b> won {puntos} points in {fase}.",
        msg_recuento_gana_rival: "<b>The opponent</b> won {puntos} points in {fase}.",
        msg_recuento_pedrete_win_yo: "<b>You</b> won the match with a ¡Pedrete!",
        msg_recuento_pedrete_win_rival: "<b>The opponent</b> won the match with a ¡Pedrete!",
        msg_recuento_ordago_yo: "<b>You</b> won the órdago in {fase}.",
        msg_recuento_ordago_rival: "<b>The opponent</b> won the órdago in {fase}.",
        msg_error_ronda: "<em>(There was an error or the round had no valid bets)</em>",
        msg_gana_partida_yo: "🏆 YOU WON THIS GAME!",
        msg_gana_partida_rival: "💀 THE OPPONENT WON THIS GAME!",
        msg_gana_match_yo: "🏆 YOU WON THE MATCH!",
        msg_gana_match_rival: "💀 THE OPPONENT WON THE MATCH!",
        txt_tu_sala: "Your room",
        btn_unirse_publica: "Join",
        msg_no_publicas: "There are no public games right now. Create one!",
        txt_cartas_sin_repartir: "[Cards not dealt yet]",
        txt_hola: "Hello",
        // --- Leaving a game and substitutions ---
        btn_salir_title: "Leave the game",
        salir_titulo: "Leave the game?",
        salir_texto: "You'll go back to the main menu. The other players will be able to wait for someone else to take your seat.",
        salir_texto_bot: "You'll go back to the main menu and this game against the AI will be lost.",
        salir_confirmar: "Yes, leave",
        salir_cancelar: "Keep playing",
        abandono_titulo: "A player has left the game",
        abandono_texto: "{nombre} has left the game. Do you want to wait for someone else to take their seat, or leave too?",
        abandono_texto_timeout: "{nombre} disconnected and didn't come back in time. Do you want to wait for someone else to take their seat, or leave too?",
        abandono_esperar: "Wait for another player",
        abandono_salir: "Leave as well",
        espera_reemplazo_titulo: "Looking for a player…",
        espera_reemplazo_texto: "Your game is listed as an ongoing match: anyone can join and take the empty seat. The score is kept and a fresh hand will be dealt.",
        espera_reemplazo_salir: "Give up and go back to the menu",
        espera_reemplazo_fin: "Nobody joined in time. Going back to the main menu.",
        reemplazo_encontrado: "{nombre} joins the game. New hand!",
        txt_en_curso: "Ongoing",
        txt_hueco_libre: "Seat free",
        txt_marcador: "Score",
        // --- Authentication (auth.js) ---
        user_or_email: "Username or email",
        email_label: "Email address",
        password_min: "Password (min. 6)",
        forgot_password: "Forgot your password?",
        o_bien: "or",
        continue_google: "Continue with Google",
        verify_title: "Verify your email",
        verify_intro: "We sent you a 6-digit code. Enter it to finish signing up.",
        btn_verify: "Verify and create account",
        forgot_title: "Reset password",
        forgot_intro: "Enter your account email and we'll send you a code to reset your password.",
        btn_send_code: "Send code",
        reset_title: "New password",
        reset_intro: "Enter the code we sent you and your new password.",
        btn_reset: "Change password",
        fill_all_fields: "Please fill in all fields.",
        invalid_username: "Username must be 3-20 characters (letters, numbers or _).",
        invalid_email: "Enter a valid email address.",
        invalid_password: "Password must be at least 6 characters.",
        sending_code: "Sending code",
        code_sent: "Code sent!",
        enter_full_code: "Enter the full code.",
        session_expired: "Your session expired, please start signup again.",
        verifying: "Verifying",
        account_created: "Account created! Logging you in...",
        enter_user_pass: "Enter your username/email and password.",
        checking: "Checking",
        saving: "Saving",
        password_changed: "Password changed. You can now log in.",
        network_error: "Connection error. Please try again.",
        google_error: "Could not sign in with Google. Please try again.",
        google_sin_cuenta: "No account is linked to that Google account. Sign up to create one.",
        btn_jugar_bot: "Play against bot",
        txt_creando_partida_bot: "Creating game against a bot...",
        fase_espera_reparto: "Waiting for the deal...",
        msg_inserta_nombre: "Please enter a name to play.",
        btn_privacy: "About CallMus",
        privacy_title: "About CallMus (v0.1)",
        privacy_p1: "<strong>General Information</strong><br>CallMus is a web application designed for playing the traditional Spanish card game Mus. The platform allows users to enjoy multiplayer matches against others or challenge an advanced bot trained using the Deep CFR algorithm.",
        privacy_p2: "<strong>Development</strong><br>This project has been entirely developed by Juan Martín Fajardo. The source code is open-source under the AGPL-3.0 license. Check out the official GitHub repository here: https://github.com/JuanMartinFajardo/muson_line. To report bugs or suggest improvements, please open an Issue or send a mail to callmus.contact@gmail.com.",
        privacy_p3: "<strong>Privacy and Cookie Policy</strong><br><ul style='margin-top:5px; padding-left: 20px;'><li><strong>Personal Data:</strong> We collect your username, email, country, and birthdate to manage your account and global ranking. <strong>Only your username is publicly visible</strong>; your email is used only to verify your account and reset your password.</li> <li><strong>Password:</strong> We do not store your password, only a hash. If you forget it, you can reset it via a code sent to your email.</li><li><strong>Google Sign-in:</strong> If you sign in with Google, we receive your email and name to create or link your account; we never see your Google password.</li> <li><strong>Game Logs:</strong> We store game records to train future AI versions.</li><li><strong>Audience measurement:</strong> We count visits, time spent, games played and which menu buttons are clicked to understand how the game is used. Measurement is <strong>first-party and cookieless</strong>: nothing is stored on your device for analytics, no third-party analytics service is used, and <strong>your IP address is never stored</strong> (it is only used, together with a random key that rotates daily and is never saved, to group the pages of a single visit). The data is aggregated, never leaves our server, and detailed records are deleted after 90 days. For the Ko-fi button we only record that it was clicked; from there you leave for an external site with its own policy, and we do not know whether or how much you donate.</li><li><strong>Cookies:</strong> We strictly use technical cookies essential for keeping your session active and remembering your language. We do not use tracking or analytics cookies.</li></ul>",
        privacy_disclaimer: "By signing up, you agree to the privacy policies, which you can find in the About CallMus section.",
        msg_link_copied: "Link copied to clipboard!",
        msg_nombre_invitacion: "Enter your name to join the game.",

        // --- Social (friends, messaging, groups) ---
        btn_amigos: "👥 Friends",
        tab_amigos: "Friends",
        tab_grupos: "Groups",
        add_friend_ph: "Add by name or #code…",
        btn_add_friend: "Add",
        friend_requests: "Requests",
        sin_solicitudes: "No pending requests.",
        btn_aceptar: "Accept",
        btn_rechazar: "Decline",
        btn_chat: "💬 Chat",
        btn_invitar_juego: "🎮 Invite",
        btn_eliminar_amigo: "✕",
        crear_grupo_ph: "Group name…",
        btn_crear_grupo: "Create group",
        group_leaderboard: "🏆 Group leaderboard",
        group_members: "Members",
        group_chat: "💬 Group chat",
        group_invite_ph: "Invite by username…",
        btn_group_invite: "Invite",
        btn_salir_grupo: "Leave group",
        chat_ph: "Type a message…",
        btn_enviar: "Send",
        btn_volver: "← Back",
        estado_online: "Online",
        estado_offline: "Offline",
        sin_amigos: "No friends yet. Add someone!",
        sin_grupos: "You're not in any group.",
        sin_mensajes: "No messages yet. Say hi!",
        sin_miembros_leaderboard: "No leaderboard data yet.",
        rol_owner: "Owner",
        rol_admin: "Admin",
        rol_member: "Member",
        toast_nueva_solicitud: "New friend request from {nombre}",
        toast_amistad_aceptada: "{nombre} accepted your request",
        toast_mensaje_nuevo: "New message from {nombre}",
        toast_invitacion_grupo: "{nombre} added you to group {grupo}",
        invitacion_de: "{nombre} invites you to play (best of {n})",
        confirm_eliminar_amigo: "Remove {nombre} from your friends?",
        confirm_salir_grupo: "Are you sure you want to leave the group?",
        btn_aceptar_partida: "Accept",
        solicitud_enviada: "Request sent!",
        grupo_creado: "Group created!",
        miembro_anadido: "Member added!",
        err_self: "You can't add yourself.",
        err_no_existe: "No such player (check the name or the code).",
        err_ya_amigos: "You're already friends.",
        err_already_pending: "Request already sent or pending.",
        err_blocked: "User unavailable.",
        err_limite: "You've reached the limit.",
        err_rate_limit: "Too many requests. Please wait a moment.",
        err_offline: "That friend is not online right now.",
        err_no_amigo: "You can only invite your friends.",
        err_nombre_grupo: "The name must be 3 to 40 characters.",
        err_ya_miembro: "That user is already in the group.",
        err_generico: "Something went wrong. Please try again.",
        cargando_social: "Loading…",
        // --- Group management (roles, permissions, leaderboard info) ---
        who_can_add: "Who can add:",
        policy_admins: "Admins only",
        policy_all: "All members",
        btn_hacer_admin: "⬆ Admin",
        btn_quitar_admin: "⬇ Remove admin",
        btn_expulsar: "Remove",
        confirm_expulsar: "Remove {nombre} from the group?",
        group_info_expl: "The group leaderboard uses only games played between members, and only those played after both joined the group. ELO and winrate are group-specific and start from scratch.",
        toast_rol_grupo: "Your role changed in group {grupo}",
        toast_expulsado: "You were removed from group {grupo}",

        // --- Settings (Roadmap #22) ---
        ajustes_titulo: "⚙ Settings",
        ajustes_tooltip: "Settings",
        ajustes_idioma: "Language",
        ajustes_nombre_invitado: "Your name at the table",
        ajustes_invitado_nota: "Create an account to keep your name, your ELO and your friends.",
        ajustes_cambiar_username: "Change username",
        ajustes_nuevo_username: "New username",
        ajustes_cambiar_email: "Change email address",
        ajustes_nuevo_email: "New email address",
        ajustes_cambiar_password: "Change password",
        ajustes_crear_password: "Create a password",
        ajustes_password_repetir: "Repeat the new password",
        ajustes_password_actual: "Current password",
        ajustes_codigo_placeholder: "6-digit code",
        ajustes_enviar_codigo: "Send me the code",
        ajustes_confirmar: "Confirm",
        ajustes_guardar: "Save",
        ajustes_guardando: "Saving…",
        ajustes_enviando: "Sending…",
        ajustes_email_codigo_nota: "Type the 6-digit code we sent to your new email address.",
        ajustes_sin_password_link: "I signed in with Google or have no password",
        ajustes_codigo_enviado_a: "Code sent to {email}",
        ajustes_cuenta_google: "You signed in with Google. Creating a password lets you log in with your username too.",
        ajustes_espera_username: "You will be able to change your name again in {dias} days.",
        ajustes_password_no_coincide: "The two passwords do not match.",
        ajustes_codigo_expl: "Your permanent ID: it never changes, even if you rename yourself. Share it so people can add you.",
        ajustes_codigo_copiar: "Click to copy",
        ajustes_codigo_copiado: "Copied!",
        ajustes_eliminar_cuenta: "Delete my account",
        ajustes_eliminar_aviso: "Your email, personal details, friendships and messages will be deleted. Your username is released for another player to take; the games you played are kept anonymously, tagged with your code, so your opponents' history stays intact. This cannot be undone.",
        ajustes_eliminar_confirmar: "Type your username",
        ajustes_eliminar_boton: "Delete my account permanently",

        // Server replies (the 'codigo' key from /auth/cuenta/*)
        ok_username_cambiado: "Username updated.",
        ok_email_cambiado: "Email address updated.",
        ok_password_cambiada: "Password updated.",
        ok_cuenta_eliminada: "Account deleted. Thanks for playing.",
        ok_codigo_enviado: "We've sent you a code.",
        err_sin_sesion: "You need to log in.",
        err_sin_email: "This account has no email address.",
        err_password_incorrecta: "That is not your current password.",
        err_falta_credencial: "Confirm with your password.",
        err_sin_codigo: "There is no pending code. Request a new one.",
        err_codigo_caducado: "The code has expired. Request a new one.",
        err_codigo_incorrecto: "Wrong code.",
        err_demasiadas_solicitudes: "Too many requests. Try again in an hour.",
        err_username_invalido: "Username must be 3-20 characters (letters, numbers or _).",
        err_username_igual: "That is already your username.",
        err_username_en_uso: "That username is already taken.",
        err_username_espera: "You can only change your name every {dias} days.",
        err_email_invalido: "Enter a valid email address.",
        err_email_igual: "That is already your email address.",
        err_email_en_uso: "An account with that email already exists.",
        err_password_corta: "The password must be at least 6 characters.",
        err_confirmacion_no_coincide: "Type your username exactly to confirm.",
        err_cuenta_no_encontrada: "We couldn't find the account.",
        err_red: "Connection error. Please try again.",
        err_cuenta_baneada: "This account is suspended. Write to callmus.contact@gmail.com if you think this is a mistake.",

        // ===== Support and admin announcements (Roadmap #13) =====
        soporte_titulo: "Support & contact",
        soporte_intro: "Found a bug or need a hand? Write to us and we'll reply right here.",
        soporte_invitado: "You need an account to open a ticket, so that we can reply to you. You can also write to callmus.contact@gmail.com.",
        soporte_nuevo: "Open a ticket",
        soporte_tipo: "Type",
        soporte_tipo_bug: "Game bug",
        soporte_tipo_cuenta: "Account problem",
        soporte_tipo_sugerencia: "Suggestion",
        soporte_tipo_abuso: "Report a player",
        soporte_tipo_otro: "Something else",
        soporte_asunto: "Subject",
        soporte_mensaje: "Tell us what happened",
        soporte_enviar: "Send",
        soporte_enviado: "Ticket sent. We'll let you know when there's a reply.",
        soporte_mis_incidencias: "My tickets",
        soporte_sin_incidencias: "You haven't opened any yet.",
        soporte_responder: "Write your reply…",
        soporte_marcar_resuelto: "Mark as solved",
        soporte_volver: "← Back",
        soporte_estado_abierto: "Waiting for reply",
        soporte_estado_respondido: "Answered",
        soporte_estado_resuelto: "Solved",
        soporte_autor_admin: "CallMus team",
        soporte_autor_yo: "You",
        soporte_rate_limit: "You've opened too many tickets today. Try again later.",
        soporte_vacio: "Fill in the subject and the message.",
        soporte_largo: "That message is too long.",
        toast_soporte_respuesta: "The team replied to your ticket.",
        toast_anuncio: "CallMus announcement",
        anuncio_cerrar: "Got it",
        mantenimiento_titulo: "Maintenance",
        ajustes_soporte: "Support & contact",
        ajustes_panel_admin: "🛠 Admin panel",
        recon_jugador_caido: "A player dropped. Waiting for them to return…"
    }
};

// Idiomas disponibles, en el orden en que los recorre el botón de Ajustes.
// El botón muestra SIEMPRE el siguiente de la rueda, no el actual.
const LANGS = ['es', 'en', 'eu'];
const LANG_ETIQUETA = { es: 'ES', en: 'EN', eu: 'EU' };

// Recuperar idioma guardado o usar español por defecto. Si en localStorage hay
// un idioma que ya no existe (o basura), se vuelve al español.
let langActual = localStorage.getItem('callmus_lang') || 'es';
if (!LANGS.includes(langActual)) langActual = 'es';

// Siguiente idioma de la rueda: es → en → eu → es.
function siguienteLang(lang) {
    return LANGS[(LANGS.indexOf(lang) + 1) % LANGS.length];
}

// Busca la clave en el idioma activo y, si allí no está, en castellano, que es
// el idioma completo por definición. Devuelve null si no está en ninguno: así
// aplicarTraduccion() puede distinguir «no traducido» de «cadena vacía».
// El castellano de reserva importa con tres idiomas: una clave que se añada y
// no llegue a traducirse se ve en castellano, no como el nombre de la clave.
function _resolver(clave) {
    const propio = dict[langActual] && dict[langActual][clave];
    if (propio) return propio;
    const base = dict.es && dict.es[clave];
    return base || null;
}

function t(clave) {
    // Si no está en ningún idioma devuelve la propia clave, para que se note el error.
    return _resolver(clave) || clave;
}

// Traduce e inyecta variables dinámicas en la frase
function t_dinamico(clave, variables) {
    let texto = t(clave);
    for (let prop in variables) {
        texto = texto.replace('{' + prop + '}', variables[prop]);
    }
    return texto;
}


function aplicarTraduccion() {
// 1. Traducir todos los elementos estáticos que tengan data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
        let clave = el.getAttribute('data-i18n');
        if (dict[langActual] && dict[langActual][clave]) {
            // NUEVO: Si es un campo de texto, cambiamos el placeholder
            if (el.tagName === 'INPUT') {
                el.placeholder = dict[langActual][clave];
            } else {
                el.innerHTML = dict[langActual][clave];
            }
        }
    });
    
    // 1bis. Tooltips (title="...") de los botones que solo llevan icono.
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const clave = el.getAttribute('data-i18n-title');
        if (dict[langActual] && dict[langActual][clave]) el.title = dict[langActual][clave];
    });

    // 2. El botón de idioma anuncia a cuál se saltará al pulsarlo
    const btnLang = document.getElementById('btn-lang');
    if(btnLang) btnLang.innerText = LANG_ETIQUETA[siguienteLang(langActual)];

    // 3. El atributo lang del documento, para el navegador y los lectores de
    //    pantalla (y para que la tipografía elija bien las reglas de guionado).
    document.documentElement.setAttribute('lang', langActual);
}

// Escuchador del botón: recorre la rueda de idiomas
document.getElementById('btn-lang').addEventListener('click', () => {
    langActual = siguienteLang(langActual);
    localStorage.setItem('callmus_lang', langActual); // Guardar preferencia
    aplicarTraduccion(); // Traducir todo al vuelo
});

// Ejecutar la primera vez que carga la web
aplicarTraduccion();


// ==========================================
// PANTALLA COMPLETA
// ==========================================
// Vive en static/pantalla.js, que además congela la página mientras se juega
// («modo mesa») y explica el caso del iPhone, donde Safari no tiene la API.
// Aquí sólo queda la nota para no volver a montar otro botón por su cuenta.

// Quitar el foco de cualquier botón tras hacer clic para evitar que se quede "atascado" (marcado en blanco)
document.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (btn) btn.blur();
});


// ==========================================
// 1. LÓGICA DEL MENÚ Y SALAS
// ==========================================

const btnCrear = document.getElementById('btn-crear');
const btnUnirse = document.getElementById('btn-unirse');
const inCodigo = document.getElementById('in-codigo');
const menuMsg = document.getElementById('menu-msg');

/** Escapa un texto que va a viajar dentro de innerHTML. Los nombres de mesa los
 *  escribe cualquiera sin registrarse, así que no pueden entrar en crudo en las
 *  listas de partidas ni en la clasificación (misma regla que social.js). */
function escHtml(texto) {
    return String(texto == null ? '' : texto).replace(/[&<>"']/g, c => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
}

/** Los avisos tienen dos casas: el menú y la ventana de Jugar, que tapa el menú
 *  mientras está abierta. Se escribe en las dos para que el jugador lea el aviso
 *  esté donde esté (antes solo existía #menu-msg, invisible tras un modal). */
function menuMensaje(texto, color) {
    [menuMsg, document.getElementById('play-msg')].forEach(el => {
        if (!el) return;
        el.innerText = texto || '';
        el.style.color = color || '';
    });
}

socket.emit('pedir_publicas');

btnCrear.addEventListener('click', () => {
    miNombre = document.getElementById('nombre-jugador').value.trim();
    if (!miNombre) {
        menuMensaje(t('msg_inserta_nombre'));
        return;
    }
    localStorage.setItem('callmus_nombre', miNombre);
    let mejorDe = parseInt(document.getElementById('in-mejor-de').value) || 3;
    let esPublico = document.getElementById('in-publico').checked;
    socket.emit('crear_sala', { nombre: miNombre, al_mejor_de: mejorDe, publico: esPublico});
    btnCrear.disabled = true;
    btnUnirse.disabled = true;
    menuMensaje(t('msg_creando_sala'));
});

const btnJugarBot = document.getElementById('btn-jugar-bot');

btnJugarBot.addEventListener('click', () => {
    miNombre = document.getElementById('nombre-jugador').value.trim() || "Jugador 1";
    let mejorDe = parseInt(document.getElementById('in-mejor-de').value) || 3;

    // Emitimos un nuevo evento específico para el bot
    esPartidaContraBot = true;
    socket.emit('crear_partida_bot', { nombre: miNombre, al_mejor_de: mejorDe });

    btnCrear.disabled = true;
    btnUnirse.disabled = true;
    btnJugarBot.disabled = true;
    menuMensaje(t('txt_creando_partida_bot'));
});



btnUnirse.addEventListener('click', () => {
    miNombre = document.getElementById('nombre-jugador').value.trim();
    if (!miNombre) {
        menuMensaje(t('msg_inserta_nombre'));
        return;
    }
    let cod = inCodigo.value.trim().toUpperCase();
    if (!cod) {
        menuMensaje(t('msg_escribe_codigo'));
        return;
    }
    localStorage.setItem('callmus_nombre', miNombre);
    localStorage.setItem('callmus_sala', cod);
    socket.emit('unirse_sala', { nombre: miNombre, codigo: cod });
    menuMensaje(t('msg_conectando'));
});

document.getElementById('btn-volver-menu').addEventListener('click', () => {
    enPartida = false;
    localStorage.removeItem('callmus_sala');
    localStorage.removeItem('callmus_token');   // salida voluntaria: no reconectar
    socket.emit('abandonar_sala_limpiamente');
    setTimeout(() => { window.location.reload(); }, 100);
});


// ==========================================
// SALIDA DE PARTIDA Y SUSTITUCIONES
// Overlays compartidos: app4.js reutiliza estas funciones para el 2v2, así que
// todo lo que hay aquí es agnóstico del modo (el "qué emitir" lo pone quien llama).
// ==========================================
const ovSalir = document.getElementById('overlay-salir');
const ovAbandono = document.getElementById('overlay-abandono');
const ovEspera = document.getElementById('overlay-espera-reemplazo');

let _accionSalir = null;        // callback del overlay de confirmación
let _accionEsperar = null;      // callbacks del overlay de abandono
let _accionSalirAbandono = null;
let _accionSalirEspera = null;
let _esperaInterval = null;

function ocultarOverlaysPartida() {
    [ovSalir, ovAbandono, ovEspera].forEach(o => o && o.classList.add('hidden'));
    clearInterval(_esperaInterval);
    _esperaInterval = null;
}

/** Confirmación previa a abandonar. `onConfirm` solo se ejecuta si el jugador acepta. */
function confirmarSalidaPartida(texto, onConfirm) {
    document.getElementById('overlay-salir-texto').innerText = texto || t('salir_texto');
    _accionSalir = onConfirm;
    ovSalir.classList.remove('hidden');
}

/** Alguien se fue: preguntamos si esperamos sustituto o nos vamos también.
 *  `texto` permite al 2v2 dar su propia redacción (nombra el asiento vacante). */
function mostrarAvisoAbandono({ nombre, motivo, onEsperar, onSalir, texto }) {
    const clave = motivo === 'timeout' ? 'abandono_texto_timeout' : 'abandono_texto';
    document.getElementById('overlay-abandono-texto').innerText =
        texto || t_dinamico(clave, { nombre: nombre || '...' });
    _accionEsperar = onEsperar;
    _accionSalirAbandono = onSalir;
    ovEspera.classList.add('hidden');
    ovAbandono.classList.remove('hidden');
}

/** La partida se anuncia buscando sustituto: overlay con cuenta atrás.
 *  `opciones.texto` sustituye la explicación por defecto (el 2v2 añade cuántos faltan). */
function mostrarEsperaReemplazo(segundos, onSalir, opciones) {
    _accionSalirEspera = onSalir;
    ovAbandono.classList.add('hidden');
    ovEspera.classList.remove('hidden');
    document.getElementById('overlay-espera-texto').innerText =
        (opciones && opciones.texto) || t('espera_reemplazo_texto');
    const cont = document.getElementById('overlay-espera-cont');
    clearInterval(_esperaInterval);
    let restante = Math.max(0, parseInt(segundos) || 0);
    const pinta = () => {
        const m = Math.floor(restante / 60);
        const s = restante % 60;
        cont.innerText = m + ':' + String(s).padStart(2, '0');
    };
    pinta();
    _esperaInterval = setInterval(() => {
        restante -= 1;
        pinta();
        if (restante <= 0) { clearInterval(_esperaInterval); _esperaInterval = null; }
    }, 1000);
}

function ocultarEsperaReemplazo() {
    ovEspera.classList.add('hidden');
    clearInterval(_esperaInterval);
    _esperaInterval = null;
}

document.getElementById('btn-salir-cancelar').addEventListener('click', () => {
    ovSalir.classList.add('hidden');
    _accionSalir = null;
});
document.getElementById('btn-salir-confirmar').addEventListener('click', () => {
    ovSalir.classList.add('hidden');
    const cb = _accionSalir;
    _accionSalir = null;
    if (cb) cb();
});
document.getElementById('btn-abandono-esperar').addEventListener('click', () => {
    ovAbandono.classList.add('hidden');
    if (_accionEsperar) _accionEsperar();
});
document.getElementById('btn-abandono-salir').addEventListener('click', () => {
    ovAbandono.classList.add('hidden');
    if (_accionSalirAbandono) _accionSalirAbandono();
});
document.getElementById('btn-espera-salir').addEventListener('click', () => {
    ocultarEsperaReemplazo();
    if (_accionSalirEspera) _accionSalirEspera();
});

// --- Cableado del modo 1v1 / vs IA ---
function salirDePartida2p() {
    enPartida = false;
    ocultarOverlaysPartida();
    localStorage.removeItem('callmus_sala');
    localStorage.removeItem('callmus_token');   // salida voluntaria: no reconectar
    socket.emit('abandonar_partida');
    setTimeout(() => { window.location.reload(); }, 150);
}

document.getElementById('btn-salir-partida').addEventListener('click', () => {
    confirmarSalidaPartida(esPartidaContraBot ? t('salir_texto_bot') : t('salir_texto'),
                           salirDePartida2p);
});

// El rival se fue (o agotó su ventana de reconexión): esperar o salir.
socket.on('jugador_abandono', (d) => {
    if (!enPartida) return;
    ocultarOverlayReconexion();
    mostrarAvisoAbandono({
        nombre: (d && d.nombre) || '...',
        motivo: d && d.motivo,
        onEsperar: () => socket.emit('esperar_reemplazo'),
        onSalir: salirDePartida2p,
    });
});

// Aceptamos esperar: la partida ya sale anunciada en la lista pública.
socket.on('esperando_reemplazo', (d) => {
    if (!enPartida) return;
    mostrarEsperaReemplazo((d && d.segundos) || 0, salirDePartida2p);
});

// Alguien ocupó el hueco: se reanuda con marcador intacto y mano nueva.
socket.on('reemplazo_encontrado', (d) => {
    ocultarOverlaysPartida();
    if (enPartida && d && d.nombre) mostrarToastPartida(t_dinamico('reemplazo_encontrado', { nombre: d.nombre }));
});

function mostrarToastPartida(texto) {
    const toast = document.getElementById('social-toast');
    if (!toast) return;
    toast.innerText = texto;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3500);
}

window.addEventListener('beforeunload', (e) => {
    if (enPartida) {
        e.preventDefault();
        e.returnValue = '';
    }
});

socket.on('sala_creada', (datos) => {
    // La sala pasa a ser la única vista de la ventana de Jugar: se guarda el
    // formulario y se muestra el código a compartir.
    const setup = document.getElementById('play-setup');
    if (setup) setup.classList.add('hidden');
    document.getElementById('codigo-creado').classList.remove('hidden');
    document.getElementById('txt-codigo').innerText = datos.codigo;
    if (typeof marcarEsperaPlay === 'function') marcarEsperaPlay(true);
    menuMensaje("");
    localStorage.setItem('callmus_sala', datos.codigo);
    if (datos.token) localStorage.setItem('callmus_token', datos.token);  // reconexión
    btnCrear.disabled = true;
    btnUnirse.disabled = true;
});

socket.on('error_sala', (datos) => {
    menuMensaje(datos.mensaje);
    // Si la sala se creó y luego falló, se vuelve al formulario.
    const setup = document.getElementById('play-setup');
    if (setup) setup.classList.remove('hidden');
    document.getElementById('codigo-creado').classList.add('hidden');
    btnCrear.disabled = false;
    btnUnirse.disabled = false;
    localStorage.removeItem('callmus_sala');
    localStorage.removeItem('callmus_token');   // token viejo inservible
});

// Dibujar la lista de partidas públicas (dentro de la ventana de Jugar)
socket.on('actualizar_publicas', (lista) => {
    const tbody = document.getElementById('lista-partidas-publicas');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (lista.length === 0) {
        tbody.innerHTML = `<tr><td colspan="2" class="cm-live-empty">${t('msg_no_publicas')}</td></tr>`;
        return;
    }

    lista.forEach(partida => {
        const tr = document.createElement('tr');

        // SISTEMA ROBUSTO: Es nuestra sala si el ID de conexión es el nuestro,
        // o si estamos logueados y la sala pertenece a nuestra misma cuenta.
        let esMiSala = false;
        if (partida.creador_sid === socket.id) esMiSala = true;
        if (miUsernameLogueado && partida.creador_username === miUsernameLogueado) esMiSala = true;

        // Partida EN CURSO con hueco: se anuncia con el marcador que heredarías.
        let etiqueta = '';
        let meta = t_dinamico('live_mejor_de', { n: partida.al_mejor_de });
        if (partida.en_curso) {
            tr.className = 'fila-en-curso';
            etiqueta = `<span class="badge-en-curso">${t('txt_en_curso')}</span>`;
            if (partida.marcador) {
                meta += ` · ${t('txt_marcador')} ${partida.marcador[0]}-${partida.marcador[1]}`;
            }
        }

        tr.innerHTML = `
            <td>
                <span class="cm-live-name">${escHtml(partida.creador)}</span>${etiqueta}
                <span class="cm-live-meta">${meta}</span>
            </td>
            <td class="cm-live-cell-act">
                <button class="btn-unirse-publica cm-live-join${esMiSala ? ' es-mia' : ''}" data-codigo="${partida.codigo}">
                    ${esMiSala ? t('txt_tu_sala') : t('btn_unirse_publica')}
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    // Darle funcionalidad a los botones generados
    tbody.querySelectorAll('.btn-unirse-publica').forEach(btn => {
        btn.addEventListener('click', () => {
            let cod = btn.getAttribute('data-codigo');
            miNombre = document.getElementById('nombre-jugador').value.trim();
            if (!miNombre) {
                menuMensaje(t('msg_inserta_nombre'));
                return;
            }
            localStorage.setItem('callmus_nombre', miNombre); // <--- AÑADIR
            localStorage.setItem('callmus_sala', cod);
            socket.emit('unirse_sala', { nombre: miNombre, codigo: cod });
            menuMensaje(t('msg_conectando'));
        });
    });
});

socket.on('iniciar_partida', (datos) => {
    // La ventana de Jugar se cierra y queda lista para la próxima: antes vivía
    // dentro del menú y desaparecía con él; ahora es un modal y hay que bajarlo
    // a mano (si no, la sala creada se queda flotando sobre la mesa).
    cerrarModales();
    document.getElementById('codigo-creado').classList.add('hidden');
    const setup = document.getElementById('play-setup');
    if (setup) setup.classList.remove('hidden');
    if (typeof marcarEsperaPlay === 'function') marcarEsperaPlay(false);

    menuScreen.classList.add('hidden');
    gameScreen.classList.remove('hidden');
    enPartida = true;
});


document.getElementById('btn-show-privacy').addEventListener('click', () => {
    abrirModal('modal-privacy');
});

socket.on('rival_desconectado', (d) => {
    if (enPartida) {
        ocultarOverlayReconexion();
        ocultarOverlaysPartida();
        alert((d && d.motivo === 'sin_reemplazo')
            ? t('espera_reemplazo_fin')
            : "Tu rival se ha desconectado o ha abandonado la partida. Volviendo al menú principal.");
        enPartida = false;
        localStorage.removeItem('callmus_sala');
        localStorage.removeItem('callmus_token');
        window.location.reload();
    }
});

// ==========================================
// Reconexión 2p / vs-IA: pausa por caída del rival + reenganche automático.
// ==========================================
let _reconInterval = null;
function mostrarOverlayReconexion(segundos) {
    const ov = document.getElementById('overlay-reconexion');
    const msg = document.getElementById('overlay-reconexion-msg');
    const cont = document.getElementById('overlay-reconexion-cont');
    if (!ov) return;
    msg.innerText = t('recon_jugador_caido');
    ov.classList.remove('hidden');
    clearInterval(_reconInterval);
    if (segundos && segundos > 0) {
        let restante = segundos;
        cont.innerText = restante + 's';
        _reconInterval = setInterval(() => {
            restante -= 1;
            cont.innerText = (restante > 0 ? restante : 0) + 's';
            if (restante <= 0) clearInterval(_reconInterval);
        }, 1000);
    } else {
        cont.innerText = '';
    }
}
function ocultarOverlayReconexion() {
    const ov = document.getElementById('overlay-reconexion');
    if (ov) ov.classList.add('hidden');
    clearInterval(_reconInterval);
}

// El rival (o yo, si reconecto con el rival aún fuera) sigue caído: mostramos aviso.
socket.on('oponente_desconectado', (d) => {
    if (!enPartida) return;
    mostrarOverlayReconexion((d && d.gracia) || 0);
});
socket.on('oponente_reconectado', () => ocultarOverlayReconexion());

// Nos reengancharon a la partida en curso: volvemos a la mesa (el estado la repinta).
socket.on('reanudado', () => {
    menuScreen.classList.add('hidden');
    gameScreen.classList.remove('hidden');
    enPartida = true;
    const msgEl = document.getElementById('menu-msg');
    if (msgEl) msgEl.innerText = "";
});

// ==========================================
// 2. ACCIONES DE JUEGO AL SERVIDOR
// ==========================================

document.getElementById('btn-deal').addEventListener('click', () => {
    mostrarBotones([]);
    socket.emit('accion_juego', { accion: 'repartir' });
});

document.getElementById('btn-pedrete').addEventListener('click', () => {
    mostrarBotones([]);
    socket.emit('accion_juego', { accion: 'pedrete' });
});


document.getElementById('btn-mus').addEventListener('click', () => {
    mostrarBotones([]);
    socket.emit('accion_juego', { accion: 'mus' });
});

document.getElementById('btn-nomus').addEventListener('click', () => {
    mostrarBotones([]);
    socket.emit('accion_juego', { accion: 'no_mus' });
});

document.getElementById('btn-descartar').addEventListener('click', () => {
    mostrarBotones([]);
    socket.emit('accion_juego', { accion: 'descartar', indices: cartasSeleccionadas });
});

['pasar', 'ver', 'nover', 'ordago', 'ordago-resp'].forEach(id => {
    let el = document.getElementById('btn-' + id);
    if(el) el.addEventListener('click', () => {
        mostrarBotones([]);
        let accion = id === 'ordago-resp' ? 'ordago' : id;
        socket.emit('accion_juego', { accion: accion });
    });
});

document.getElementById('btn-envidar').addEventListener('click', () => {
    mostrarBotones([]);
    let cant = parseInt(document.getElementById('in-envidar').value) || 2;
    let misPuntos = parseInt(document.getElementById('puntos-mios').innerText) || 0;
    if (cant > 40 - misPuntos) cant = 40 - misPuntos;
    socket.emit('accion_juego', { accion: 'envidar', cantidad: cant });
});

document.getElementById('btn-subir').addEventListener('click', () => {
    mostrarBotones([]);
    let cant = parseInt(document.getElementById('in-subir').value) || 2;
    let misPuntos = parseInt(document.getElementById('puntos-mios').innerText) || 0;
    let tope = 40 - misPuntos - apuestaVistaActual;
    if (cant > tope) cant = tope;
    if (cant < 1) cant = 1;
    if (cant > 40 - misPuntos) cant = 40 - misPuntos;
    socket.emit('accion_juego', { accion: 'subir', cantidad: cant });
});

document.getElementById('btn-next-round').addEventListener('click', (e) => {
    clearTimeout(recuentoTimeout);
    mostrarBotones([]);
    document.getElementById('my-cards').innerHTML = '';
    const contenedorRival = document.querySelector('#opponent-area .cards-placeholder');
    if (contenedorRival) contenedorRival.innerHTML = '';

    let textoEspera = e.target.innerText === "Siguiente partida"
        ? `${t('rival_siguiente_partida')}`
        : `${t('info_esperando_rival_listo')}`;

    gameLog.innerHTML = `<strong style='font-size: 1.2em; color: #ffffff; font-weight: 300; letter-spacing: 1px;'>${textoEspera}</strong>`;
    socket.emit('accion_juego', { accion: 'listo_siguiente_ronda' });
});

// ==========================================
// 3. RECIBIR ESTADO DEL JUEGO
// ==========================================

// La zona del rival, en un sitio solo: sus cuatro dorsos mientras se juega y
// sus cartas al descubierto en el recuento. Todo con SU baraja (Roadmap #5),
// que llega en el estado y puede cambiar en plena partida, así que también se
// repinta desde el aviso `baraja_rival` con el último estado recibido.
function pintarCartasRival(datos) {
    const cont = document.querySelector('#opponent-area .cards-placeholder');
    if (!cont || !datos) return;

    if (datos.fase === 'espera_reparto') {
        cont.innerHTML = `${t('txt_cartas_sin_repartir')}`;
        return;
    }

    if (datos.fase === 'recuento') {
        cont.innerHTML = '';
        (datos.cartas_rival || []).forEach(c => {
            const d = document.createElement('div');
            d.className = 'carta';
            d.innerHTML = `<img src="${imgCarta(c, barajaRival)}" alt="${c.texto}" draggable="false" oncontextmenu="return false;">`;
            cont.appendChild(d);
        });
        return;
    }

    const dorso = `<div class="carta"><img src="${imgDorso(barajaRival)}" draggable="false" oncontextmenu="return false;"></div>`;
    cont.innerHTML = dorso.repeat(4);
}

// El rival ha cambiado de baraja sin levantarse de la mesa.
socket.on('baraja_rival', (d) => {
    if (!d || !d.config) return;
    barajaRival = d.config;
    if (window.Barajas) window.Barajas.precargarAjena(barajaRival);
    if (enPartida) pintarCartasRival(ultimoEstadoMesa);
});

socket.on('actualizar_mesa', (datos) => {
    // 1. FILTRO: Si el paquete no es para mí, lo ignoro
    if (datos.para_sid !== socket.id) return;

    // La baraja del rival, antes de pintar nada suyo.
    if (datos.baraja_rival) {
        barajaRival = datos.baraja_rival;
        if (window.Barajas) window.Barajas.precargarAjena(barajaRival);
    }
    ultimoEstadoMesa = datos;

    // Token de reconexión: nos aseguramos de tenerlo siempre guardado (invitado incl.).
    if (datos.reconexion_token) localStorage.setItem('callmus_token', datos.reconexion_token);

    clearTimeout(recuentoTimeout);
    
    // 2. CHIVATO: Esto imprimirá los datos en la consola si por fin llegan
   
    if (show_in_console) {
        console.log("📥 Datos recibidos del servidor:", datos);
    }

    if (!enPartida) {
        document.getElementById('menu-screen').classList.add('hidden');
        document.getElementById('game-screen').classList.remove('hidden');
        enPartida = true;
    }
    
    if (datos.nombre_rival) {
        document.getElementById('nombre-rival-ui').innerText = datos.nombre_rival;
    }

    faseJuego = datos.fase;

    pintarCartasRival(datos);

    const logDiv = document.getElementById('betting-log');
    if (datos.fase === 'apuestas' || datos.fase === 'recuento') {
        logDiv.classList.remove('hidden');

        let fAct = datos.apuestas ? datos.apuestas.fase_actual : '';
            if (datos.mensaje_transicion && datos.mensaje_transicion.fase) {
                fAct = datos.mensaje_transicion.fase;
            }

        if (datos.fase === 'apuestas' && fAct !== subfaseApuestasActual) {
            subfaseApuestasActual = fAct;
            document.getElementById('in-envidar').value = 2;
            document.getElementById('in-subir').value = 2;
        }

        // La apuesta en el aire: si no hay ninguna, la caja se queda vacía y el
        // CSS la colapsa (antes reservaba 65px de hueco muerto).
        let htmlApuestaEnAire = '<div id="caja-en-aire" class="cm-aire">';

        if (datos.apuestas && (datos.apuestas.subida > 0 || datos.apuestas.subida === 'ÓRDAGO')) {
            const cantidadStr = datos.apuestas.subida === 'ÓRDAGO' ? t('un_ordago') : datos.apuestas.subida;
            const textoSube = datos.apuestas.soy_quien_sube ? t('has_subido') + cantidadStr : t('te_suben') + cantidadStr;

            htmlApuestaEnAire += `
                <p class="cm-aire-vista">${t('info_apuesta_vista')} <b>${datos.apuestas.apuesta_vista}</b></p>
                <p class="cm-aire-sube${datos.apuestas.soy_quien_sube ? ' es-mia' : ''}">${textoSube}</p>
            `;
        }
        htmlApuestaEnAire += '</div>';

        logDiv.innerHTML = htmlApuestaEnAire + htmlTanteador(datos.apuestas, fAct, (fase, ap) => {
            const deje = ap.dejes && ap.dejes[fase];
            return deje ? { valor: deje.valor, gano: deje.gano_yo } : null;
        });
    } else {
        if (logDiv) logDiv.classList.add('hidden');
    }

    if (datos.mensaje_transicion) {
        // NUEVO: Traducir transición dinámica
        let textoTrans = "";
        if (datos.mensaje_transicion.code === 'no_pares' || datos.mensaje_transicion.code === 'no_juego') {
            let rolTrad = datos.mensaje_transicion.rol === 'mano' ? t('txt_mano') : t('txt_postre');
            textoTrans = t_dinamico('msg_' + datos.mensaje_transicion.code, { rol: rolTrad });
        } else {
            textoTrans = t('msg_' + datos.mensaje_transicion.code);
        }
        
        gameLog.innerHTML = `<strong class="cm-transicion">${textoTrans}</strong>`;
        mostrarBotones([]);
        if (datos.es_mi_turno) {
            setTimeout(() => socket.emit('accion_juego', { accion: 'continuar_transicion' }), 3000);
        }
        return;
    }

    if (datos.fase === 'recuento') {
        document.getElementById('apuesta-iniciar').classList.add('hidden');
        document.getElementById('apuesta-responder').classList.add('hidden');
        const cajaEnAire = document.getElementById('caja-en-aire');
        if (cajaEnAire) cajaEnAire.classList.add('hidden');
        mostrarRecuentoEstatico(datos);
        return;
    }

    // Guardamos la selección anterior si seguimos en la fase de descarte y aún no nos hemos descartado
    let seleccionAnterior = [];
    if (datos.fase === 'descarte' && !datos.descartes_listos) {
        seleccionAnterior = [...cartasSeleccionadas];
    }

    cartasSeleccionadas = [];
    const btnDescartar = document.getElementById('btn-descartar');
    if(btnDescartar) btnDescartar.innerText = `${t('btn_descartar')} (0)`;

    const contenedorCartas = document.getElementById('my-cards');
    contenedorCartas.innerHTML = '';

    if (datos.mis_cartas && datos.mis_cartas.length > 0) {
        datos.mis_cartas.forEach((carta, index) => {
            const div = document.createElement('div');
            div.className = 'carta';
            div.innerHTML = `<img src="${imgCarta(carta)}" alt="${carta.texto}" draggable="false" oncontextmenu="return false;">`;

            if (seleccionAnterior.includes(index)) {
                cartasSeleccionadas.push(index);
                div.classList.add('seleccionada');
            }

            div.onclick = () => {
                if (datos.fase === 'descarte' && !datos.descartes_listos) {
                    const pos = cartasSeleccionadas.indexOf(index);
                    if (pos === -1) {
                        cartasSeleccionadas.push(index);
                        div.classList.add('seleccionada');
                    } else {
                        cartasSeleccionadas.splice(pos, 1);
                        div.classList.remove('seleccionada');
                    }
                    btnDescartar.innerText = `${t('btn_descartar')} (${cartasSeleccionadas.length})`;
                    btnDescartar.disabled = cartasSeleccionadas.length === 0;
                }
            };
            contenedorCartas.appendChild(div);
        });
        
        if (btnDescartar && cartasSeleccionadas.length > 0) {
            btnDescartar.innerText = `${t('btn_descartar')} (${cartasSeleccionadas.length})`;
        }
    } else {
        contenedorCartas.innerHTML = `${t('info_tus_cartas')}`;
    }

    document.getElementById('puntos-mios').innerText = datos.mis_puntos;
    document.getElementById('puntos-rival').innerText = datos.puntos_rival;
    document.getElementById('mi-rol').innerText = datos.soy_mano ? t('eres_mano') : t('eres_postre');
    document.getElementById('mi-turno').classList.toggle('hidden', !datos.es_mi_turno);
    document.getElementById('turno-rival').classList.toggle('hidden', datos.es_mi_turno);

    apuestaVistaActual = datos.apuestas ? datos.apuestas.apuesta_vista : 0;

    // Calculamos el tope real teniendo en cuenta también los puntos del rival
    let ptsMaximos = Math.max(datos.mis_puntos, datos.puntos_rival);
    let maxApuesta = 40 - ptsMaximos;
    
    let inEnvidar = document.getElementById('in-envidar');
    let inSubir = document.getElementById('in-subir');

    if (inEnvidar) inEnvidar.max = maxApuesta > 0 ? maxApuesta : 1;
    if (inSubir) {
        let topeSubida = maxApuesta - apuestaVistaActual;
        inSubir.max = topeSubida > 0 ? topeSubida : 1;
    }

    if(document.getElementById('partidas-mios')) {
        pintarPiedras(document.getElementById('partidas-mios'), datos.mis_partidas, datos.al_mejor_de);
        pintarPiedras(document.getElementById('partidas-rival'), datos.partidas_rival, datos.al_mejor_de);
        alMejorDeActual = datos.al_mejor_de;
        document.querySelectorAll('.mejor-de-texto').forEach(el => el.innerText = `${t('al_mejor_de')} ${datos.al_mejor_de }`);
    }

    if (datos.fase === 'descarte' && datos.descartes_listos) {
        gameLog.innerText = `${t('info_esperando_rival_descarte')}`;
    } else {
        
        let textoMsg = "";
        if (datos.mensaje) {
            if (datos.mensaje.code === 'fase_apuestas' || datos.mensaje.code === 'fase_general') {
                //let nombreFaseTraducida = t('fase_' + datos.mensaje.fase.toLowerCase());
                //textoMsg = t_dinamico('msg_' + datos.mensaje.code, { fase: nombreFaseTraducida, jugador: datos.mensaje.jugador });
                // Deliberately hidden so the table area isn't pushed down by repetitive text
                textoMsg = "";
            } else {
                textoMsg = t('msg_' + datos.mensaje.code);
            }
        }
        
        gameLog.innerText = textoMsg;

        if (datos.descartes_rival > 0 && datos.fase === 'mus') {
            gameLog.innerHTML += `<br><span class="cm-nota-mesa">(${t('info_rival_cambio')} ${datos.descartes_rival} ${t('cartas')})</span>`;
        }
    }

    mostrarBotones([]);
    document.getElementById('apuesta-iniciar').classList.add('hidden');
    document.getElementById('apuesta-responder').classList.add('hidden');

    // Creamos una cesta de botones
    let botonesActivos = [];

    // 1. El pedrete es el rey. Si lo tienes, el botón aparece siempre, sea el turno que sea.
    if (datos.puede_pedrete) {
        botonesActivos.push('btn-pedrete');
    }

    // 2. Lógica normal del resto de fases
    if (datos.fase === 'descarte') {
        if (!datos.descartes_listos) {
            botonesActivos.push('btn-descartar');
            document.getElementById('btn-descartar').disabled = cartasSeleccionadas.length === 0;
        } else {
            document.getElementById('btn-descartar').disabled = true;
        }
        
    } else if (datos.es_mi_turno) {
        if (datos.fase === 'espera_reparto') {
            botonesActivos.push('btn-deal');
            
        } else if (datos.fase === 'mus') {
            botonesActivos.push('btn-mus', 'btn-nomus');
            
        } else if (datos.fase === 'apuestas' && datos.apuestas) {
            
            // Hacemos visible el contenedor principal de botones
            document.getElementById('action-buttons').classList.remove('hidden');

            if (datos.apuestas.subida === 0) {
                // --- FASE 1: INICIAR APUESTA (Nadie ha apostado, subida es 0) ---
                document.getElementById('apuesta-iniciar').classList.remove('hidden');
                
            } else {
                // --- FASE 2: RESPONDER APUESTA (Alguien ya ha envidado/subido) ---
                document.getElementById('apuesta-responder').classList.remove('hidden');

                let esOrdago = datos.apuestas.subida === 'ÓRDAGO';
                
                // Calculamos el total de puntos que ya están en juego en esta fase si se acepta
                let totalApuestaActual = datos.apuestas.apuesta_vista + (esOrdago ? 0 : datos.apuestas.subida);
                
                // Si esos puntos ya hacen que tú o el rival paséis de 40, la subida numérica ya no tiene sentido
                let yaPasaDe40 = (datos.mis_puntos + totalApuestaActual >= 40 || datos.puntos_rival + totalApuestaActual >= 40);

                // Ocultamos la subida numérica (input y botón) si ya es Órdago o si ya se cubren los 40 puntos
                let ocultarSubirNumerico = esOrdago || yaPasaDe40;
                document.getElementById('in-subir').classList.toggle('hidden', ocultarSubirNumerico);
                document.getElementById('btn-subir').classList.toggle('hidden', ocultarSubirNumerico);
                
                // El botón de Órdago de respuesta solo se oculta si la apuesta ya era un Órdago
                document.getElementById('btn-ordago-resp').classList.toggle('hidden', esOrdago);

                // --- Ocultar "No ver" si el deje le da la partida al rival ---
                let deje = datos.apuestas.apuesta_vista > 0 ? datos.apuestas.apuesta_vista : 1;
                let obligadoAVer = (datos.puntos_rival + deje >= 40);
                document.getElementById('btn-nover').classList.toggle('hidden', obligadoAVer);
            }
        }
    }

    // 3. Mostramos todos los botones de la cesta a la vez
    if (botonesActivos.length > 0) {
        mostrarBotones(botonesActivos);
    }
});

// ==========================================
// 4. UTILIDADES VISUALES
// ==========================================

/**
 * Tanteador de lances: Grande · Chica · Pares · Juego en cuatro columnas con el
 * lance en curso en oro (ver .cm-botes en static/game.css). Lo comparten la
 * mesa de 1v1 y la de 2v2 (table4.js lo llama con su propio lector de dejes).
 *
 * @param {object}   apuestas   bloque `apuestas` del estado del servidor.
 * @param {string}   faseActual lance que se está jugando ('Grande', 'Chica'…).
 * @param {Function} dejeDe     (fase, apuestas) → {valor, gano} | null. El deje
 *                              de ese lance, si alguien no quiso ver; cada mesa
 *                              lo mira a su manera (gano_yo / gano_mi_equipo).
 */
function htmlTanteador(apuestas, faseActual, dejeDe) {
    const ap = apuestas || {};
    const lances = [
        ['Grande', t('fase_grande')],
        ['Chica',  t('fase_chica')],
        ['Pares',  t('fase_pares')],
        ['Juego',  ap.juego_es_punto ? t('fase_punto') : t('fase_juego')],
    ];

    let html = '<div class="cm-botes">';
    lances.forEach(([clave, etiqueta]) => {
        const deje = dejeDe(clave, ap);
        let valor;
        if (deje) {
            const signo = deje.gano
                ? '<span class="cm-bote-signo es-mas">+</span>'
                : '<span class="cm-bote-signo es-menos">−</span>';
            valor = deje.valor + signo;
        } else {
            valor = (ap.botes && ap.botes[clave]) || 0;
        }
        const clases = 'cm-bote'
            + (faseActual === clave ? ' is-activa' : '')
            + (deje ? ' es-deje' : '');
        html += `<div class="${clases}">`
              + `<span class="cm-bote-fase">${etiqueta}</span>`
              + `<span class="cm-bote-val">${valor}</span>`
              + `</div>`;
    });
    return html + '</div>';
}

/**
 * Las piedras (los amarrakos de toda la vida): una por cada partida que hace
 * falta para llevarse el match, rellenas de oro las ya ganadas. Sustituye al
 * viejo contador "Partidas: 2" en las chapas de las dos mesas.
 */
function pintarPiedras(el, ganadas, alMejorDe) {
    if (!el) return;
    const necesarias = Math.floor((parseInt(alMejorDe, 10) || 1) / 2) + 1;
    const ganadasNum = parseInt(ganadas, 10) || 0;
    let html = '';
    for (let i = 0; i < necesarias; i++) {
        html += `<span class="piedra${i < ganadasNum ? ' es-ganada' : ''}"></span>`;
    }
    el.innerHTML = html;
    el.setAttribute('title', `${ganadasNum} / ${necesarias}`);
}

function mostrarBotones(ids) {
    const contenedor = document.getElementById('action-buttons');
    const allIds = ['btn-deal', 'btn-pedrete', 'btn-mus', 'btn-nomus', 'btn-descartar', 'btn-next-round','btn-volver-menu'];
    allIds.forEach(id => {
        let el = document.getElementById(id);
        if(el) el.classList.add('hidden');
    });
    if (ids.length > 0) {
        contenedor.classList.remove('hidden');
        ids.forEach(id => {
            let el = document.getElementById(id);
            if(el) el.classList.remove('hidden');
        });
        // El centro de la mesa tiene scroll propio: en pantallas bajas el
        // recuento puede empujar los botones fuera de la vista, así que los
        // acercamos siempre (block:'nearest' sólo mueve lo imprescindible).
        contenedor.scrollIntoView({ block: 'nearest' });
    } else {
        contenedor.classList.add('hidden');
    }
}

function mostrarRecuentoEstatico(datos) {
    mostrarBotones([]);

    // En el recuento no habla nadie: apagamos los dos avisos de turno (si no, la
    // chapa se queda marcada en oro como si te tocara).
    document.getElementById('mi-turno').classList.add('hidden');
    document.getElementById('turno-rival').classList.add('hidden');

    // Las cartas del rival ya las ha puesto boca arriba `pintarCartasRival`,
    // que se llama al recibir el estado.

    if(document.getElementById('partidas-mios')) {
        const mejorDe = datos.al_mejor_de || alMejorDeActual;
        pintarPiedras(document.getElementById('partidas-mios'), datos.mis_partidas, mejorDe);
        pintarPiedras(document.getElementById('partidas-rival'), datos.partidas_rival, mejorDe);
    }

    const gameLog = document.getElementById('game-log');
    let baseHtml = `<strong class="cm-res-title">${t('msg_resultados')}</strong><br>`;
    gameLog.innerHTML = baseHtml;

    let mensajes = [];
    let ptMios = datos.mis_puntos;
    let ptRival = datos.puntos_rival;

    // Calculamos los puntos iniciales restando los ganados en el recuento
    if (datos.recuento && datos.recuento.length > 0) {
        for (let paso of datos.recuento) {
            let pts = 0;
            if (paso.datos.code === 'recuento_gana') pts = paso.datos.puntos || 0;
            else if (paso.datos.code === 'recuento_ordago') pts = 40;
            
            if (paso.gano_yo) ptMios -= pts;
            else ptRival -= pts;
        }
    }
    
    // Evitamos negativos por seguridad
    ptMios = Math.max(0, ptMios);
    ptRival = Math.max(0, ptRival);

    // Inicializamos la vista con los puntos de antes de la fase de recuento
    document.getElementById('puntos-mios').innerText = ptMios;
    document.getElementById('puntos-rival').innerText = ptRival;

    if (datos.recuento && datos.recuento.length > 0) {
        for (let paso of datos.recuento) {
            let code = paso.datos.code;
            
            if (code === 'recuento_nover') {
                if (paso.datos.fase !== 'Grande' && paso.datos.fase !== 'Chica') {
                    let nombreFase = t('fase_' + paso.datos.fase.toLowerCase());
                    mensajes.push({ texto: `<i>${t_dinamico('msg_recuento_nover', {fase: nombreFase})}</i><br>`, puntos: 0 });
                }
            } else if (code === 'recuento_gana') {
                let nombreFase = t('fase_' + paso.datos.fase.toLowerCase());
                let claveGana = paso.gano_yo ? 'msg_recuento_gana_yo' : 'msg_recuento_gana_rival';
                mensajes.push({ texto: `${t_dinamico(claveGana, {puntos: paso.datos.puntos, fase: nombreFase})}<br>`, gano_yo: paso.gano_yo, puntos: paso.datos.puntos });
                
            } else if (code === 'recuento_pedrete_win') {
                let claveGana = paso.gano_yo ? 'msg_recuento_pedrete_win_yo' : 'msg_recuento_pedrete_win_rival';
                mensajes.push({ texto: `${t(claveGana)}<br>`, puntos: 0 });
            } else if (code === 'recuento_ordago') {
                let nombreFase = t('fase_' + paso.datos.fase.toLowerCase());
                let claveGana = paso.gano_yo ? 'msg_recuento_ordago_yo' : 'msg_recuento_ordago_rival';
                mensajes.push({ texto: `${t_dinamico(claveGana, {fase: nombreFase})}<br>`, gano_yo: paso.gano_yo, puntos: 40 });
            }
        }
    } else {
        if (datos.mis_puntos >= 40 || datos.puntos_rival >= 40) {
             // Solo mostramos el mensaje de victoria/derrota
        } else {
             mensajes.push({ texto: `${t('msg_error_ronda')}<br>`, puntos: 0 });
        }
    }

    let btnNext = document.getElementById('btn-next-round');
    let botonesFinales = [];

    // Comprobar victorias de partida o match
    if (datos.mis_puntos >= 40 || datos.puntos_rival >= 40) {
        const txt = datos.mis_puntos >= 40 ? t('msg_gana_partida_yo') : t('msg_gana_partida_rival');
        mensajes.push({ texto: `<br><strong class="cm-res-big">${txt}</strong>`, puntos: 0 });
        
        if (datos.match_finalizado) {
            const txtGlobal = datos.mis_puntos >= 40 ? t('msg_gana_match_yo') : t('msg_gana_match_rival');
            mensajes.push({ texto: `<br><strong class="cm-res-big">${txtGlobal}</strong>`, puntos: 0 });
            botonesFinales = ['btn-volver-menu'];
        } else {
            if (btnNext) btnNext.innerText = t("btn_next_game"); 
            botonesFinales = ['btn-next-round'];
        }
    } else {
        if (btnNext) btnNext.innerText = t("btn_next_round");
        botonesFinales = ['btn-next-round'];
    }

    let index = 0;
    function mostrarSiguienteMensaje() {
        if (index < mensajes.length) {
            let msgObj = mensajes[index];
            gameLog.innerHTML += msgObj.texto;
            
            // Sumamos los puntos visualmente en ese momento
            if (msgObj.puntos > 0) {
                if (msgObj.gano_yo) {
                    ptMios = Math.min(40, ptMios + msgObj.puntos);
                    document.getElementById('puntos-mios').innerText = ptMios;
                } else {
                    ptRival = Math.min(40, ptRival + msgObj.puntos);
                    document.getElementById('puntos-rival').innerText = ptRival;
                }
            }

            index++;
            if (index < mensajes.length) {
                recuentoTimeout = setTimeout(mostrarSiguienteMensaje, 2000);
            } else {
                mostrarBotones(botonesFinales);
            }
        } else {
            mostrarBotones(botonesFinales);
        }
    }

    if (mensajes.length > 0) {
        mostrarSiguienteMensaje();
    } else {
        mostrarBotones(botonesFinales);
    }
}

// ==========================================
// 5. USUARIOS, MODALES Y FETCH
// ==========================================

const modalOverlay = document.getElementById('modal-overlay');
const modalLogin = document.getElementById('modal-login');
const modalSignup = document.getElementById('modal-signup');

/** Abre un modal dejando cerrados todos los demás (incluida la ventana de Jugar). */
function abrirModal(id) {
    cerrarModales();
    modalOverlay.style.display = 'flex';
    modalOverlay.classList.remove('hidden');
    const m = document.getElementById(id);
    if (m) m.classList.remove('hidden');
}

document.getElementById('btn-show-login').addEventListener('click', () => {
    abrirModal('modal-login');
    document.getElementById('msg-login').innerText = "";
});

document.getElementById('btn-show-signup').addEventListener('click', () => {
    abrirModal('modal-signup');
    document.getElementById('msg-signup').innerText = "";
});

document.querySelectorAll('.btn-cerrar-modal').forEach(btn => {
    btn.addEventListener('click', cerrarModales);
});

modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) cerrarModales();
});

function cerrarModales() {
    modalOverlay.style.display = 'none';
    modalOverlay.classList.add('hidden');
    modalLogin.classList.add('hidden');
    modalSignup.classList.add('hidden');
    
    const modalLeaderboard = document.getElementById('modal-leaderboard');
    if (modalLeaderboard) modalLeaderboard.classList.add('hidden');
    
    const modalPrivacy = document.getElementById('modal-privacy');
    if (modalPrivacy) modalPrivacy.classList.add('hidden');

    const modalSocial = document.getElementById('modal-social');
    if (modalSocial) modalSocial.classList.add('hidden');

    const modalSettings = document.getElementById('modal-settings');
    if (modalSettings) modalSettings.classList.add('hidden');

    // Ventana de Jugar (1v1 y 2v2). Sólo se oculta: si había una sala esperando,
    // al volver a abrirla se sigue viendo su código (ver abrirPlay en menu.js).
    const modalPlay = document.getElementById('modal-play');
    if (modalPlay) modalPlay.classList.add('hidden');

    // Modales de autenticación añadidos (verificación / recuperación) y el de
    // barajas (Roadmap #5).
    ['modal-verify', 'modal-forgot', 'modal-reset', 'modal-decks'].forEach(id => {
        const m = document.getElementById(id);
        if (m) m.classList.add('hidden');
    });
}
let miUsernameLogueado = null; // NUEVO: Variable para recordar quiénes somos
// La lógica de autenticación (sesión, registro, login, logout, recuperación y
// Google) vive ahora en static/auth.js, que se carga después de este archivo.
// Comparte con app.js: miUsernameLogueado, actualizarInterfazLogueado, cerrarModales, t().

// ==========================================
// 6. LÓGICA DE LA LEADERBOARD
// ==========================================

const modalLeaderboard = document.getElementById('modal-leaderboard');
let leaderboardData = [];
let currentSort = 'elo';
let sortDesc = true;

if (document.getElementById('btn-show-leaderboard')) {
    document.getElementById('btn-show-leaderboard').addEventListener('click', () => {
        abrirModal('modal-leaderboard');
        cargarLeaderboard();
    });
}

function cargarLeaderboard() {
    document.getElementById('lista-leaderboard-body').innerHTML =
        `<tr><td colspan="5" class="cm-live-empty">${t('loading_players')}</td></tr>`;

    fetch('/api/leaderboard').then(res => res.json()).then(datos => {
        if (datos.exito) {
            leaderboardData = datos.leaderboard;
            currentSort = 'elo';
            sortDesc = true;
            renderLeaderboard();
        }
    });
}

function renderLeaderboard() {
    const tbody = document.getElementById('lista-leaderboard-body');
    tbody.innerHTML = '';

    leaderboardData.sort((a, b) => {
        let valA = a[currentSort];
        let valB = b[currentSort];
        if (valA < valB) return sortDesc ? 1 : -1;
        if (valA > valB) return sortDesc ? -1 : 1;
        return 0;
    });

    // Cabeceras: la columna ordenada lleva la flecha y se pinta en oro (.is-sorted).
    const flecha = (col) => (currentSort === col ? (sortDesc ? ' ↓' : ' ↑') : '');
    [['th-sort-elo', 'elo', 'lb_elo'],
     ['th-sort-wins', 'victorias', 'lb_wins'],
     ['th-sort-winrate', 'winrate', 'lb_winrate']].forEach(([id, col, clave]) => {
        const th = document.getElementById(id);
        if (!th) return;
        th.innerText = t(clave) + flecha(col);
        th.classList.toggle('is-sorted', currentSort === col);
    });

    if (leaderboardData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="cm-live-empty">${t('lb_vacia')}</td></tr>`;
        return;
    }

    leaderboardData.forEach((jugador, index) => {
        const tr = document.createElement('tr');
        const podio = (currentSort === 'elo' && sortDesc && index < 3);

        // El código de jugador ya no se enseña bajo el nombre: se guarda en el
        // botón y sólo aparece un instante al pulsarlo (data-codigo abajo).
        tr.innerHTML = `
            <td class="cm-td-rank${podio ? ' es-podio' : ''}">${index + 1}</td>
            <td class="cm-td-name">
                <button class="lb-name" data-nombre="${escHtml(jugador.username)}"
                        data-codigo="${escHtml(jugador.codigo || '')}">${escHtml(jugador.username)}</button>
            </td>
            <td class="cm-td-elo">${jugador.elo}</td>
            <td class="cm-td-num">${jugador.victorias}</td>
            <td class="cm-td-num">${jugador.winrate}%</td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.lb-name').forEach(btn => {
        btn.addEventListener('click', () => mostrarCodigoJugador(btn));
    });
}

/** Enseña el código público del jugador durante unos segundos y vuelve al nombre. */
let _codigoVisibleTimeout = null;
function mostrarCodigoJugador(btn) {
    const codigo = btn.getAttribute('data-codigo');
    const nombre = btn.getAttribute('data-nombre');
    if (!codigo || btn.classList.contains('es-codigo')) return;

    clearTimeout(_codigoVisibleTimeout);
    // Si había otro código a la vista, se cierra antes de abrir este.
    document.querySelectorAll('.lb-name.es-codigo').forEach(otro => {
        otro.innerText = otro.getAttribute('data-nombre');
        otro.classList.remove('es-codigo');
    });

    btn.innerText = '#' + codigo;
    btn.classList.add('es-codigo');
    _codigoVisibleTimeout = setTimeout(() => {
        btn.innerText = nombre;
        btn.classList.remove('es-codigo');
    }, 2600);
}

document.getElementById('th-sort-elo').addEventListener('click', () => {
    if (currentSort === 'elo') sortDesc = !sortDesc;
    else { currentSort = 'elo'; sortDesc = true; }
    renderLeaderboard();
});

document.getElementById('th-sort-wins').addEventListener('click', () => {
    if (currentSort === 'victorias') sortDesc = !sortDesc;
    else { currentSort = 'victorias'; sortDesc = true; }
    renderLeaderboard();
});

document.getElementById('th-sort-winrate').addEventListener('click', () => {
    if (currentSort === 'winrate') sortDesc = !sortDesc;
    else { currentSort = 'winrate'; sortDesc = true; }
    renderLeaderboard();
});

// ==========================================
// 7. EFECTOS VISUALES (HOVER CARTAS)
// ==========================================
const myCardsContainer = document.getElementById('my-cards');
let zoomTimeout;

if (myCardsContainer) {
    myCardsContainer.addEventListener('mouseenter', () => {
        // Solo ampliamos en PC, si no es fase descarte y si hay cartas repartidas
        if (window.innerWidth > 768 && faseJuego !== 'descarte' && myCardsContainer.children.length > 0) {
            myCardsContainer.classList.add('cartas-ampliadas');
            clearTimeout(zoomTimeout);
            zoomTimeout = setTimeout(() => {
                myCardsContainer.classList.remove('cartas-ampliadas');
            }, 3000); // Se dejan de ampliar automáticamente a los 3 segundos
        }
    });
    myCardsContainer.addEventListener('mouseleave', () => {
        clearTimeout(zoomTimeout);
        myCardsContainer.classList.remove('cartas-ampliadas');
    });
}

// Lógica de ampliación para las cartas del rival (SOLO en recuento)
const oppCardsContainer = document.querySelector('#opponent-area .cards-placeholder');
let zoomTimeoutOpp;

if (oppCardsContainer) {
    oppCardsContainer.addEventListener('mouseenter', () => {
        // Solo ampliamos en PC, si es fase recuento y hay cartas dibujadas (no texto)
        if (window.innerWidth > 768 && faseJuego === 'recuento' && oppCardsContainer.children.length > 0) {
            if (oppCardsContainer.querySelector('.carta')) {
                oppCardsContainer.classList.add('cartas-ampliadas-rival');
                clearTimeout(zoomTimeoutOpp);
                zoomTimeoutOpp = setTimeout(() => {
                    oppCardsContainer.classList.remove('cartas-ampliadas-rival');
                }, 3000); // Auto-cierre a los 3 segundos al igual que las nuestras
            }
        }
    });
    oppCardsContainer.addEventListener('mouseleave', () => {
        clearTimeout(zoomTimeoutOpp);
        oppCardsContainer.classList.remove('cartas-ampliadas-rival');
    });
}


// ==========================================
// SISTEMA DE INVITACIONES
// ==========================================

// 1. Leer la URL al abrir la página por si venimos de un enlace
const urlParams = new URLSearchParams(window.location.search);
const urlRoom = urlParams.get('room');

if (urlRoom) {
    // Si entramos con enlace, lo guardamos para que el sistema de auto-reconexión lo pille
    localStorage.setItem('callmus_sala', urlRoom.toUpperCase());

    // Rellenamos la casilla del código visualmente por si acaso
    const codInput = document.getElementById('in-codigo');
    if (codInput) codInput.value = urlRoom.toUpperCase();

    // menu.js todavía no existe cuando esto se ejecuta: le dejamos el código
    // aquí para que abra la ventana de Jugar con el hueco ya rellenado.
    window.__cmSalaInvitacion = urlRoom.toUpperCase();

    // Limpiamos la URL para que no quede fea en el navegador
    window.history.replaceState({}, document.title, window.location.pathname);

    // Si NO está logueado y NO tiene nombre guardado, le pedimos amablemente el nombre
    setTimeout(() => {
        if (!miUsernameLogueado && !localStorage.getItem('callmus_nombre')) {
            document.getElementById('nombre-jugador').focus();
            menuMensaje(t('msg_nombre_invitacion'));
        } else {
            // Si ya tiene nombre, forzamos que intente unirse
            document.getElementById('btn-unirse').click();
        }
    }, 600); // Esperamos a que la sesión haya cargado
}

// 2. Funciones de los botones de compartir
document.getElementById('btn-share-copy').addEventListener('click', () => {
    const cod = document.getElementById('txt-codigo').innerText;
    const link = window.location.origin + "/?room=" + cod;
    
    navigator.clipboard.writeText(link).then(() => {
        menuMensaje(t('msg_link_copied'), '#8FA76B');
    });
});

document.getElementById('btn-share-wa').addEventListener('click', () => {
    const cod = document.getElementById('txt-codigo').innerText;
    const link = window.location.origin + "/?room=" + cod;
    
    // Texto predefinido para WhatsApp
    const mensaje = encodeURIComponent(`🃏 ¡Únete a mi partida de Mus en CallMus!\nCódigo de sala: ${cod}\n\nEntra directo aquí: ${link}`);
    window.open(`https://api.whatsapp.com/send?text=${mensaje}`, '_blank');
});

document.getElementById('btn-share-api').addEventListener('click', () => {
    const cod = document.getElementById('txt-codigo').innerText;
    const link = window.location.origin + "/?room=" + cod;
    
    // Esto abre el menú nativo de compartir del móvil (iOS/Android)
    if (navigator.share) {
        navigator.share({
            title: 'CallMus - Partida Privada',
            text: `¡Únete a mi partida de Mus! Código: ${cod}`,
            url: link
        }).catch(err => console.log('Compartir cancelado', err));
    } else {
        alert("Tu navegador no soporta el menú de compartir nativo. Usa el botón de copiar.");
    }
});



// ==========================================
// AUTO-RECONEXIÓN MÁGICA
// ==========================================
socket.on('connect', () => {
    // Este evento es a prueba de balas: solo se dispara cuando
    // la conexión con el servidor está 100% establecida y lista.

    // Si hay una sesión 4p activa, que la gestione app4.js (su propio 'connect').
    if (localStorage.getItem('callmus4_codigo')) return;

    const salaGuardada = localStorage.getItem('callmus_sala');
    const nombreGuardado = localStorage.getItem('callmus_nombre');
    const tokenGuardado = localStorage.getItem('callmus_token');

    if (!salaGuardada || enPartida) return;

    // Con token → estábamos en plena partida: reenganche por identidad (2p/vs-IA).
    if (tokenGuardado) {
        menuMensaje(t('msg_reconectando'), '#918E84');
        console.log(`🔌 Reanudando partida ${salaGuardada} con token.`);
        socket.emit('reanudar_partida', { codigo: salaGuardada, token: tokenGuardado });
        return;
    }

    // Sin token → sala en espera (aún no arrancó): reclamamos el asiento.
    if (nombreGuardado) {
        menuMensaje(t('msg_reconectando'), '#918E84');
        console.log(`🔌 Conexión establecida. Reclamando sala oculta: ${salaGuardada}`);
        socket.emit('unirse_sala', { nombre: nombreGuardado, codigo: salaGuardada });
    }
});