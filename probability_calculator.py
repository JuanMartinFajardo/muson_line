import math
import itertools
from itertools import combinations_with_replacement
from collections import Counter

# ==========================================
# FUNCIONES AUXILIARES GLOBALES
# ==========================================

def evaluar_pares(mano):
    """Devuelve (Categoria, (Valores)). Categorías: 3=Duples, 2=Medias, 1=Par, 0=Nada"""
    conteos = Counter(mano)
    pares = [(count, carta) for carta, count in conteos.items() if count >= 2]
    if not pares: 
        return (0, (0,))
    
    pares.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if pares[0][0] == 4: 
        return (3, (pares[0][1], pares[0][1]))
    elif len(pares) == 2 and pares[0][0] == 2 and pares[1][0] == 2: 
        return (3, (pares[0][1], pares[1][1]))
    elif pares[0][0] == 3: 
        return (2, (pares[0][1],))
    elif pares[0][0] == 2: 
        return (1, (pares[0][1],))

def calcular_valor_juego(mano):
    """Calcula la suma, rango y si es 31 Real."""
    suma = sum([10 if c >= 10 else c for c in mano])
    es_real = (mano.count(7) == 3 and mano.count(10) == 1)
    
    if suma >= 31:
        rango = 9 if es_real else {31: 8, 32: 7, 40: 6, 37: 5, 36: 4, 35: 3, 34: 2, 33: 1}.get(suma, 0)
        return {"tiene_juego": True, "suma": suma, "rango": rango, "es_real": es_real}
    else:
        return {"tiene_juego": False, "suma": suma, "rango": suma, "es_real": False}

def generar_robos(num_cartas, mazo_disponible):
    """Generador matemático para calcular permutaciones de robos sin explosión combinatoria."""
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
            # Combinatoria real: N sobre K
            formas *= math.comb(mazo_disponible[carta], cantidad)
        if valido:
            yield combo, formas, conteos

# ==========================================
# PROBABILIDADES FASE A FASE (SIN DESCARTAR)
# ==========================================

def calcular_probabilidad_grande(mis_cartas, cartas_conocidas_fuera=None, soy_mano=True):
    if cartas_conocidas_fuera is None: cartas_conocidas_fuera = []

    mis_cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in mis_cartas]
    mis_cartas_norm.sort(reverse=True)
    descartadas_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_conocidas_fuera]

    mazo_restante = ([12]*8 + [11]*4 + [10]*4 + [7]*4 + [6]*4 + [5]*4 + [4]*4 + [1]*8)

    for carta in mis_cartas_norm + descartadas_norm:
        if carta in mazo_restante: mazo_restante.remove(carta)

    victorias, derrotas = 0, 0

    for mano_rival in itertools.combinations(mazo_restante, 4):
        rival_ordenada = sorted(mano_rival, reverse=True)
        for mi_carta, su_carta in zip(mis_cartas_norm, rival_ordenada):
            if mi_carta > su_carta:
                victorias += 1; break
            elif su_carta > mi_carta:
                derrotas += 1; break
        else:
            if soy_mano: victorias += 1
            else: derrotas += 1

    total_combinaciones = victorias + derrotas
    return {
        "victorias": victorias, "derrotas": derrotas,
        "prob_ganar": round((victorias / total_combinaciones) * 100, 2),
        "prob_perder": round((derrotas / total_combinaciones) * 100, 2)
    }

