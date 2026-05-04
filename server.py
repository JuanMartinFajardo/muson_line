from flask import Flask, render_template, request, session, jsonify
import base_datos
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string
from mus_mecanicas import PartidaMus

app = Flask(__name__, static_folder='static', template_folder='.')
app.config['SECRET_KEY'] = 'clave_secreta_mus'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- NUEVA ARQUITECTURA MULTIJUGADOR ---
# jugadores = { 'sid': {'nombre': 'Juan', 'sala': 'A1B2'} }
jugadores = {}  
# salas = { 'A1B2': {'estado': 'esperando', 'sids': [sid1, sid2], 'motor': PartidaMus} }
salas = {}      

show_global_log = False 

def generar_codigo():
    letras = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letras) for _ in range(4))

@app.route('/')
def index():
    return render_template('index.html')


# ==========================================
# GESTIÓN DE USUARIOS Y SESIONES (Vía HTTP)
# ==========================================


@app.route('/api/leaderboard', methods=['GET'])
def api_leaderboard():
    datos = base_datos.obtener_leaderboard()
    return jsonify({'exito': True, 'leaderboard': datos})


@app.route('/auth/registro', methods=['POST'])
def auth_registro():
    datos = request.json
    exito, msg = base_datos.registrar_usuario(datos.get('username'), datos.get('password'), datos.get('country'), datos.get('birthdate'))
    return jsonify({'exito': exito, 'mensaje': msg})

@app.route('/auth/login', methods=['POST'])
def auth_login():
    datos = request.json
    user = datos.get('username')
    
    if base_datos.verificar_login(user, datos.get('password')):
        session.permanent = datos.get('remember', False)
        session['username'] = user
        return jsonify({'exito': True})
        
    return jsonify({'exito': False, 'mensaje': 'Usuario o contraseña incorrectos'})

@app.route('/auth/sesion', methods=['GET'])
def auth_sesion():
    if 'username' in session:
        user = session['username']
        usuario_data = base_datos.obtener_usuario(user)
        if usuario_data:
            return jsonify({'exito': True, 'usuario': usuario_data})
    return jsonify({'exito': False})

@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    session.pop('username', None)
    return jsonify({'exito': True})



# --- 1. GESTIÓN DE SALAS ---

def emitir_lista_publicas():
    """Recopila las salas públicas que están esperando y las manda a todos los conectados"""
    lista = []
    for cod, info in salas.items():
        if info['estado'] == 'esperando' and info.get('publico', False):
            creador_sid = info['sids'][0] if info['sids'] else None
            nombre = jugadores[creador_sid]['nombre'] if creador_sid in jugadores else "Desconocido"
            creador_username = info.get('username')

            lista.append({
                'codigo': cod,
                'creador': nombre,
                'creador_sid': creador_sid,
                'creador_username': creador_username,
                'al_mejor_de': info.get('al_mejor_de', 3)
            })
    socketio.emit('actualizar_publicas', lista)

@socketio.on('pedir_publicas')
def handle_pedir_publicas():
    emitir_lista_publicas()


# aqui iba el anteriorgestion de usuarios y sesiones


@socketio.on('crear_sala')
def handle_crear_sala(datos):
    sid = request.sid
    nombre = datos.get('nombre', 'Jugador 1')
    es_publico = datos.get('publico', False)
    al_mejor_de_valor = datos.get('al_mejor_de', 3)
    
    # Como ya está importado en la línea 1, lo usamos directamente
    real_username = session.get('username')

    codigo = generar_codigo()
    while codigo in salas:
        codigo = generar_codigo()
        
    # AQUÍ ESTABA EL FALLO: Ahora sí guardamos tu username en tus datos de conexión
    jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': real_username}
    join_room(codigo) 
    
    salas[codigo] = {'estado': 'esperando', 'sids': [sid], 'al_mejor_de': al_mejor_de_valor, 'publico': es_publico, 'username': real_username}
    
    print(f"👉 {nombre} ha creado la sala {codigo} (Pública: {es_publico})")
    emit('sala_creada', {'codigo': codigo}, room=sid)
    emitir_lista_publicas()

