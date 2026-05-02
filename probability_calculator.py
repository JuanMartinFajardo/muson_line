import itertools

def calcular_probabilidad_grande(mis_cartas, cartas_conocidas_fuera=None, soy_mano=True):
    """
    Calcula la probabilidad de ganar a la Grande en el Mus.
    mis_cartas: lista de 4 enteros (ej: [12, 12, 11, 1])
    cartas_conocidas_fuera: lista de enteros con cartas descartadas/vistas (ej: [4, 5, 7])
    soy_mano: booleano que indica si somos nosotros los que tenemos la mano
    """
    if cartas_conocidas_fuera is None:
        cartas_conocidas_fuera = []

    # 1. Normalizar mis cartas y las descartadas (3s son Reyes(12), 2s son Ases(1))
    mis_cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in mis_cartas]
    mis_cartas_norm.sort(reverse=True)
    
    descartadas_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_conocidas_fuera]

    # 2. Definir el mazo completo
    mazo_completo = (
        [12] * 8 +  # Reyes y Treses
        [11] * 4 +  # Caballos
        [10] * 4 +  # Sotas
        [7]  * 4 +
        [6]  * 4 +
        [5]  * 4 +
        [4]  * 4 +
        [1]  * 8    # Ases y Doses
    )

    mazo_restante = mazo_completo.copy()

    # 3. Retirar mis cartas del mazo
    for carta in mis_cartas_norm:
        if carta in mazo_restante:
            mazo_restante.remove(carta)
        else:
            raise ValueError(f"Error: La carta {carta} en tu mano no es válida o hay demasiadas.")

    # 4. Retirar las cartas conocidas/pedretes descartados
    for carta in descartadas_norm:
        if carta in mazo_restante:
            mazo_restante.remove(carta)
        else:
            raise ValueError(f"Error: La carta descartada {carta} ya no está en el mazo. Revisa los datos.")

    victorias = 0
    derrotas = 0
    empates = 0

    # 5. Generar combinaciones. Ahora el mazo tiene 36 - N cartas.
    for mano_rival in itertools.combinations(mazo_restante, 4):
        rival_ordenada = sorted(mano_rival, reverse=True)

        for mi_carta, su_carta in zip(mis_cartas_norm, rival_ordenada):
            if mi_carta > su_carta:
                victorias += 1
                break
            elif su_carta > mi_carta:
                derrotas += 1
                break
            else:
                if soy_mano:
                    victorias += 1
                else:
                    derrotas += 1

    total_combinaciones = victorias + derrotas

    return {
        "victorias": victorias,
        "derrotas": derrotas,
        "prob_ganar": round((victorias / total_combinaciones) * 100, 2),
        "prob_perder": round((derrotas / total_combinaciones) * 100, 2)
    }

# --- Prueba del impacto de los pedretes ---
mis_cartas = [12, 10, 7, 1]  # Rey, Sota, 7, As

# Escenario A: No sabemos nada de los descartes
resultados_sin_descartes = calcular_probabilidad_grande(mis_cartas)

# Escenario B: Nos descartamos nosotros mismos de tres pedretes (un 4, un 5 y un 6)
pedretes_descartados = [4, 5, 6]
resultados_con_descartes = calcular_probabilidad_grande(mis_cartas, pedretes_descartados)

print("--- ESCENARIO A: Sin contar pedretes ---")
print(f"Ganar:  {resultados_sin_descartes['prob_ganar']}%")
print("\n--- ESCENARIO B: Sabiendo que 4, 5 y 6 están fuera ---")
print(f"Ganar:  {resultados_con_descartes['prob_ganar']}%")




