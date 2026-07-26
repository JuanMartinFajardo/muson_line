import random
import os
import random, string

from mus_log import MatchLogger, NullLogger

# Logger mudo compartido por todos los `fork()`: un fork es una rama hipotética
# del árbol de CFR y nunca escribe, así que no merece su propio objeto.
_LOG_MUDO = NullLogger('-', '2p')
# ==========================================
# 1. BARAJA Y CARTAS
# ==========================================

Oros = 'coins' #Oros_btc
Copas = 'coups' #Copas_pirate
Espadas = 'swords'
Bastos = 'clubs'

import os

# 1. Obtenemos la ruta real de la carpeta donde está este script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def obtener_ruta_imagen(nombre):
    extensiones = [".webp", ".svg", ".jpg", ".png", ".jpeg"]
    
    for ext in extensiones:
        # Construimos la ruta real para que Python la encuentre en el disco
        # Ejemplo: C:/Proyecto/static/img/foto.jpg
        ruta_real = os.path.join(BASE_DIR, "static", "img", f"{nombre}{ext}")
        
        if os.path.exists(ruta_real):
            # Si existe, devolvemos la ruta que el NAVEGADOR entiende
            return f"/static/img/{nombre}{ext}"
            
    return "/static/img/default.jpg"

# Uso
nombre = "mi_imagen"
datos = {
    'img': obtener_ruta_imagen(nombre)
}

def crear_baraja():
    # Diccionario con tus nombres exactos de palos en minúsculas
    traduccion_palos = {
        'Oros': 'coins',
        'Copas': 'cups',
        'Espadas': 'swords',
        'Bastos': 'clubs'
    }
    
    palos = ['Oros', 'Copas', 'Espadas', 'Bastos']
    valores = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]
    baraja = []
    
    for palo in palos:
        for valor in valores:
            # Lógica del texto visible para el usuario en español
            nombre = str(valor)
            if valor == 1: nombre = 'As'
            elif valor == 10: nombre = 'Sota'
            elif valor == 11: nombre = 'Caballo'
            elif valor == 12: nombre = 'Rey'
            
            # Obtenemos el equivalente para el nombre del archivo SVG
            palo_en = traduccion_palos[palo]
            
            # Construye el formato exacto: card_coups_10, card_coins_1, etc.
            nombre_archivo = f"card_{palo_en}_{valor:02d}"
            
            baraja.append({
                'valor': valor, 
                'palo': palo,
                'img': obtener_ruta_imagen(nombre_archivo),
                'texto': f"{nombre} de {palo}"
            })
    return baraja


def get_valores_mus(cartas):
    # Los 3 son Reyes (12) y los 2 son Ases (1)
    return [12 if c['valor'] == 3 else (1 if c['valor'] == 2 else c['valor']) for c in cartas]

# ==========================================
# 2. EVALUACIÓN DE JUGADAS (Pares y Juego)
# ==========================================

# Nota de rendimiento (Fase 1.4): estas dos funciones son las más llamadas de
# todo el proyecto — el gimnasio las invoca cientos de miles de veces por
# iteración desde `acciones_legales`, `vista` y el recuento. Contaban con
# `collections.Counter`, que en cada llamada construye un objeto y pasa por el
# `isinstance` de la ABC: en el perfil salían ~170.000 Counter por 120 travesías.
# Un dict a mano hace lo mismo sin asignar nada raro. Mismo resultado, ~2× más
# rápido en el camino caliente.

def tiene_pares(cartas):
    valores = get_valores_mus(cartas)
    vistos = set()
    for v in valores:
        if v in vistos:
            return True
        vistos.add(v)
    return False

def get_pares_info(cartas):
    valores = get_valores_mus(cartas)
    counts = {}
    for v in valores:
        counts[v] = counts.get(v, 0) + 1

    # Filtramos solo los que tienen pareja o más
    pares = [[val, count] for val, count in counts.items() if count >= 2]
    
    if not pares:
        return {'tipo': 0, 'premio': 0}
        
    if len(pares) == 1:
        val, count = pares[0]
        if count == 2: return {'tipo': 1, 'v1': val, 'premio': 1} # Par
        if count == 3: return {'tipo': 2, 'v1': val, 'premio': 2} # Trío
        if count == 4: return {'tipo': 3, 'v1': val, 'v2': val, 'premio': 3} # Dúplex (4 iguales)
        
    if len(pares) == 2:
        mayor = max(pares[0][0], pares[1][0])
        menor = min(pares[0][0], pares[1][0])
        return {'tipo': 3, 'v1': mayor, 'v2': menor, 'premio': 3} # Dúplex (2 parejas)

def get_suma_juego(cartas):
    suma = 0
    for c in cartas:
        v = c['valor']
        if v == 3 or v >= 10: suma += 10
        elif v == 2 or v == 1: suma += 1
        else: suma += v
    return suma

def tiene_juego(cartas):
    return get_suma_juego(cartas) >= 31

def es_la_real(cartas):
    num_sietes = sum(1 for c in cartas if c['valor'] == 7)
    num_sotas = sum(1 for c in cartas if c['valor'] == 10)
    return num_sietes == 3 and num_sotas == 1