@socketio.on('unirse_sala')
def handle_unirse_sala(datos):
    sid = request.sid
    nombre = datos.get('nombre', 'Jugador 2')
    codigo = datos.get('codigo', '').upper()
    
    if codigo in salas and salas[codigo]['estado'] == 'esperando':
        creador_sid = salas[codigo]['sids'][0]
        
        # Leemos los usernames sin importar nada nuevo
        mi_username = session.get('username')
        creador_username = salas[codigo].get('username') # Lo leemos de la sala directamente (más seguro)
        
        # --- BLOQUEO 1: Es la misma pestaña exacta (Mismo SID) ---
        if sid == creador_sid:
            emit('error_sala', {'mensaje': 'No puedes unirte a tu propia sala.'}, room=sid)
            return
            
        # --- BLOQUEO 2: Es la misma cuenta logueada (En dos pestañas distintas) ---
        if mi_username and creador_username and mi_username == creador_username:
            emit('error_sala', {'mensaje': 'No puedes jugar contra ti mismo.'}, room=sid)
            return

        # Si supera los bloqueos, lo unimos con normalidad
        salas[codigo]['sids'].append(sid)
        salas[codigo]['estado'] = 'jugando'
        
        # Añadimos el username al que se une
        jugadores[sid] = {'nombre': nombre, 'sala': codigo, 'username': mi_username}
        join_room(codigo)
        
        print(f"👉 {nombre} se ha unido a la sala {codigo}. ¡Arrancamos!")
        
        # Instanciamos el motor de Mus para esta sala
        j1_sid = salas[codigo]['sids'][0]
        j2_sid = sid
        partida = PartidaMus(j1_sid, j2_sid)

        #Le pasamos los nombres reales para el log
        partida.nombres_ia = {
            j1_sid: creador_username if creador_username else jugadores[j1_sid]['nombre'],
            j2_sid: mi_username if mi_username else jugadores[j2_sid]['nombre']
        }
        partida.al_mejor_de = salas[codigo].get('al_mejor_de', 3)
        partida.iniciar_ronda()
        salas[codigo]['motor'] = partida
        
        emit('iniciar_partida', {'mensaje': '¡La partida comienza!'}, room=codigo)
        enviar_estado_a_jugadores(codigo)
        emitir_lista_publicas()
    else:
        emit('error_sala', {'mensaje': 'El código no existe o la sala está llena.'}, room=sid)

# --- 2. ACCIONES DE JUEGO AISLADAS ---

@socketio.on('accion_juego')
def handle_accion_juego(datos):
    sid_jugador = request.sid
    if sid_jugador not in jugadores: return
    
    codigo = jugadores[sid_jugador]['sala']
    if codigo not in salas or salas[codigo]['estado'] != 'jugando': return
    
    # Extraemos el motor específico de la sala donde está este jugador
    partida_actual = salas[codigo]['motor']
    accion = datos.get('accion')
    
    if accion == 'pedrete':
        if partida_actual.procesar_pedrete(sid_jugador):
            enviar_estado_a_jugadores(codigo)
        return


    if sid_jugador == partida_actual.turno_de:
        if accion == 'repartir':
            partida_actual.repartir_inicial()
            enviar_estado_a_jugadores(codigo)
        elif accion == 'mus':
            partida_actual.cantar_mus(sid_jugador, True)
            enviar_estado_a_jugadores(codigo)
        elif accion == 'no_mus':
            partida_actual.cantar_mus(sid_jugador, False)
            enviar_estado_a_jugadores(codigo)
        elif accion in ['pasar', 'envidar', 'subir', 'ver', 'ordago', 'nover']:
            cantidad = datos.get('cantidad', 0)
            partida_actual.accion_apuesta(sid_jugador, accion, cantidad)
            enviar_estado_a_jugadores(codigo)

    if accion == 'descartar' and partida_actual.fase == 'descarte':
        if not partida_actual.estado[sid_jugador]['descartes_listos']:
            indices_a_tirar = datos.get('indices', [])
            partida_actual.procesar_descarte(sid_jugador, indices_a_tirar)
            enviar_estado_a_jugadores(codigo)

    if accion == 'continuar_transicion':
        partida_actual.mensaje_transicion = None
        partida_actual.preparar_subfase() 
        enviar_estado_a_jugadores(codigo)
        
    elif accion == 'listo_siguiente_ronda':
        if getattr(partida_actual, 'match_finalizado', False):
            return 
            
        if sid_jugador not in partida_actual.jugadores_listos:
            partida_actual.jugadores_listos.append(sid_jugador)
            
        if len(partida_actual.jugadores_listos) == 2:
            if partida_actual.estado[partida_actual.j1]['puntos'] >= 40 or partida_actual.estado[partida_actual.j2]['puntos'] >= 40:
                partida_actual.reiniciar_partida()
                partida_actual.db_registrada = False
            else:
                partida_actual.cambiar_roles() 
                partida_actual.iniciar_ronda() 
                partida_actual.fase = 'espera_reparto'
                partida_actual.turno_de = partida_actual.id_postre
            
            partida_actual.jugadores_listos = []
            partida_actual.recuento_calculado = False
            enviar_estado_a_jugadores(codigo)

# --- 3. REPARTO CIEGO POR SALA ---