def calcular_probabilidad_chica(mis_cartas, cartas_conocidas_fuera=None, soy_mano=True):
    """
    Calcula la probabilidad de ganar a la Chica en el Mus.
    mis_cartas: lista de 4 enteros (ej: [1, 1, 4, 12] para dos ases, un cuatro y un rey)
    cartas_conocidas_fuera: lista de enteros con cartas descartadas/vistas
    soy_mano: booleano que indica si somos nosotros los que tienen la mano
    """
    if cartas_conocidas_fuera is None:
        cartas_conocidas_fuera = []

    # 1. Normalizar mis cartas y las descartadas (3s son Reyes(12), 2s son Ases(1))
    mis_cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in mis_cartas]
    # ORDENAMOS DE MENOR A MAYOR para la chica
    mis_cartas_norm.sort()
    
    descartadas_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_conocidas_fuera]

    # 2. Definir el mazo completo
    mazo_completo = (
        [12] * 8 +  # Reyes y Treses
        [11] * 4 +  # Caballos
        [10] * 4 +  # Sotas
        [7]  * 4 +
        [6]  * 4 +
        [5]  * 4 +
        [4]  * 4 +
        [1]  * 8    # Ases y Doses
    )

    mazo_restante = mazo_completo.copy()

    # 3. Retirar mis cartas del mazo
    for carta in mis_cartas_norm:
        if carta in mazo_restante:
            mazo_restante.remove(carta)
        else:
            raise ValueError(f"Error: La carta {carta} en tu mano no es válida o hay demasiadas.")

    # 4. Retirar las cartas conocidas fuera
    for carta in descartadas_norm:
        if carta in mazo_restante:
            mazo_restante.remove(carta)
        else:
            raise ValueError(f"Error: La carta descartada {carta} ya no está en el mazo.")

    victorias = 0
    derrotas = 0
    empates = 0

    # 5. Generar combinaciones y evaluar
    for mano_rival in itertools.combinations(mazo_restante, 4):
        # ORDENAMOS DE MENOR A MAYOR la mano rival
        rival_ordenada = sorted(mano_rival)

        for mi_carta, su_carta in zip(mis_cartas_norm, rival_ordenada):
            # En la chica, gana la carta con el valor MENOR
            if mi_carta < su_carta:
                victorias += 1
                break
            elif su_carta < mi_carta:
                derrotas += 1
                break
            else:
                if soy_mano:
                    victorias += 1
                else:
                    derrotas += 1

    total_combinaciones = victorias + derrotas

    return {
        "victorias": victorias,
        "derrotas": derrotas,
        "prob_ganar": round((victorias / total_combinaciones) * 100, 2),
        "prob_perder": round((derrotas / total_combinaciones) * 100, 2)
    }

# --- Prueba del código ---
# Imagina que llevas una mano típica de chica: As, As, Cuatro, Rey
mis_cartas = [1, 1, 4, 12]
# Supongamos que en los descartes viste a alguien tirar un Caballo y un Siete
descartes = [11, 7] 

resultados = calcular_probabilidad_chica(mis_cartas, descartes)

print(f"Mano para Chica: {mis_cartas} (Ordenada: {sorted([12 if c == 3 else 1 if c == 2 else c for c in mis_cartas])})")
print(f"Descartes vistos: {descartes}")
print(f"Ganar:   {resultados['prob_ganar']}% ({resultados['victorias']} combos)")
print(f"Perder:  {resultados['prob_perder']}% ({resultados['derrotas']} combos)")



#pares


def evaluar_pares(mano_norm):
    conteos = {}
    for carta in mano_norm:
        conteos[carta] = conteos.get(carta, 0) + 1
    pares = [(count, carta) for carta, count in conteos.items() if count >= 2]
    if not pares:
        return (0, (0,))
    pares.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if pares[0][0] == 4: return (3, (pares[0][1], pares[0][1]))
    elif len(pares) == 2 and pares[0][0] == 2 and pares[1][0] == 2: return (3, (pares[0][1], pares[1][1]))
    elif pares[0][0] == 3: return (2, (pares[0][1],))
    elif pares[0][0] == 2: return (1, (pares[0][1],))