# ==========================================
# 2 bis. CÓDEC DE CARTAS PARA EL ESTADO PLANO (Fase 1.3 del roadmap de IA)
# ------------------------------------------------------------------
# `to_state()` de los motores tiene que ser JSON-able (también lo pide el
# Roadmap #18 capa 2 para guardar partidas), pero una carta es un dict con ruta
# de imagen y texto: pesado y redundante. Se serializa como (valor, palo) y se
# reconstruye desde un índice creado una sola vez por proceso, de modo que
# `from_state` devuelve LAS MISMAS instancias que crearía crear_baraja().
# Vive aquí (y no en mus_core) solo para no crear un import circular.
# ==========================================

_INDICE_CARTAS = {(c['valor'], c['palo']): c for c in crear_baraja()}


def carta_a_clave(carta):
    return (carta['valor'], carta['palo'])


def clave_a_carta(clave):
    return _INDICE_CARTAS[tuple(clave)]


def cartas_a_claves(cartas):
    return [(c['valor'], c['palo']) for c in cartas]


def claves_a_cartas(claves):
    return [_INDICE_CARTAS[tuple(k)] for k in claves]

# ==========================================
# 3. COMPARADORES (Devuelven 'mano' o 'postre')
# ==========================================

def comparar_cartas(cartas_mano, cartas_postre, is_grande):
    v_mano = sorted(get_valores_mus(cartas_mano), reverse=is_grande)
    v_postre = sorted(get_valores_mus(cartas_postre), reverse=is_grande)
    
    for i in range(4):
        if v_mano[i] > v_postre[i]: return 'mano' if is_grande else 'postre'
        if v_mano[i] < v_postre[i]: return 'postre' if is_grande else 'mano'
        
    return 'mano' # En empate absoluto, gana la mano

def comp_pares_info(info_mano, info_postre):
    if info_mano['tipo'] != info_postre['tipo']:
        return 'mano' if info_mano['tipo'] > info_postre['tipo'] else 'postre'
    
    if info_mano['v1'] != info_postre['v1']:
        return 'mano' if info_mano['v1'] > info_postre['v1'] else 'postre'
        
    if 'v2' in info_mano and 'v2' in info_postre and info_mano['v2'] != info_postre['v2']:
        return 'mano' if info_mano['v2'] > info_postre['v2'] else 'postre'
        
    return 'mano' # Empate

J_RANK = {31: 8, 32: 7, 40: 6, 37: 5, 36: 4, 35: 3, 34: 2, 33: 1}

def comp_juego(cartas_mano, cartas_postre):
    mano_real = es_la_real(cartas_mano)
    postre_real = es_la_real(cartas_postre)
    
    if mano_real and not postre_real: return 'mano'
    if not mano_real and postre_real: return 'postre'

    s_mano = get_suma_juego(cartas_mano)
    s_postre = get_suma_juego(cartas_postre)
    
    r_mano = J_RANK.get(s_mano, 0)
    r_postre = J_RANK.get(s_postre, 0)
    
    if r_mano > r_postre: return 'mano'
    if r_mano < r_postre: return 'postre'
    return 'mano'

def comp_punto(cartas_mano, cartas_postre):
    s_mano = get_suma_juego(cartas_mano)
    s_postre = get_suma_juego(cartas_postre)
    
    if s_mano > s_postre: return 'mano'
    if s_mano < s_postre: return 'postre'
    return 'mano'


# ==========================================
# 4. EL MOTOR DE LA PARTIDA (Clase principal)
# ==========================================



# (Aquí arriba se mantienen las funciones puras que ya definimos: crear_baraja, comp_juego, etc.)