def calcular_probabilidad_chica(mis_cartas, cartas_conocidas_fuera=None, soy_mano=True):
    if cartas_conocidas_fuera is None: cartas_conocidas_fuera = []

    mis_cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in mis_cartas]
    mis_cartas_norm.sort()
    descartadas_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_conocidas_fuera]

    mazo_restante = ([12]*8 + [11]*4 + [10]*4 + [7]*4 + [6]*4 + [5]*4 + [4]*4 + [1]*8)

    for carta in mis_cartas_norm + descartadas_norm:
        if carta in mazo_restante: mazo_restante.remove(carta)

    victorias, derrotas = 0, 0

    for mano_rival in itertools.combinations(mazo_restante, 4):
        rival_ordenada = sorted(mano_rival)
        for mi_carta, su_carta in zip(mis_cartas_norm, rival_ordenada):
            if mi_carta < su_carta:
                victorias += 1; break
            elif su_carta < mi_carta:
                derrotas += 1; break
        else:
            if soy_mano: victorias += 1
            else: derrotas += 1

    total_combinaciones = victorias + derrotas
    return {
        "victorias": victorias, "derrotas": derrotas,
        "prob_ganar": round((victorias / total_combinaciones) * 100, 2),
        "prob_perder": round((derrotas / total_combinaciones) * 100, 2)
    }

def calcular_probabilidad_pares(mis_cartas, rival_pares=False, soy_mano=True, cartas_conocidas_fuera=None):
    if cartas_conocidas_fuera is None: cartas_conocidas_fuera = []
    
    mis_cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in mis_cartas]
    descartadas_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_conocidas_fuera]
    mi_categoria, mi_valor = evaluar_pares(mis_cartas_norm)
    
    mazo_restante = ([12]*8 + [11]*4 + [10]*4 + [7]*4 + [6]*4 + [5]*4 + [4]*4 + [1]*8)
    for carta in mis_cartas_norm + descartadas_norm:
        mazo_restante.remove(carta)

    victorias, derrotas, combinaciones_validas = 0, 0, 0

    for mano_rival in itertools.combinations(mazo_restante, 4):
        su_categoria, su_valor = evaluar_pares(mano_rival)
        if rival_pares and su_categoria == 0: continue
        combinaciones_validas += 1

        if mi_categoria == 0:
            if su_categoria > 0: derrotas += 1
            else: 
                if soy_mano: victorias += 1 
                else: derrotas += 1
            continue

        if mi_categoria > su_categoria: victorias += 1
        elif mi_categoria < su_categoria: derrotas += 1
        else:
            if mi_valor > su_valor: victorias += 1
            elif mi_valor < su_valor: derrotas += 1
            else:
                if soy_mano: victorias += 1
                else: derrotas += 1

    if combinaciones_validas == 0: return {"error": "Sin combinaciones"}
    return {
        "victorias": victorias, "derrotas": derrotas,
        "prob_ganar": round((victorias / combinaciones_validas) * 100, 2)
    }

def calcular_probabilidad_juego(mis_cartas, rival_pares=0, fase_confirmada=False, soy_mano=True, cartas_conocidas_fuera=None):
    """rival_pares: 1 (Tiene), 0 (No sabemos), -1 (No tiene)"""
    if cartas_conocidas_fuera is None: cartas_conocidas_fuera = []
    
    mis_cartas_norm = [12 if c == 3 else 1 if c == 2 else c for c in mis_cartas]
    descartadas_norm = [12 if c == 3 else 1 if c == 2 else c for c in cartas_conocidas_fuera]
    mi_estado = calcular_valor_juego(mis_cartas_norm)

    mazo_restante = ([12]*8 + [11]*4 + [10]*4 + [7]*4 + [6]*4 + [5]*4 + [4]*4 + [1]*8)
    for carta in mis_cartas_norm + descartadas_norm:
        mazo_restante.remove(carta)

    victorias, derrotas, combinaciones_validas = 0, 0, 0

    for mano_rival in itertools.combinations(mazo_restante, 4):
        # 1. Filtro de Pares (-1, 0, 1) usando la tupla de evaluar_pares
        su_tiene_pares = evaluar_pares(mano_rival)[0] > 0
        if rival_pares == 1 and not su_tiene_pares: continue
        elif rival_pares == -1 and su_tiene_pares: continue
        
        su_estado = calcular_valor_juego(mano_rival)
        
        # 2. Filtro de Fase 
        if fase_confirmada and mi_estado["tiene_juego"] != su_estado["tiene_juego"]: continue
            
        combinaciones_validas += 1

        # 3. Victorias/Derrotas cruzadas
        if mi_estado["tiene_juego"] and not su_estado["tiene_juego"]:
            victorias += 1; continue
        elif not mi_estado["tiene_juego"] and su_estado["tiene_juego"]:
            derrotas += 1; continue

        # 4. Misma fase: comparamos Rangos
        if mi_estado["rango"] > su_estado["rango"]: victorias += 1
        elif mi_estado["rango"] < su_estado["rango"]: derrotas += 1
        else:
            if soy_mano: victorias += 1
            else: derrotas += 1

    if combinaciones_validas == 0: return {"error": "No hay combinaciones válidas en este escenario."}
    
    return {
        "fase": "JUEGO" if mi_estado["tiene_juego"] else "PUNTO",
        "mi_suma": "31 REAL" if mi_estado["es_real"] else mi_estado["suma"],
        "prob_ganar": round((victorias / combinaciones_validas) * 100, 2),
        "prob_perder": round((derrotas / combinaciones_validas) * 100, 2)
    }