def calcular_probabilidad_pares(mis_cartas, rival_pares=False, soy_mano=True, cartas_conocidas_fuera=None):
    if cartas_conocidas_fuera is None: cartas_conocidas_fuera = []
    mis_cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in mis_cartas]
    descartadas_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_conocidas_fuera]

    mi_categoria, mi_valor = evaluar_pares(mis_cartas_norm)
    mazo_restante = ([12]*8 + [11]*4 + [10]*4 + [7]*4 + [6]*4 + [5]*4 + [4]*4 + [1]*8)

    for carta in mis_cartas_norm + descartadas_norm:
        mazo_restante.remove(carta)

    victorias, derrotas = 0, 0
    combinaciones_validas = 0

    for mano_rival in itertools.combinations(mazo_restante, 4):
        su_categoria, su_valor = evaluar_pares(mano_rival)
        if rival_pares and su_categoria == 0: continue
        combinaciones_validas += 1

        if mi_categoria == 0:
            if su_categoria > 0: derrotas += 1
            else: 
                # Si ninguno tiene pares, "gana" la mano (aunque no se apueste)
                if soy_mano: victorias += 1 
                else: derrotas += 1
            continue

        if mi_categoria > su_categoria: victorias += 1
        elif mi_categoria < su_categoria: derrotas += 1
        else:
            if mi_valor > su_valor: victorias += 1
            elif mi_valor < su_valor: derrotas += 1
            else:
                # AQUÍ ESTÁ LA MAGIA DEL EMPATE: Gana la mano. Sin mirar el resto de cartas.
                if soy_mano:
                    victorias += 1
                else:
                    derrotas += 1

    if combinaciones_validas == 0: return {"error": "Sin combinaciones"}
    return {
        "victorias": victorias, "derrotas": derrotas,
        "prob_ganar": round((victorias / combinaciones_validas) * 100, 2)
    }




## JUEGO
import itertools

def evaluar_pares(mano):
    conteos = {}
    for carta in mano: conteos[carta] = conteos.get(carta, 0) + 1
    return any(count >= 2 for count in conteos.values())

def calcular_valor_juego(mano_norm):
    suma = sum([10 if c >= 10 else c for c in mano_norm])
    es_real = (mano_norm.count(7) == 3 and mano_norm.count(10) == 1)
    
    if suma >= 31:
        if es_real:
            rango = 9
        else:
            jerarquia_juego = {31: 8, 32: 7, 40: 6, 37: 5, 36: 4, 35: 3, 34: 2, 33: 1}
            rango = jerarquia_juego.get(suma, 0)
        return {"tiene_juego": True, "suma": suma, "rango": rango, "es_real": es_real}
    else:
        return {"tiene_juego": False, "suma": suma, "rango": suma, "es_real": False}

def calcular_probabilidad_juego(mis_cartas, rival_pares=0, fase_confirmada=False, soy_mano=True, cartas_conocidas_fuera=None):
    """
    rival_pares: 
        1 -> Sabemos que tiene pares ("Pares sí")
        0 -> No lo sabemos (Primera ronda, en frío)
       -1 -> Sabemos que NO tiene pares ("Pares no")
    fase_confirmada: True si sabemos seguro que el rival disputa la misma fase que nosotros.
    """
    if cartas_conocidas_fuera is None: cartas_conocidas_fuera = []
    
    mis_cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in mis_cartas]
    descartadas_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_conocidas_fuera]
    mi_estado = calcular_valor_juego(mis_cartas_norm)

    mazo_restante = ([12]*8 + [11]*4 + [10]*4 + [7]*4 + [6]*4 + [5]*4 + [4]*4 + [1]*8)
    for carta in mis_cartas_norm + descartadas_norm:
        mazo_restante.remove(carta)

    victorias, derrotas, combinaciones_validas = 0, 0, 0

    for mano_rival in itertools.combinations(mazo_restante, 4):
        # 1. Filtro de Pares (Tu nueva lógica: 1, 0, -1)
        su_tiene_pares = evaluar_pares(mano_rival)
        if rival_pares == 1 and not su_tiene_pares:
            continue
        elif rival_pares == -1 and su_tiene_pares:
            continue
        
        su_estado = calcular_valor_juego(mano_rival)
        
        # 2. Filtro de Fase 
        if fase_confirmada and mi_estado["tiene_juego"] != su_estado["tiene_juego"]: 
            continue
            
        combinaciones_validas += 1

        # 3. Victorias/Derrotas cruzadas
        if mi_estado["tiene_juego"] and not su_estado["tiene_juego"]:
            victorias += 1
            continue
        elif not mi_estado["tiene_juego"] and su_estado["tiene_juego"]:
            derrotas += 1
            continue

        # 4. Misma fase: comparamos Rangos
        if mi_estado["rango"] > su_estado["rango"]: victorias += 1
        elif mi_estado["rango"] < su_estado["rango"]: derrotas += 1
        else:
            if soy_mano:
                victorias += 1
            else:
                derrotas += 1

    if combinaciones_validas == 0: return {"error": "No hay combinaciones válidas en este escenario."}
    
    return {
        "fase": "JUEGO" if mi_estado["tiene_juego"] else "PUNTO",
        "mi_suma": "31 REAL" if mi_estado["es_real"] else mi_estado["suma"],
        "prob_ganar": round((victorias / combinaciones_validas) * 100, 2),
        "prob_perder": round((derrotas / combinaciones_validas) * 100, 2)
    }