class PartidaMus:
    def __init__(self, id_jugador_1, id_jugador_2):
            self.j1 = id_jugador_1
            self.j2 = id_jugador_2
            
            # Fuente de azar del motor. `None` = el `random` global de siempre;
            # la arena y la sonda LBR le enchufan un random.Random(semilla) para
            # que dos enfrentamientos vean los mismos repartos (menos varianza).
            # Se guarda None y no el módulo: un módulo no es copiable.
            self.rng = None

            sids = [self.j1, self.j2]
            random.shuffle(sids)
            self.id_mano = sids[0] 
            self.id_postre = sids[1]
            
            self.baraja = []
            self.descartes = []
            
            self.estado = {
                self.j1: {'cartas': [], 'puntos': 0, 'quiere_mus': None, 'descartes_listos': False, 'descartes_hechos': 0},
                self.j2: {'cartas': [], 'puntos': 0, 'quiere_mus': None, 'descartes_listos': False, 'descartes_hechos': 0}
            }
            
            self.fase = 'espera' 
            self.fases_apuesta = ['Grande', 'Chica', 'Pares', 'Juego']
            self.indice_fase = 0
            self.botes = {'Grande': 0, 'Chica': 0, 'Pares': 0, 'Juego': 0}
            self.dejes_fase = {'Grande': None, 'Chica': None, 'Pares': None, 'Juego': None}
            self.ganadores_fase = {'Grande': None, 'Chica': None, 'Pares': None, 'Juego': None}
            
            self.apuesta_vista = 0
            self.subida_pendiente = 0
            self.quien_sube = None
            self.pases_consecutivos = 0
            self.turno_de = None
            self.ordago_aceptado_en = None        
            self.mensaje_transicion = None
            self.recuento_calculado = False
            self.pasos_recuento = []
            self.jugadores_listos = []

            # --- LOG v2 (mus_log.py, Fase 1.1 del roadmap de IA) ---
            # Los ASIENTOS son estables durante todo el match (0 = j1, 1 = j2);
            # quién es mano en cada ronda va en el evento `deal`. El log arranca
            # mudo: lo enciende el servidor con `activar_log()`.
            self.match_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) # ID único para todo el match
            self.ronda_n = 0
            self.nombres_ia = {} # Para guardar los nombres reales de los jugadores y que aparezcan en el log
            self.asientos = [self.j1, self.j2]
            self.log = NullLogger(self.match_id, '2p')
            self._lances_ronda = {}
            self._decl_emitidas = set()

            # Baraja guionizada para la re-jugada (tools/log_verify.py).
            self.fuente_cartas = None


            # --- SISTEMA DE PARTIDAS ---
            self.partidas_ganadas = {self.j1: 0, self.j2: 0}
            self.al_mejor_de = 3 
            self.partida_sumada = False
            self.match_finalizado = False


    # --- 0. LOG v2 (wiki/Bot-AI-4p-ML-Strategy.md §8) ---

    def _azar(self):
        return self.rng if self.rng is not None else random

    def seat(self, jugador):
        """Índice de asiento estable (0 = j1, 1 = j2). El rol mano/postre rota."""
        return 0 if jugador == self.j1 else 1

    def _lance_actual(self):
        if self.fase == 'apuestas' and self.indice_fase < len(self.fases_apuesta):
            nombre = self.fases_apuesta[self.indice_fase]
            return 'Punto' if (nombre == 'Juego' and getattr(self, 'juego_es_punto', False)) else nombre
        return None

    def activar_log(self, seats=None, rules=None, dir_logs=None, enabled=True):
        """Abre el fichero v2 del match y escribe la cabecera. Mismo API que en 4p."""
        if seats is None:
            seats = [{'s': s, 'kind': 'human',
                      'code': self.nombres_ia.get(self.asientos[s])} for s in (0, 1)]
        base = {'objetivo': 40, 'al_mejor_de': self.al_mejor_de,
                'team_response': 'na', 'senas': False, 'engine': 'mus2'}
        if rules:
            base.update(rules)
        self.log = MatchLogger(self.match_id, '2p', enabled=enabled, dir_logs=dir_logs)
        self.log.hdr(base, seats, [[0], [1]])
        return self.log

        # --- 1. REPARTO Y GESTIÓN DE BARAJA ---

    def robar(self, cantidad):
        # Re-jugada: las cartas las dicta el log, no el azar.
        if getattr(self, 'fuente_cartas', None) is not None:
            return self.fuente_cartas(cantidad)
        robadas = []
        for _ in range(cantidad):
            if not self.baraja:
                # Si nos quedamos sin cartas, barajamos los descartes
                self.baraja = self.descartes.copy()
                self._azar().shuffle(self.baraja)
                self.descartes = []
            if self.baraja:
                robadas.append(self.baraja.pop(0))
        return robadas

    def iniciar_ronda(self):
        self.baraja = []#crear_baraja()
        #random.shuffle(self.baraja)
        self.descartes = []
        self.ronda_n += 1
        
        self.estado[self.j1]['cartas'] = []
        self.estado[self.j2]['cartas'] = []
      #  self.estado[self.j1]['cartas'] = self.robar(4)
       # self.estado[self.j2]['cartas'] = self.robar(4)
        
        self.fase = 'espera_reparto' #maybe comment
        self.estado[self.j1]['quiere_mus'] = None
        self.estado[self.j2]['quiere_mus'] = None
        self.turno_de = self.id_postre # o postre
        self.estado[self.j1]['descartes_hechos'] = 0
        self.estado[self.j2]['descartes_hechos'] = 0
        self.quien_corta_mus = None
        self.rondas_mus = 0
        self._lances_ronda = {}
        self._decl_emitidas = set()

    # --- 2. FASE DE MUS Y DESCARTES ---

    def cantar_mus(self, jugador, quiere_mus):
        """Devuelve True si ambos han hablado y hay que cambiar de fase"""
        self.log.accion(self.seat(jugador), 'mus' if quiere_mus else 'no_mus')
        self.estado[jugador]['quiere_mus'] = quiere_mus
        
        if not quiere_mus:
            # Si alguien corta el mus, pasamos directamente a apuestas
            self.quien_corta_mus = jugador
            self.iniciar_fase_apuestas()
            return 'apuestas'
            
        # Si la mano quiere mus, le toca hablar al postre
        if jugador == self.id_mano and quiere_mus:
            self.turno_de = self.id_postre
            return 'esperando_postre'
            
        # Si ambos quieren mus
        if self.estado[self.id_mano]['quiere_mus'] and self.estado[self.id_postre]['quiere_mus']:
            self.fase = 'descarte'
            self.estado[self.j1]['descartes_listos'] = False
            self.estado[self.j2]['descartes_listos'] = False
            self.rondas_mus += 1
            return 'descarte'


    def procesar_pedrete(self, jugador):
            """Verifica si tiene pedrete, le da un punto y le renueva la mano."""
            if self.fase not in ['mus', 'descarte']: return False
            
            # Comprobamos los valores reales (sin transformar los 3s y 2s)
            valores = sorted([c['valor'] for c in self.estado[jugador]['cartas']])
            if valores != [4, 5, 6, 7]: return False

            # 1. Registramos en el log v2
            self.log.accion(self.seat(jugador), 'pedrete')

            # 2. Sumamos el premio inmediato
            self.estado[jugador]['puntos'] += 1

            # 3. Tiramos sus cartas y le damos 4 nuevas
            cartas_viejas = self.estado[jugador]['cartas']
            self.descartes.extend(cartas_viejas)
            self.estado[jugador]['cartas'] = self.robar(4)
            self.log.draw(self.seat(jugador), [c['valor'] for c in self.estado[jugador]['cartas']])

            # 4. Si por un milagro este punto le hace ganar la partida:
            if self.estado[jugador]['puntos'] >= 40:
                self.fase = 'recuento'
                self.recuento_calculado = True
                self.pasos_recuento = [{'ganador_sid': jugador, 'datos': 'recuento_pedrete_win'}]
                self._lances_ronda['Pedrete'] = {'win': self.seat(jugador), 'pts': 1}
                self._cerrar_ronda()

            return True


    def procesar_descarte(self, jugador, indices_cartas_a_tirar):
            """Recibe una lista de índices (ej: [0, 2]) que el jugador quiere tirar"""
            indices_cartas_a_tirar = [int(i) for i in indices_cartas_a_tirar]
            # El log v2 guarda los ÍNDICES tirados: es lo que hace falta para
            # re-jugar la mano (las cartas ya se conocen por `deal`/`draw`).
            self.log.accion(self.seat(jugador), 'descarte', idx=sorted(indices_cartas_a_tirar))

            cartas_jugador = self.estado[jugador]['cartas']

            # Extraer las cartas a tirar de mayor a menor índice para no alterar la lista al borrar
            cartas_tiradas = [cartas_jugador.pop(i) for i in sorted(indices_cartas_a_tirar, reverse=True)]
            self.descartes.extend(cartas_tiradas)
            self.estado[jugador]['descartes_hechos'] = len(indices_cartas_a_tirar)

            # Robar nuevas
            nuevas_cartas = self.robar(len(indices_cartas_a_tirar))
            self.estado[jugador]['cartas'].extend(nuevas_cartas)
            if nuevas_cartas:
                self.log.draw(self.seat(jugador), [c['valor'] for c in nuevas_cartas])

            self.estado[jugador]['descartes_listos'] = True
            
            if self.estado[self.id_mano]['descartes_listos'] and self.estado[self.id_postre]['descartes_listos']:
                self.fase = 'mus'
                self.estado[self.j1]['quiere_mus'] = None
                self.estado[self.j2]['quiere_mus'] = None
                self.turno_de = self.id_mano
                return 'nuevo_mus'
                
            return 'esperando_rival'

    # --- 3. MOTOR DE APUESTAS ---

    def iniciar_fase_apuestas(self):
        self.fase = 'apuestas'
        self.indice_fase = 0
        self.botes = {'Grande': 0, 'Chica': 0, 'Pares': 0, 'Juego': 0}
        self.dejes_fase = {'Grande': None, 'Chica': None, 'Pares': None, 'Juego': None}
        self.ganadores_fase = {'Grande': None, 'Chica': None, 'Pares': None, 'Juego': None}
        self.ordago_aceptado_en = None
        self.juego_es_punto = False
        self.preparar_subfase()
        self.transicion_punto_mostrada = False

    def preparar_subfase(self):
        self.mensaje_transicion = None
        if self.indice_fase >= len(self.fases_apuesta):
            self.fase = 'recuento'
            return

        nombre_fase = self.fases_apuesta[self.indice_fase]
        self.apuesta_vista = 0
        self.subida_pendiente = 0
        self.quien_sube = None
        self.pases_consecutivos = 0

        if nombre_fase == 'Grande' and getattr(self, 'quien_corta_mus', None):
            self.turno_de = self.quien_corta_mus
        else:
            self.turno_de = self.id_mano

        if nombre_fase == 'Pares':
            m_tiene = tiene_pares(self.estado[self.id_mano]['cartas'])
            p_tiene = tiene_pares(self.estado[self.id_postre]['cartas'])
            self._declarar('Pares', {self.id_mano: m_tiene, self.id_postre: p_tiene})
            if not m_tiene or not p_tiene:
                if not m_tiene and not p_tiene: self.mensaje_transicion = {'code': 'nadie_pares', 'fase': 'Pares'}
                elif m_tiene: self.mensaje_transicion = {'code': 'no_pares', 'rol': 'postre', 'fase': 'Pares'}
                else: self.mensaje_transicion = {'code': 'no_pares', 'rol': 'mano', 'fase': 'Pares'}
                # Avanzamos la máquina de estados internamente antes del return
                self.indice_fase += 1 
                return
                
        elif nombre_fase == 'Juego':
            m_tiene = tiene_juego(self.estado[self.id_mano]['cartas'])
            p_tiene = tiene_juego(self.estado[self.id_postre]['cartas'])
            self._declarar('Juego', {self.id_mano: m_tiene, self.id_postre: p_tiene})

            # ¡NUEVO! Si nadie tiene, mostramos el aviso pero NO saltamos la fase
            if not m_tiene and not p_tiene:
                self.juego_es_punto = True
                if not getattr(self, 'transicion_punto_mostrada', False):
                    self.mensaje_transicion = {'code': 'juego_a_punto', 'fase': 'Juego'}
                    self.transicion_punto_mostrada = True
                    return # Hace la pausa de 3s, luego volverá a entrar aquí y pasará de largo
            
            # Si solo uno tiene, mostramos el aviso y SÍ saltamos la fase
            elif m_tiene != p_tiene:
                if m_tiene: self.mensaje_transicion = {'code': 'no_juego', 'rol': 'postre', 'fase': 'Juego'}
                else: self.mensaje_transicion = {'code': 'no_juego', 'rol': 'mano', 'fase': 'Juego'}
                self.indice_fase += 1
                return

    def _declarar(self, lance, por_jugador):
        """Emite las declaraciones públicas de pares/juego al log (una vez por ronda).

        A la rama de Juego se vuelve a entrar tras el aviso "juego a punto", de
        ahí el guard: la declaración se canta una sola vez."""
        if lance in self._decl_emitidas:
            return
        self._decl_emitidas.add(lance)
        for jugador in (self.id_mano, self.id_postre):
            self.log.decl(self.seat(jugador), lance, por_jugador[jugador])

    def avanzar_subfase(self, bote_extra):
        nombre_fase = self.fases_apuesta[self.indice_fase]
        self.botes[nombre_fase] += bote_extra
        self.indice_fase += 1
        self.preparar_subfase()

    def accion_apuesta(self, jugador, accion, cantidad=0):
        # Cantidad PEDIDA (no la recortada al tope legal): es la decisión real.
        self.log.accion(self.seat(jugador), accion, lance=self._lance_actual(), cantidad=cantidad)
        nombre_fase = self.fases_apuesta[self.indice_fase]
        rival = self.id_postre if jugador == self.id_mano else self.id_mano

        if accion == 'pasar':
            self.pases_consecutivos += 1
            if self.pases_consecutivos == 2:
                # Pase corrido. Punto de pase solo en Grande y Chica (El Punto ya se suma en el recuento como pts_bonus).
                punto_pase = 1 if nombre_fase in ['Grande', 'Chica'] else 0
                self.avanzar_subfase(punto_pase)
            else:
                self.turno_de = rival

        elif accion == 'nover':
            deje = self.apuesta_vista if self.apuesta_vista > 0 else 1
            
            # --- NUEVA REGLA: OBLIGADO A VER SI CUESTA LA PARTIDA ---
            if self.estado[rival]['puntos'] + deje >= 40:
                print(f"⚠️ {jugador} obligado a ver. El deje de {deje} da la partida al rival.")
                # Transformamos la acción en "ver" automáticamente
                if self.subida_pendiente == 'ÓRDAGO':
                    self.botes[nombre_fase] = 40
                    self.ordago_aceptado_en = nombre_fase
                    self.fase = 'recuento'
                else:
                    self.botes[nombre_fase] += (self.apuesta_vista + self.subida_pendiente)
                    self.avanzar_subfase(0)
            else:
                # Comportamiento normal del "No ver"
                self.estado[rival]['puntos'] += deje
                self.ganadores_fase[nombre_fase] = rival
                if not hasattr(self, 'dejes_fase'):
                    self.dejes_fase = {'Grande': None, 'Chica': None, 'Pares': None, 'Juego': None}
                self.dejes_fase[nombre_fase] = {'ganador': rival, 'valor': deje}
                self.avanzar_subfase(0)

        elif accion == 'envidar' or accion == 'subir':
            self.pases_consecutivos = 0
            
            # --- BLINDAJE 2: TOPE NUMÉRICO PARA JUGADORES E IA ---
            pts_maximos = max(self.estado[jugador]['puntos'], self.estado[rival]['puntos'])
            
            if accion == 'subir':
                self.apuesta_vista += self.subida_pendiente
                
            # Calculamos cuántos puntos faltan para que la partida se acabe
            tope_legal = 40 - pts_maximos - self.apuesta_vista
            
            if tope_legal <= 0:
                # Si ya estamos en 40, cualquier intento de subir se convierte en Órdago automáticamente
                print(f"⚠️ {jugador} (o Bot) intentó subir sin margen. Convertido a ÓRDAGO.")
                self.subida_pendiente = 'ÓRDAGO'
            else:
                # Capamos la apuesta de la IA o del jugador al máximo legal permitido
                cantidad_real = min(cantidad, tope_legal)
                self.subida_pendiente = max(1, cantidad_real) # Evitamos números negativos o ceros
                
            self.quien_sube = jugador
            self.turno_de = rival

        elif accion == 'ver':
            if self.subida_pendiente == 'ÓRDAGO':
                self.botes[nombre_fase] = 40
                self.ordago_aceptado_en = nombre_fase
                self.fase = 'recuento'
            else:
                self.botes[nombre_fase] += (self.apuesta_vista + self.subida_pendiente)
                self.avanzar_subfase(0)

        elif accion == 'ordago':
            self.pases_consecutivos = 0
            if self.subida_pendiente != 'ÓRDAGO':
                self.apuesta_vista += self.subida_pendiente
            self.subida_pendiente = 'ÓRDAGO'
            self.quien_sube = jugador
            self.turno_de = rival



    def repartir_inicial(self):
        self.baraja = crear_baraja()
        self._azar().shuffle(self.baraja)
        self.descartes = []
        
        self.estado[self.id_mano]['cartas'] = self.robar(4)
        self.estado[self.id_postre]['cartas'] = self.robar(4)
        self.fase = 'mus'
        self.turno_de = self.id_mano #mano
        self.log.deal(self.ronda_n, self.seat(self.id_mano),
                      [[c['valor'] for c in self.estado[p]['cartas']] for p in self.asientos])
        
        
    def puede_pedrete(self, jugador):
        if self.fase not in ('mus', 'descarte'):
            return False
        return sorted([c['valor'] for c in self.estado[jugador]['cartas']]) == [4, 5, 6, 7]

    def acciones_legales(self, jugador):
        """Acciones que `jugador` puede ejecutar AHORA mismo, ya filtradas.

        Análogo 2p de PartidaMus4.acciones_legales: incluye la legalidad del
        motor (turno, fase, tope de 40) y las reglas que el motor no vigila por
        sí solo (no se apuesta a Pares/Juego sin la jugada). Quien elija solo de
        esta lista no puede hacer una jugada ilegal — lo necesitan la re-jugada,
        la sonda LBR (Fase 1.6) y cualquier bot que no pase por mus_env."""
        if self.match_finalizado or self.mensaje_transicion:
            return []

        rival = self.id_postre if jugador == self.id_mano else self.id_mano
        acciones = []
        if self.puede_pedrete(jugador):
            acciones.append('pedrete')

        if self.fase == 'recuento':
            if jugador not in self.jugadores_listos:
                acciones.append('listo_siguiente_ronda')
            return acciones

        if self.fase == 'descarte':
            if not self.estado[jugador]['descartes_listos']:
                acciones.append('descartar')
            return acciones

        if jugador != self.turno_de:
            return acciones

        if self.fase == 'espera_reparto':
            return acciones + ['repartir']

        if self.fase == 'mus':
            if self.estado[jugador]['quiere_mus'] is None:
                acciones.extend(['mus', 'no_mus'])
            return acciones

        if self.fase != 'apuestas' or self.indice_fase >= len(self.fases_apuesta):
            return acciones

        nombre_fase = self.fases_apuesta[self.indice_fase]
        cartas = self.estado[jugador]['cartas']
        respondiendo = (self.subida_pendiente != 0)

        if nombre_fase == 'Pares' and not tiene_pares(cartas):
            return acciones + (['nover'] if respondiendo else ['pasar'])
        if nombre_fase == 'Juego' and not tiene_juego(cartas) and not getattr(self, 'juego_es_punto', False):
            return acciones + (['nover'] if respondiendo else ['pasar'])

        pts_max = max(self.estado[jugador]['puntos'], self.estado[rival]['puntos'])
        deje = self.apuesta_vista if self.apuesta_vista > 0 else 1
        obligado_a_ver = (self.estado[rival]['puntos'] + deje >= 40)

        if not respondiendo:
            acciones.append('pasar')
            if 40 - pts_max - self.apuesta_vista > 0:
                acciones.append('envidar')
            acciones.append('ordago')
            return acciones

        if self.subida_pendiente == 'ÓRDAGO':
            acciones.append('ver')
            if not obligado_a_ver:
                acciones.append('nover')
            return acciones

        acciones.append('ver')
        if not obligado_a_ver:
            acciones.append('nover')
        if 40 - pts_max - (self.apuesta_vista + self.subida_pendiente) > 0:
            acciones.append('subir')
        acciones.append('ordago')
        return acciones

    def cambiar_roles(self):
        # Intercambia quién es mano y postre
        self.id_mano, self.id_postre = self.id_postre, self.id_mano

    def reiniciar_partida(self):
        self.estado[self.j1]['puntos'] = 0
        self.estado[self.j2]['puntos'] = 0
        self.partida_sumada = False
        self.cambiar_roles()
        self.iniciar_ronda()


    def calcular_recuento(self):
        if self.recuento_calculado: return self.pasos_recuento
        
        self.recuento_calculado = True
        self.pasos_recuento = [] 
        cartas_m = self.estado[self.id_mano]['cartas']
        cartas_p = self.estado[self.id_postre]['cartas']
        fases_eval = [self.ordago_aceptado_en] if self.ordago_aceptado_en else self.fases_apuesta
        
        for fase in fases_eval:
            if self.estado[self.id_mano]['puntos'] >= 40 or self.estado[self.id_postre]['puntos'] >= 40: break
            
            ganador_sid = self.ganadores_fase.get(fase)
            bote = self.botes.get(fase, 0)
            pts_bonus = 0
            n_log = fase
            
            if self.ordago_aceptado_en:
                pts_total = 40
                if not ganador_sid:
                    ganador_rol = None
                    if fase == 'Grande': ganador_rol = comparar_cartas(cartas_m, cartas_p, True)
                    elif fase == 'Chica': ganador_rol = comparar_cartas(cartas_m, cartas_p, False)
                    elif fase == 'Pares': ganador_rol = comp_pares_info(get_pares_info(cartas_m), get_pares_info(cartas_p))
                    elif fase == 'Juego':
                        if not tiene_juego(cartas_m) and not tiene_juego(cartas_p):
                            n_log = 'Punto'
                            ganador_rol = comp_punto(cartas_m, cartas_p)
                        else:
                            ganador_rol = comp_juego(cartas_m, cartas_p)
                    ganador_sid = self.id_mano if ganador_rol == 'mano' else self.id_postre
            else:
                if fase == 'Grande' and not ganador_sid:
                    ganador_sid = self.id_mano if comparar_cartas(cartas_m, cartas_p, True) == 'mano' else self.id_postre
                elif fase == 'Chica' and not ganador_sid:
                    ganador_sid = self.id_mano if comparar_cartas(cartas_m, cartas_p, False) == 'mano' else self.id_postre
                elif fase == 'Pares':
                    if not tiene_pares(cartas_m) and not tiene_pares(cartas_p): continue
                    if not ganador_sid:
                        if tiene_pares(cartas_m) and not tiene_pares(cartas_p): ganador_sid = self.id_mano
                        elif not tiene_pares(cartas_m) and tiene_pares(cartas_p): ganador_sid = self.id_postre
                        else: ganador_sid = self.id_mano if comp_pares_info(get_pares_info(cartas_m), get_pares_info(cartas_p)) == 'mano' else self.id_postre
                    pts_bonus = get_pares_info(cartas_m)['premio'] if ganador_sid == self.id_mano else get_pares_info(cartas_p)['premio']
                elif fase == 'Juego':
                    if not tiene_juego(cartas_m) and not tiene_juego(cartas_p):
                        n_log = 'Punto'
                        if not ganador_sid: ganador_sid = self.id_mano if comp_punto(cartas_m, cartas_p) == 'mano' else self.id_postre
                        pts_bonus = 1
                    else:
                        if not ganador_sid:
                            if tiene_juego(cartas_m) and not tiene_juego(cartas_p): ganador_sid = self.id_mano
                            elif not tiene_juego(cartas_m) and tiene_juego(cartas_p): ganador_sid = self.id_postre
                            else: ganador_sid = self.id_mano if comp_juego(cartas_m, cartas_p) == 'mano' else self.id_postre
                        suma = get_suma_juego(cartas_m) if ganador_sid == self.id_mano else get_suma_juego(cartas_p)
                        pts_bonus = 3 if suma == 31 else 2
                
            pts_total = bote + pts_bonus
            
            if pts_total > 0:
                self.estado[ganador_sid]['puntos'] = min(40, self.estado[ganador_sid]['puntos'] + pts_total)
                
            # Construimos el texto exacto para enviarlo al navegador
            if self.ordago_aceptado_en and fase == self.ordago_aceptado_en:
                datos_paso = {'code': 'recuento_ordago', 'fase': n_log}
            elif self.ganadores_fase.get(fase) is not None and pts_total == 0:
                datos_paso = {'code': 'recuento_nover', 'fase': n_log}
            else:
                datos_paso = {'code': 'recuento_gana', 'puntos': pts_total, 'fase': n_log}
                
            self.pasos_recuento.append({
                'ganador_sid': ganador_sid,
                'datos': datos_paso
            })
            deje = self.dejes_fase.get(fase)
            self._lances_ronda[n_log] = {'win': self.seat(ganador_sid), 'pts': pts_total}
            if self.ordago_aceptado_en:
                self._lances_ronda[n_log]['ordago'] = True
            elif deje is not None:
                self._lances_ronda[n_log]['deje'] = deje['valor']

        self._cerrar_ronda()
        return self.pasos_recuento

    def _cerrar_ronda(self):
        """Evento `eor`, recuento de partidas y, si toca, `eom`.

        Aparte del recuento normal se llega aquí por el pedrete que cierra la
        partida, que se salta `calcular_recuento` entero."""
        self.log.eor(self.ronda_n, self._lances_ronda,
                     [self.estado[p]['puntos'] for p in self.asientos],
                     [[c['valor'] for c in self.estado[p]['cartas']] for p in self.asientos])

        if not getattr(self, 'partida_sumada', False):
            if self.estado[self.id_mano]['puntos'] >= 40:
                self.partidas_ganadas[self.id_mano] += 1
                self.partida_sumada = True
            elif self.estado[self.id_postre]['puntos'] >= 40:
                self.partidas_ganadas[self.id_postre] += 1
                self.partida_sumada = True

            # Si alguien ha ganado la partida, comprobamos si ha ganado el "Match"
            if self.partida_sumada:
                puntos_para_ganar = (self.al_mejor_de // 2) + 1
                if self.partidas_ganadas[self.id_mano] >= puntos_para_ganar or self.partidas_ganadas[self.id_postre] >= puntos_para_ganar:
                    self.match_finalizado = True

        if self.match_finalizado:
            ganador = self.j1 if self.partidas_ganadas[self.j1] > self.partidas_ganadas[self.j2] else self.j2
            self.log.eom(self.seat(ganador),
                         [self.partidas_ganadas[self.j1], self.partidas_ganadas[self.j2]])

    # ==========================================
    # Estado plano: fork() y (de)serialización — Fase 1.3
    # ------------------------------------------------------------------
    # Ver la nota larga en mus_mecanicas_4.PartidaMus4.fork(): las cartas son
    # inmutables en la práctica, así que el fork comparte los dicts de carta y
    # solo duplica los contenedores. Esto es lo que quita a `copy.deepcopy` del
    # camino crítico del gimnasio (mus_env.py).
    # ==========================================
    _CAMPOS_ESCALARES = (
        'j1', 'j2', 'id_mano', 'id_postre', 'fase', 'indice_fase',
        'apuesta_vista', 'subida_pendiente', 'quien_sube', 'pases_consecutivos',
        'turno_de', 'ordago_aceptado_en', 'recuento_calculado', 'match_id',
        'ronda_n', 'al_mejor_de', 'partida_sumada', 'match_finalizado',
        'quien_corta_mus', 'rondas_mus', 'juego_es_punto',
        'transicion_punto_mostrada',
    )

    def fork(self):
        """Copia rápida e independiente del motor (sin logger: un fork no escribe)."""
        otro = object.__new__(PartidaMus)
        d, od = self.__dict__, otro.__dict__
        for campo in PartidaMus._CAMPOS_ESCALARES:
            od[campo] = d.get(campo)
        od['fases_apuesta'] = self.fases_apuesta
        od['asientos'] = self.asientos
        od['rng'] = self.rng
        od['nombres_ia'] = self.nombres_ia
        od['baraja'] = self.baraja[:]
        od['descartes'] = self.descartes[:]
        od['estado'] = {p: {'cartas': e['cartas'][:], 'puntos': e['puntos'],
                            'quiere_mus': e['quiere_mus'],
                            'descartes_listos': e['descartes_listos'],
                            'descartes_hechos': e['descartes_hechos']}
                        for p, e in self.estado.items()}
        od['botes'] = dict(self.botes)
        od['dejes_fase'] = dict(self.dejes_fase)
        od['ganadores_fase'] = dict(self.ganadores_fase)
        od['partidas_ganadas'] = dict(self.partidas_ganadas)
        od['pasos_recuento'] = list(self.pasos_recuento)
        od['jugadores_listos'] = list(self.jugadores_listos)
        od['mensaje_transicion'] = self.mensaje_transicion
        od['_lances_ronda'] = dict(self._lances_ronda)
        od['_decl_emitidas'] = set(self._decl_emitidas)
        od['log'] = _LOG_MUDO
        od['fuente_cartas'] = None
        return otro

    def to_state(self):
        """Estado completo como estructura plana JSON-able."""
        return {
            'v': 1,
            'escalares': {c: getattr(self, c, None) for c in PartidaMus._CAMPOS_ESCALARES},
            'baraja': cartas_a_claves(self.baraja),
            'descartes': cartas_a_claves(self.descartes),
            'estado': {p: {'cartas': cartas_a_claves(e['cartas']), 'puntos': e['puntos'],
                           'quiere_mus': e['quiere_mus'],
                           'descartes_listos': e['descartes_listos'],
                           'descartes_hechos': e['descartes_hechos']}
                       for p, e in self.estado.items()},
            'botes': dict(self.botes),
            'dejes_fase': dict(self.dejes_fase),
            'ganadores_fase': dict(self.ganadores_fase),
            'partidas_ganadas': dict(self.partidas_ganadas),
            'pasos_recuento': list(self.pasos_recuento),
            'jugadores_listos': list(self.jugadores_listos),
            'mensaje_transicion': self.mensaje_transicion,
            'lances_ronda': dict(self._lances_ronda),
            'decl_emitidas': sorted(self._decl_emitidas),
        }

    @classmethod
    def from_state(cls, estado_plano):
        esc = estado_plano['escalares']
        motor = cls(esc['j1'], esc['j2'])
        for campo, valor in esc.items():
            setattr(motor, campo, valor)
        motor.baraja = claves_a_cartas(estado_plano['baraja'])
        motor.descartes = claves_a_cartas(estado_plano['descartes'])
        motor.estado = {p: {'cartas': claves_a_cartas(e['cartas']), 'puntos': e['puntos'],
                            'quiere_mus': e['quiere_mus'],
                            'descartes_listos': e['descartes_listos'],
                            'descartes_hechos': e['descartes_hechos']}
                        for p, e in estado_plano['estado'].items()}
        motor.asientos = [esc['j1'], esc['j2']]
        motor.botes = dict(estado_plano['botes'])
        motor.dejes_fase = dict(estado_plano['dejes_fase'])
        motor.ganadores_fase = dict(estado_plano['ganadores_fase'])
        motor.partidas_ganadas = dict(estado_plano['partidas_ganadas'])
        motor.pasos_recuento = list(estado_plano['pasos_recuento'])
        motor.jugadores_listos = list(estado_plano['jugadores_listos'])
        motor.mensaje_transicion = estado_plano['mensaje_transicion']
        motor._lances_ronda = dict(estado_plano.get('lances_ronda') or {})
        motor._decl_emitidas = set(estado_plano.get('decl_emitidas') or ())
        motor.log = NullLogger(motor.match_id, '2p')
        return motor