# ==========================================
# CÁLCULOS DE VALOR ESPERADO (DESCARTES)
# ==========================================

def evaluar_descarte_grande_chica(mis_cartas, cartas_a_descartar, cartas_conocidas_fuera=None, soy_mano=True):
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
    victorias_g, derrotas_g, victorias_c, derrotas_c, total_casos = 0, 0, 0, 0, 0
    
    for mi_robo, formas_mi_robo, conteo_robo in generar_robos(k, mazo_completo):
        mi_mano_final = guardadas + list(mi_robo)
        mi_g = sorted(mi_mano_final, reverse=True)
        mi_c = sorted(mi_mano_final)
        
        mazo_para_rival = mazo_completo.copy()
        for carta, cantidad in conteo_robo.items():
            mazo_para_rival[carta] -= cantidad
            
        for su_mano, formas_su_mano, _ in generar_robos(4, mazo_para_rival):
            casos_escenario = formas_mi_robo * formas_su_mano
            total_casos += casos_escenario
            
            su_g = sorted(su_mano, reverse=True)
            su_c = sorted(su_mano)
            
            # Evaluación GRANDE
            for m, s in zip(mi_g, su_g):
                if m > s: victorias_g += casos_escenario; break
                elif m < s: derrotas_g += casos_escenario; break
            else: 
                if soy_mano: victorias_g += casos_escenario
                else: derrotas_g += casos_escenario
                    
            # Evaluación CHICA
            for m, s in zip(mi_c, su_c):
                if m < s: victorias_c += casos_escenario; break
                elif m > s: derrotas_c += casos_escenario; break
            else: 
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
            
            # --- EVALUACIÓN PARES ---
            if mi_cat == 0 and su_cat == 0: sin_pares_mesa += casos
            elif mi_cat > su_cat: vic_pares += casos
            elif mi_cat < su_cat: der_pares += casos
            else: 
                if mi_val > su_val: vic_pares += casos
                elif mi_val < su_val: der_pares += casos
                else: 
                    if soy_mano: vic_pares += casos
                    else: der_pares += casos
                        
            # --- EVALUACIÓN JUEGO / PUNTO ---
            if mi_estado["tiene_juego"] or su_estado["tiene_juego"]:
                casos_juego += casos
                if mi_estado["tiene_juego"] and not su_estado["tiene_juego"]: vic_juego += casos
                elif su_estado["tiene_juego"] and not mi_estado["tiene_juego"]: der_juego += casos
                else:
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

    if casos_juego == 0: casos_juego = 1 
    if casos_punto == 0: casos_punto = 1

    return {
        "cartas_guardadas": sorted(guardadas, reverse=True),
        "robo_cartas": k,
        "total_universos": total_casos,
        "pares_prob_ganar_absoluta": round(vic_pares / total_casos * 100, 2),
        "pares_prob_perder_absoluta": round(der_pares / total_casos * 100, 2),
        "pares_prob_nadie_tiene": round(sin_pares_mesa / total_casos * 100, 2),
        "prob_que_haya_juego": round(casos_juego / total_casos * 100, 2),
        "juego_prob_ganar_si_lo_hay": round(vic_juego / casos_juego * 100, 2),
        "prob_que_haya_punto": round(casos_punto / total_casos * 100, 2),
        "punto_prob_ganar_si_lo_hay": round(vic_punto / casos_punto * 100, 2),
    }