# --- Demostración del impacto del "Pares No" (-1) ---
mis_cartas = [12, 5, 4, 1]  # Llevas un Punto miserable de 20 (Rey, 5, 4, As)

print("Tienes 20 de Punto, asumiendo que el rival también tiene Punto:")
# Escenario 1: No sabemos nada (0)
res_incognita = calcular_probabilidad_juego(mis_cartas, rival_pares=0, fase_confirmada=True)
print(f"Prob. Ganar sin saber sus pares (0): {res_incognita['prob_ganar']}%")

# Escenario 2: Rival ha dicho "Pares NO" (-1)
res_sin_pares = calcular_probabilidad_juego(mis_cartas, rival_pares=-1, fase_confirmada=True)
print(f"Prob. Ganar si rival NO tiene pares (-1): {res_sin_pares['prob_ganar']}%")



#calculo de probabilidades con descartes grandes y chicas


import math
from itertools import combinations_with_replacement
from collections import Counter

def evaluar_descarte_grande_chica(mis_cartas, cartas_a_descartar, cartas_conocidas_fuera=None, soy_mano=True):
    """
    Simula el descarte de k cartas y calcula las probabilidades futuras de ganar a la Grande y Chica.
    mis_cartas: Lista de 4 cartas (ej: [12, 12, 4, 1])
    cartas_a_descartar: Lista con el subconjunto de cartas que vas a tirar (ej: [4, 1])
    """
    if cartas_conocidas_fuera is None:
        cartas_conocidas_fuera = []
        
    # 1. Normalizar cartas (los 3s son 12s, los 2s son 1s)
    mis_cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in mis_cartas]
    descartar_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_a_descartar]
    fuera_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_conocidas_fuera]
    
    # 2. Separar lo que me guardo
    guardadas = mis_cartas_norm.copy()
    for c in descartar_norm:
        if c in guardadas:
            guardadas.remove(c)
        else:
            raise ValueError(f"Error: Estás intentando descartar un {c} que no está en tu mano.")
            
    # 3. Construir el mazo de frecuencias
    mazo_completo = {12: 8, 11: 4, 10: 4, 7: 4, 6: 4, 5: 4, 4: 4, 1: 8}
    
    # Quitar mis 4 cartas iniciales (las guardadas me las quedo, las descartadas van al montón de descarte)
    for c in mis_cartas_norm:
        mazo_completo[c] -= 1
    # Quitar las otras cartas que sabemos que ya están descartadas previamente
    for c in fuera_norm:
        if mazo_completo[c] > 0:
            mazo_completo[c] -= 1

    k = len(descartar_norm) # Cantidad de cartas que voy a robar
    
    # Helper generador: saca todas las combinaciones de valores posibles y calcula sus permutaciones reales
    def generar_robos(num_cartas, mazo_disponible):
        if num_cartas == 0:
            yield (), 1, Counter()
            return
            
        cartas_validas = [c for c, count in mazo_disponible.items() if count > 0]
        for combo in combinations_with_replacement(cartas_validas, num_cartas):
            conteos = Counter(combo)
            valido = True
            formas = 1
            for carta, cantidad in conteos.items():
                if cantidad > mazo_disponible[carta]:
                    valido = False
                    break
                # Aplicamos combinatoria: N sobre K
                formas *= math.comb(mazo_disponible[carta], cantidad)
            if valido:
                yield combo, formas, conteos

    victorias_g, derrotas_g = 0, 0
    victorias_c, derrotas_c = 0, 0
    total_casos = 0
    
    # 4. Bucle Principal: Iterar sobre todos mis posibles robos
    for mi_robo, formas_mi_robo, conteo_robo in generar_robos(k, mazo_completo):
        mi_mano_final = guardadas + list(mi_robo)
        
        mi_g = sorted(mi_mano_final, reverse=True)
        mi_c = sorted(mi_mano_final) # Orden inverso para la chica
        
        # Mazo restante para el rival (el mazo menos lo que yo acabo de robar)
        mazo_para_rival = mazo_completo.copy()
        for carta, cantidad in conteo_robo.items():
            mazo_para_rival[carta] -= cantidad
            
        # 5. Sub-bucle: Iterar sobre las posibles manos del rival
        for su_mano, formas_su_mano, _ in generar_robos(4, mazo_para_rival):
            # La cantidad de universos en los que ocurre este escenario exacto
            casos_escenario = formas_mi_robo * formas_su_mano
            total_casos += casos_escenario
            
            su_g = sorted(su_mano, reverse=True)
            su_c = sorted(su_mano)
            
            # Evaluación de la GRANDE
            for m, s in zip(mi_g, su_g):
                if m > s:
                    victorias_g += casos_escenario
                    break
                elif m < s:
                    derrotas_g += casos_escenario
                    break
            else: # Empate (gana la mano)
                if soy_mano: victorias_g += casos_escenario
                else: derrotas_g += casos_escenario
                    
            # Evaluación de la CHICA
            for m, s in zip(mi_c, su_c):
                if m < s:
                    victorias_c += casos_escenario
                    break
                elif m > s:
                    derrotas_c += casos_escenario
                    break
            else: # Empate (gana la mano)
                if soy_mano: victorias_c += casos_escenario
                else: derrotas_c += casos_escenario
                
    return {
        "cartas_guardadas": sorted(guardadas, reverse=True),
        "robo_cartas": k,
        "prob_ganar_grande": round(victorias_g / total_casos * 100, 2),
        "prob_perder_grande": round(derrotas_g / total_casos * 100, 2),
        "prob_ganar_chica": round(victorias_c / total_casos * 100, 2),
        "prob_perder_chica": round(derrotas_c / total_casos * 100, 2)
    }