def enviar_estado_a_jugadores(codigo_sala):
    puede_pedrete_ahora = False
    global show_global_log
    sala = salas.get(codigo_sala)
    if not sala: return
    partida_actual = sala['motor']
        
    for sid in sala['sids']:
        estado_del_jugador = partida_actual.estado[sid]
        es_mi_turno = (sid == partida_actual.turno_de)
        soy_mano = (sid == partida_actual.id_mano)
        rival_sid = partida_actual.id_postre if sid == partida_actual.id_mano else partida_actual.id_mano
        
        if partida_actual.fase == 'descarte':
            mensaje = {'code': 'fase_descarte'}
        elif partida_actual.fase == 'apuestas':
            if partida_actual.indice_fase < len(partida_actual.fases_apuesta):
                n_fase = partida_actual.fases_apuesta[partida_actual.indice_fase]
                nombre_turno = jugadores[partida_actual.turno_de]['nombre']
                mensaje = {'code': 'fase_apuestas', 'fase': n_fase, 'jugador': nombre_turno}
            else:
                mensaje = {'code': 'fase_recuento'}
        else:
            nombre_turno = jugadores[partida_actual.turno_de]['nombre'] if partida_actual.turno_de else "..."
            mensaje = {'code': 'fase_general', 'fase': partida_actual.fase, 'jugador': nombre_turno}
        
        info_apuestas = {
            'fase_actual': '',
            'subida': partida_actual.subida_pendiente,
            'botes': partida_actual.botes,
            'apuesta_vista': partida_actual.apuesta_vista,
            'soy_quien_sube': (partida_actual.quien_sube == sid)
        }
        if partida_actual.fase == 'apuestas' and partida_actual.indice_fase < len(partida_actual.fases_apuesta):
            info_apuestas['fase_actual'] = partida_actual.fases_apuesta[partida_actual.indice_fase]
        
        datos_recuento = None
        cartas_rival = partida_actual.estado[rival_sid]['cartas']

        puede_pedrete_ahora = False
        if partida_actual.fase == 'mus':
            vals = sorted([c['valor'] for c in estado_del_jugador['cartas']])
            if vals == [4, 5, 6, 7]:
                puede_pedrete_ahora = True


        if partida_actual.fase == 'recuento':
            pasos_crudos = partida_actual.calcular_recuento()

            # Si alguien acaba de ganar la partida y aún no lo hemos registrado
            if getattr(partida_actual, 'partida_sumada', False) and not getattr(partida_actual, 'db_registrada', False):
                partida_actual.db_registrada = True # Ponemos el seguro para no sumar el premio dos veces
                import base_datos
                
                # Detectamos quién es el ganador
                if partida_actual.estado[partida_actual.j1]['puntos'] >= 40:
                    ganador_sid, perdedor_sid = partida_actual.j1, partida_actual.j2
                else:
                    ganador_sid, perdedor_sid = partida_actual.j2, partida_actual.j1
                    
                u_ganador = jugadores.get(ganador_sid, {}).get('username')
                u_perdedor = jugadores.get(perdedor_sid, {}).get('username')
                if u_ganador or u_perdedor:
                    base_datos.registrar_partida_completa(u_ganador, u_perdedor)

            # ... Y preparamos el recuento bonito para el cliente

            datos_recuento = []
            for paso in pasos_crudos:
                gano_yo = (paso['ganador_sid'] == sid)
                sujeto = "Has" if gano_yo else "El rival ha"
                if paso['texto_fase'].startswith('('):
                    datos_recuento.append(f"<i>{paso['texto_fase']}</i>")
                else:
                    datos_recuento.append(f"<b>{sujeto}</b> {paso['texto_fase']}")

        if show_global_log:
            print(f"📤 [SALA {codigo_sala}] Estado a {jugadores[sid]['nombre']}: Fase {partida_actual.fase}")

        emit('actualizar_mesa', {
            'fase': partida_actual.fase,
            'puede_pedrete': puede_pedrete_ahora,
            'es_mi_turno': es_mi_turno,
            'soy_mano': soy_mano,
            'descartes_listos': estado_del_jugador.get('descartes_listos', False),
            'descartes_rival': partida_actual.estado[rival_sid].get('descartes_hechos', 0),
            'apuestas': info_apuestas,
            'mensaje': mensaje,
            'mis_cartas': estado_del_jugador['cartas'],
            'mis_puntos': estado_del_jugador['puntos'],
            'puntos_rival': partida_actual.estado[rival_sid]['puntos'],
            'mensaje_transicion': partida_actual.mensaje_transicion,
            'recuento': datos_recuento,
            'cartas_rival': cartas_rival,
            'rival_puntos_finales': partida_actual.estado[rival_sid]['puntos'],
            'mis_partidas': partida_actual.partidas_ganadas[sid],
            'partidas_rival': partida_actual.partidas_ganadas[rival_sid],
            'al_mejor_de': partida_actual.al_mejor_de,
            'match_finalizado': partida_actual.match_finalizado
        }, room=sid)


@socketio.on('abandonar_sala_limpiamente')
def handle_abandonar_limpiamente():
    sid = request.sid
    if sid in jugadores:
        codigo = jugadores[sid]['sala']
        if codigo in salas:
            del salas[codigo] # Destruimos la sala para que 'disconnect' no avise al rival
            emitir_lista_publicas()


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in jugadores:
        codigo = jugadores[sid]['sala']
        nombre = jugadores[sid]['nombre']
        
        # Si la sala sigue existiendo, avisamos al que se ha quedado dentro
        if codigo in salas:
            print(f"❌ {nombre} se ha desconectado. Destruyendo sala {codigo}.")
            emit('rival_desconectado', room=codigo)
            del salas[codigo]  # Borramos la sala de la memoria
            emitir_lista_publicas()
            
        del jugadores[sid]  # Borramos los datos del jugador


if __name__ == '__main__':
    print("🚀 Servidor de Mus iniciado en http://localhost:5001")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)