# ==========================================
# PRUEBAS DE EJECUCIÓN
# ==========================================

if __name__ == "__main__":
    print("\n" + "="*40)
    print("1. PRUEBA DE PEDRETES (LA GRANDE)")
    print("="*40)
    mis_cartas = [12, 10, 7, 1]
    res_sin = calcular_probabilidad_grande(mis_cartas)
    res_con = calcular_probabilidad_grande(mis_cartas, cartas_conocidas_fuera=[4, 5, 6])
    print(f"Sin descartes vistos: Ganar {res_sin['prob_ganar']}%")
    print(f"Sabiendo que 4,5,6 están fuera: Ganar {res_con['prob_ganar']}%")

    print("\n" + "="*40)
    print("2. PRUEBA DE CHICA")
    print("="*40)
    mis_cartas = [1, 1, 4, 12]
    descartes = [11, 7]
    res_chica = calcular_probabilidad_chica(mis_cartas, descartes)
    print(f"Ganar: {res_chica['prob_ganar']}% | Perder: {res_chica['prob_perder']}%")

    print("\n" + "="*40)
    print("3. PRUEBA DE JUEGO / PUNTO")
    print("="*40)
    mis_cartas = [12, 5, 4, 1] 
    print("Tienes 20 de Punto, asumiendo que el rival también tiene Punto:")
    res_incognita = calcular_probabilidad_juego(mis_cartas, rival_pares=0, fase_confirmada=True)
    res_sin_pares = calcular_probabilidad_juego(mis_cartas, rival_pares=-1, fase_confirmada=True)
    print(f"Ganar sin saber sus pares (0): {res_incognita['prob_ganar']}%")
    print(f"Ganar si rival NO tiene pares (-1): {res_sin_pares['prob_ganar']}%")

    print("\n" + "="*40)
    print("4. PRUEBA DE DESCARTES (GRANDE Y CHICA)")
    print("="*40)
    mis_cartas_iniciales = [12, 12, 4, 1]
    res_desc_gc = evaluar_descarte_grande_chica(mis_cartas_iniciales, [4, 1], soy_mano=True)
    print(f"Me guardo: {res_desc_gc['cartas_guardadas']} y robo {res_desc_gc['robo_cartas']}")
    print(f"Grande -> Ganar: {res_desc_gc['prob_ganar_grande']}%")
    print(f"Chica  -> Ganar: {res_desc_gc['prob_ganar_chica']}%")

    print("\n" + "="*40)
    print("5. PRUEBA DE DESCARTES (PARES Y JUEGO)")
    print("="*40)
    mis_cartas = [12, 12, 1, 4]
    res_desc_pj = evaluar_descarte_pares_juego(mis_cartas, [1, 4], soy_mano=True)
    print(f"Me guardo: {res_desc_pj['cartas_guardadas']} y robo {res_desc_pj['robo_cartas']}")
    print(f"Pares -> Ganar: {res_desc_pj['pares_prob_ganar_absoluta']}%")
    print(f"Juego -> Probabilidad de que haya: {res_desc_pj['prob_que_haya_juego']}% (Ganarlo: {res_desc_pj['juego_prob_ganar_si_lo_hay']}%)")