# --- Prueba del algoritmo de descartes ---
mis_cartas_iniciales = [12, 12, 4, 1]  # Dos Reyes, un 4, un As

# Decides romper la pareja quedándote solo con los Reyes y tirando el 4 y el As.
# Quieres ver qué pasa si haces esto siendo mano.
resultados = evaluar_descarte_grande_chica(
    mis_cartas=mis_cartas_iniciales, 
    cartas_a_descartar=[4, 1], 
    soy_mano=True
)

print(f"Me guardo: {resultados['cartas_guardadas']} (Robaré {resultados['robo_cartas']} cartas)")
print(f"--- EXPECTATIVA PARA LA GRANDE ---")
print(f"Ganar:  {resultados['prob_ganar_grande']}%")
print(f"Perder: {resultados['prob_perder_grande']}%")
print(f"--- EXPECTATIVA PARA LA CHICA ---")
print(f"Ganar:  {resultados['prob_ganar_chica']}%")
print(f"Perder: {resultados['prob_perder_chica']}%")



#calculo de probabilidades con descartes pares y juego

import math
from itertools import combinations_with_replacement
from collections import Counter

# --- FUNCIONES AUXILIARES ---
def evaluar_pares(mano):
    conteos = Counter(mano)
    pares = [(count, carta) for carta, count in conteos.items() if count >= 2]
    if not pares: return (0, (0,))
    pares.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if pares[0][0] == 4: return (3, (pares[0][1], pares[0][1]))
    elif len(pares) == 2 and pares[0][0] == 2 and pares[1][0] == 2: return (3, (pares[0][1], pares[1][1]))
    elif pares[0][0] == 3: return (2, (pares[0][1],))
    elif pares[0][0] == 2: return (1, (pares[0][1],))

def calcular_valor_juego(mano):
    suma = sum([10 if c >= 10 else c for c in mano])
    es_real = (mano.count(7) == 3 and mano.count(10) == 1)
    if suma >= 31:
        rango = 9 if es_real else {31: 8, 32: 7, 40: 6, 37: 5, 36: 4, 35: 3, 34: 2, 33: 1}.get(suma, 0)
        return {"tiene_juego": True, "suma": suma, "rango": rango}
    else:
        return {"tiene_juego": False, "suma": suma, "rango": suma}


# --- MOTOR PRINCIPAL ---
def evaluar_descarte_pares_juego(mis_cartas, cartas_a_descartar, cartas_conocidas_fuera=None, soy_mano=True):
    if cartas_conocidas_fuera is None: cartas_conocidas_fuera = []
    
    mis_cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in mis_cartas]
    descartar_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_a_descartar]
    fuera_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_conocidas_fuera]
    
    guardadas = mis_cartas_norm.copy()
    for c in descartar_norm:
        if c in guardadas: guardadas.remove(c)
        else: raise ValueError(f"Error: No tienes un {c} para descartar.")
            
    mazo_completo = {12: 8, 11: 4, 10: 4, 7: 4, 6: 4, 5: 4, 4: 4, 1: 8}
    for c in mis_cartas_norm + fuera_norm:
        if mazo_completo[c] > 0: mazo_completo[c] -= 1

    k = len(descartar_norm)
    
    def generar_robos(num_cartas, mazo_disponible):
        if num_cartas == 0:
            yield (), 1, Counter()
            return
        cartas_validas = [c for c, count in mazo_disponible.items() if count > 0]
        for combo in combinations_with_replacement(cartas_validas, num_cartas):
            conteos = Counter(combo)
            valido, formas = True, 1
            for carta, cantidad in conteos.items():
                if cantidad > mazo_disponible[carta]:
                    valido = False; break
                formas *= math.comb(mazo_disponible[carta], cantidad)
            if valido: yield combo, formas, conteos

    # Contadores
    total_casos = 0
    vic_pares, der_pares, sin_pares_mesa = 0, 0, 0
    vic_juego, der_juego, casos_juego = 0, 0, 0
    vic_punto, der_punto, casos_punto = 0, 0, 0
    
    for mi_robo, formas_mi, conteo_robo in generar_robos(k, mazo_completo):
        mi_mano_final = guardadas + list(mi_robo)
        mi_cat, mi_val = evaluar_pares(mi_mano_final)
        mi_estado = calcular_valor_juego(mi_mano_final)
        
        mazo_para_rival = mazo_completo.copy()
        for carta, cantidad in conteo_robo.items(): mazo_para_rival[carta] -= cantidad
            
        for su_mano, formas_su, _ in generar_robos(4, mazo_para_rival):
            casos = formas_mi * formas_su
            total_casos += casos
            
            su_cat, su_val = evaluar_pares(su_mano)
            su_estado = calcular_valor_juego(su_mano)
            
            # --- EVALUACIÓN DE PARES ---
            if mi_cat == 0 and su_cat == 0:
                sin_pares_mesa += casos
            elif mi_cat > su_cat: vic_pares += casos
            elif mi_cat < su_cat: der_pares += casos
            else: # Empate de categoría
                if mi_val > su_val: vic_pares += casos
                elif mi_val < su_val: der_pares += casos
                else: # Empate técnico, gana mano
                    if soy_mano: vic_pares += casos
                    else: der_pares += casos
                        
            # --- EVALUACIÓN DE JUEGO / PUNTO ---
            if mi_estado["tiene_juego"] or su_estado["tiene_juego"]:
                casos_juego += casos
                if mi_estado["tiene_juego"] and not su_estado["tiene_juego"]: vic_juego += casos
                elif su_estado["tiene_juego"] and not mi_estado["tiene_juego"]: der_juego += casos
                else: # Ambos tienen juego
                    if mi_estado["rango"] > su_estado["rango"]: vic_juego += casos
                    elif mi_estado["rango"] < su_estado["rango"]: der_juego += casos
                    else:
                        if soy_mano: vic_juego += casos
                        else: der_juego += casos
            else:
                casos_punto += casos
                if mi_estado["rango"] > su_estado["rango"]: vic_punto += casos
                elif mi_estado["rango"] < su_estado["rango"]: der_punto += casos
                else:
                    if soy_mano: vic_punto += casos
                    else: der_punto += casos

    # Evitar divisiones por 0
    if casos_juego == 0: casos_juego = 1 
    if casos_punto == 0: casos_punto = 1

    return {
        "cartas_guardadas": sorted(guardadas, reverse=True),
        "robo_cartas": k,
        "total_universos": total_casos,
        # PARES
        "pares_prob_ganar_absoluta": round(vic_pares / total_casos * 100, 2),
        "pares_prob_perder_absoluta": round(der_pares / total_casos * 100, 2),
        "pares_prob_nadie_tiene": round(sin_pares_mesa / total_casos * 100, 2),
        # JUEGO
        "prob_que_haya_juego": round(casos_juego / total_casos * 100, 2),
        "juego_prob_ganar_si_lo_hay": round(vic_juego / casos_juego * 100, 2),
        # PUNTO
        "prob_que_haya_punto": round(casos_punto / total_casos * 100, 2),
        "punto_prob_ganar_si_lo_hay": round(vic_punto / casos_punto * 100, 2),
    }

# --- Prueba del algoritmo ---
# Tienes dos Reyes, un As y un 4. (Par de Reyes y Punto asqueroso)
mis_cartas = [12, 12, 1, 4]

# Decides guardarte solo los Reyes y tirar el 1 y el 4 buscando mejorar pares o pillar Juego.
resultados = evaluar_descarte_pares_juego(mis_cartas, cartas_a_descartar=[1, 4], soy_mano=True)

print(f"Me guardo: {resultados['cartas_guardadas']} (Robo {resultados['robo_cartas']} cartas siendo Mano)")
print(f"Analizados {resultados['total_universos']:,} universos paralelos.\n")

print(f"--- EXPECTATIVA PARA LOS PARES ---")
print(f"Prob. de ganar los Pares: {resultados['pares_prob_ganar_absoluta']}%")
print(f"Prob. de perderlos:       {resultados['pares_prob_perder_absoluta']}%")
print(f"Prob. de que nadie tenga: {resultados['pares_prob_nadie_tiene']}%\n")

print(f"--- EXPECTATIVA PARA EL JUEGO ---")
print(f"Habrá Juego en la mesa en el {resultados['prob_que_haya_juego']}% de los casos.")
print(f"-> Si hay Juego, tu prob. de ganarlo es: {resultados['juego_prob_ganar_si_lo_hay']}%\n")

print(f"--- EXPECTATIVA PARA EL PUNTO ---")
print(f"Iremos al Punto en el {resultados['prob_que_haya_punto']}% de los casos.")
print(f"-> Si vamos al Punto, tu prob. de ganarlo es: {resultados['punto_prob_ganar_si_lo_hay']}%")