# ==========================================================================
# rig.py — El plató compartido. Se ejecuta DENTRO de Blender.
# --------------------------------------------------------------------------
# Todo lo que el DECK_SPEC declara "no negociable" vive aquí: la escena, la
# cámara ortográfica, las tres luces, el marco con sus numerales, el volcado a
# PNG. Un tema no toca nada de esto; recibe un `Contexto` y sólo añade cosas a
# las colecciones BG e INTERIOR.
#
# La regla de oro del §5 es que `view_transform = Standard`, así que un shader
# de emisión con `hex_a_lineal(x)` sale del render valiendo exactamente `x`.
# Por eso los fondos son emisión (color exacto) y los sujetos son Principled
# (los ilumina el rig, que es lo que les da el relieve).
# ==========================================================================

import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec   # noqa: E402


# ==========================================================================
# 1. Escena
# ==========================================================================

def _motor_eevee():
    """EEVEE se llama distinto según la versión de Blender (4.2 lo partió en
    'NEXT', 5.x volvió a unificarlo). Se elige el que exista."""
    disponibles = {e.identifier for e in
                   bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items}
    for nombre in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        if nombre in disponibles:
            return nombre
    return 'CYCLES'


class Contexto:
    """Lo que se le pasa a un tema para que construya una carta."""

    def __init__(self, escena, colecciones, pieza, semilla=0):
        self.escena = escena
        self.col = colecciones            # {'BG','INTERIOR','FRAME','LIGHTS','CAM'}
        self.pieza = pieza                # '01'…'12' o 'back'
        self.rnd = random.Random(semilla)

    # --- azúcar para los temas ---
    def anadir(self, obj, capa='INTERIOR'):
        self.col[capa].objects.link(obj)
        return obj


def escena_limpia():
    """Documento vacío con las cinco colecciones del §2, en orden."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    escena = bpy.context.scene

    colecciones = {}
    for nombre in ('BG', 'INTERIOR', 'FRAME', 'LIGHTS', 'CAM'):
        col = bpy.data.collections.new(nombre)
        escena.collection.children.link(col)
        colecciones[nombre] = col

    escena.render.engine = _motor_eevee()
    escena.render.resolution_x = spec.ANCHO_RENDER
    escena.render.resolution_y = spec.ALTO_RENDER
    escena.render.resolution_percentage = 100
    escena.render.film_transparent = True
    escena.render.image_settings.file_format = 'PNG'
    escena.render.image_settings.color_mode = 'RGBA'
    escena.render.image_settings.color_depth = '8'

    # Gestión de color: los hex de los temas son valores de salida literales.
    escena.view_settings.view_transform = spec.RENDER['view_transform']
    try:
        escena.view_settings.look = spec.RENDER['look']
    except Exception:
        pass
    escena.view_settings.exposure = spec.RENDER['exposicion']
    escena.view_settings.gamma = spec.RENDER['gamma']

    _ajustes_motor(escena)
    return escena, colecciones


def _ajustes_motor(escena):
    """Muestras, sombras suaves y oclusión ambiental. Los nombres de estas
    propiedades han cambiado varias veces entre versiones de EEVEE, así que
    cada una se pone dentro de su try: que falte una no debe tumbar el render."""
    ee = getattr(escena, 'eevee', None)
    if ee is None:
        return
    for atributo, valor in (
        ('taa_render_samples', spec.RENDER['muestras']),
        ('use_shadows', True),
        ('use_soft_shadows', True),
        ('use_gtao', True),                                  # EEVEE legacy
        ('gtao_distance', spec.RENDER['ao_distancia']),
        ('gtao_factor', spec.RENDER['ao_factor']),
        ('use_raytracing', True),                            # EEVEE Next
        ('fast_gi_distance', spec.RENDER['ao_distancia']),
        ('use_bloom', False),
    ):
        try:
            setattr(ee, atributo, valor)
        except Exception:
            pass


def camara(escena, col):
    datos = bpy.data.cameras.new('CAM')
    datos.type = spec.CAMARA['tipo']
    datos.ortho_scale = spec.CAMARA['ortho_scale']
    obj = bpy.data.objects.new('CAM', datos)
    obj.location = spec.CAMARA['loc']
    obj.rotation_euler = spec.CAMARA['rot']
    col.objects.link(obj)
    escena.camera = obj
    return obj


def luces(col, potencia=1.0):
    """Las tres áreas del §5, todas apuntando al origen. `potencia` es el único
    grado de libertad que tiene un tema: sube o baja el vataje absoluto para
    que su fondo caiga donde ha dicho, sin tocar las proporciones."""
    creadas = {}
    for nombre, cfg in spec.LUCES.items():
        datos = bpy.data.lights.new(nombre, 'AREA')
        datos.size = cfg['tamano']
        datos.energy = spec.POTENCIA_BASE * cfg['factor'] * potencia
        obj = bpy.data.objects.new(nombre, datos)
        obj.location = cfg['loc']
        _mirar_al_origen(obj)
        col.objects.link(obj)
        creadas[nombre] = obj
    return creadas


def _mirar_al_origen(obj):
    x, y, z = obj.location
    direccion = -1 if z >= 0 else 1        # la RIM está por detrás y mira a +Z
    distancia_xy = math.hypot(x, y)
    obj.rotation_euler = (
        math.atan2(distancia_xy, abs(z)) * (1 if direccion == -1 else -1),
        0.0,
        math.atan2(y, x) + math.pi / 2,
    )


# ==========================================================================
# 2. Materiales
# ==========================================================================

def material_plano(nombre, hex_color, alfa=1.0):
    """Color exacto, sin iluminación. Para fondos y siluetas planas: es lo
    único que garantiza que el hex del tema sale tal cual (§5)."""
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nodos = mat.node_tree.nodes
    enlaces = mat.node_tree.links
    nodos.clear()

    salida = nodos.new('ShaderNodeOutputMaterial')
    emision = nodos.new('ShaderNodeEmission')
    emision.inputs['Color'].default_value = spec.hex_a_lineal(hex_color, 1.0)
    emision.inputs['Strength'].default_value = 1.0

    if alfa >= 1.0:
        enlaces.new(emision.outputs['Emission'], salida.inputs['Surface'])
    else:
        mezcla = nodos.new('ShaderNodeMixShader')
        transp = nodos.new('ShaderNodeBsdfTransparent')
        mezcla.inputs['Fac'].default_value = alfa
        enlaces.new(transp.outputs['BSDF'], mezcla.inputs[1])
        enlaces.new(emision.outputs['Emission'], mezcla.inputs[2])
        enlaces.new(mezcla.outputs['Shader'], salida.inputs['Surface'])
        mat.blend_method = 'BLEND'
    return mat


def material_gradiente(nombre, hex_arriba, hex_abajo, eje='Y'):
    """Rampa de dos paradas a lo largo de la carta. Fondo de bajo detalle, que
    es exactamente lo que pide el §6 para no reventar el peso en webp."""
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nodos = mat.node_tree.nodes
    enlaces = mat.node_tree.links
    nodos.clear()

    salida = nodos.new('ShaderNodeOutputMaterial')
    emision = nodos.new('ShaderNodeEmission')
    coord = nodos.new('ShaderNodeTexCoord')
    separar = nodos.new('ShaderNodeSeparateXYZ')
    rango = nodos.new('ShaderNodeMapRange')
    rampa = nodos.new('ShaderNodeValToRGB')

    limite = spec.MEDIO_Y if eje == 'Y' else spec.MEDIO_X
    rango.inputs['From Min'].default_value = -limite
    rango.inputs['From Max'].default_value = limite
    rampa.color_ramp.elements[0].color = spec.hex_a_lineal(hex_abajo, 1.0)
    rampa.color_ramp.elements[1].color = spec.hex_a_lineal(hex_arriba, 1.0)

    enlaces.new(coord.outputs['Object'], separar.inputs['Vector'])
    enlaces.new(separar.outputs[eje], rango.inputs['Value'])
    enlaces.new(rango.outputs['Result'], rampa.inputs['Fac'])
    enlaces.new(rampa.outputs['Color'], emision.inputs['Color'])
    enlaces.new(emision.outputs['Emission'], salida.inputs['Surface'])
    return mat


def material_pbr(nombre, hex_color, rugosidad=0.5, metalico=0.0, alfa=1.0):
    """Superficie iluminada por el rig. Es la que da el relieve: el bisel del
    marco y la pinta se leen porque la KEY las roza."""
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = spec.hex_a_lineal(hex_color, 1.0)
    bsdf.inputs['Roughness'].default_value = rugosidad
    bsdf.inputs['Metallic'].default_value = metalico
    if alfa < 1.0:
        bsdf.inputs['Alpha'].default_value = alfa
        mat.blend_method = 'BLEND'
    return mat


def poner_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj


# ==========================================================================
# 3. Geometría
# ==========================================================================

def puntos_rect_redondeado(ancho, alto, radio, segmentos=8, centro=(0.0, 0.0)):
    """Contorno de un rectángulo de esquinas redondeadas, en sentido antihorario.

    Devuelve siempre el mismo número de puntos para el mismo `segmentos`, que es
    lo que permite coser dos contornos en un anillo (el marco) sin sorpresas.
    """
    cx, cy = centro
    mx, my = ancho / 2 - radio, alto / 2 - radio
    radio = max(radio, 1e-6)
    puntos = []
    esquinas = [(mx, my, 0.0), (-mx, my, 90.0), (-mx, -my, 180.0), (mx, -my, 270.0)]
    for ex, ey, base in esquinas:
        for i in range(segmentos + 1):
            ang = math.radians(base + 90.0 * i / segmentos)
            puntos.append((cx + ex + radio * math.cos(ang),
                           cy + ey + radio * math.sin(ang)))
    return puntos


def malla_poligono(nombre, puntos, z=0.0, col=None):
    """Un polígono relleno (ngon) en el plano XY, a la altura z."""
    malla = bpy.data.meshes.new(nombre)
    verts = [(x, y, z) for x, y in puntos]
    malla.from_pydata(verts, [], [list(range(len(verts)))])
    malla.update()
    obj = bpy.data.objects.new(nombre, malla)
    if col:
        col.objects.link(obj)
    return obj


def forma(nombre, contornos, z=0.0, grosor=0.02, bisel=0.004, suave=False,
          col=None):
    """Silueta rellena a partir de uno o varios contornos. **Es la herramienta
    principal de todo el sistema.**

    Se construye como una curva 2D de Blender, no como un ngon, y la diferencia
    no es cosmética: un ngon sólo rellena bien un polígono convexo — una figura
    con cintura, con un brazo o con un hueco sale hecha un borrón. La curva 2D
    triangula de verdad, entiende varios contornos por la regla par-impar (el
    primero es la forma, los siguientes son agujeros) y, con `suave`, interpola
    una bezier por los puntos de control: seis puntos dan una curva orgánica
    limpia donde un polígono necesitaría cuarenta y aun así se vería facetado.

    `grosor` sale de `extrude` y `bisel` de `bevel_depth`, así que el relieve y
    el canto redondeado del §4.1 salen sin modificadores que aplicar después.
    """
    if contornos and isinstance(contornos[0], (tuple, list)) and \
            len(contornos[0]) == 2 and isinstance(contornos[0][0], (int, float)):
        contornos = [contornos]          # se ha pasado un solo contorno

    datos = bpy.data.curves.new(nombre, 'CURVE')
    datos.dimensions = '2D'
    datos.fill_mode = 'BOTH'
    datos.resolution_u = 6
    if grosor:
        datos.extrude = grosor / 2.0
    if bisel:
        datos.bevel_depth = bisel
        datos.bevel_resolution = 2

    for contorno in contornos:
        if len(contorno) < 3:
            continue
        if suave:
            spline = datos.splines.new('BEZIER')
            spline.bezier_points.add(len(contorno) - 1)
            for punto, (x, y) in zip(spline.bezier_points, contorno):
                punto.co = (x, y, 0.0)
                punto.handle_left_type = 'AUTO'
                punto.handle_right_type = 'AUTO'
        else:
            spline = datos.splines.new('POLY')
            spline.points.add(len(contorno) - 1)
            for punto, (x, y) in zip(spline.points, contorno):
                punto.co = (x, y, 0.0, 1.0)
        spline.use_cyclic_u = True

    obj = bpy.data.objects.new(nombre, datos)
    obj.location.z = z
    if col:
        col.objects.link(obj)
    return obj


def a_malla(obj):
    """Convierte una curva en malla. Necesario antes de duplicar en enlazado o
    de unir varias piezas en una sola."""
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if obj.type == 'CURVE':
        bpy.ops.object.convert(target='MESH')
        obj = bpy.context.view_layer.objects.active
    return obj


def unir(objetos, nombre):
    """Funde varias piezas en una sola malla, para que el patrón de pintas
    pueda duplicarla en enlazado (§6.5) y para que la silueta se lea como un
    contorno continuo y no como un montón de recortes."""
    objetos = [a_malla(o) for o in objetos if o]
    if not objetos:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objetos:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objetos[0]
    if len(objetos) > 1:
        bpy.ops.object.join()
    unido = bpy.context.view_layer.objects.active
    unido.name = nombre
    return unido


def malla_anillo(nombre, exterior, interior, z=0.0, col=None):
    """Cose dos contornos del mismo número de puntos en una banda cerrada.
    Es el marco del §3: un bucle continuo, sin interrupciones."""
    n = len(exterior)
    assert n == len(interior), 'los dos contornos deben tener el mismo tamaño'
    verts = [(x, y, z) for x, y in exterior] + [(x, y, z) for x, y in interior]
    caras = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    malla = bpy.data.meshes.new(nombre)
    malla.from_pydata(verts, [], caras)
    malla.update()
    obj = bpy.data.objects.new(nombre, malla)
    if col:
        col.objects.link(obj)
    return obj


def dar_grosor(obj, alto, bisel=0.0, segmentos_bisel=2):
    """Extruye una superficie plana y le pone bisel. El bisel no es un adorno:
    es lo que hace que la KEY separe la pieza del fondo (§3)."""
    solid = obj.modifiers.new('grosor', 'SOLIDIFY')
    solid.thickness = alto
    solid.offset = 1.0
    if bisel > 0:
        bev = obj.modifiers.new('bisel', 'BEVEL')
        bev.width = bisel
        bev.segments = segmentos_bisel
        bev.limit_method = 'ANGLE'
        bev.angle_limit = math.radians(30)
    return obj


def aplanar(obj):
    """Aplica los modificadores. Se hace antes de duplicar en enlazado: seis
    subdivisiones vivas en la carta del 6 cuadruplican el render para nada."""
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception:
            obj.modifiers.remove(m)
    return obj


def texto(nombre, cadena, ruta_fuente=None, alto=0.20, z=0.0, extrusion=0.0,
          alineado='CENTER', col=None):
    """Texto con la altura de mayúscula pedida, ya convertido a malla.

    La conversión no es un capricho: un objeto de tipo FONT no tiene
    dimensiones reales hasta que se evalúa, así que escalarlo "a ojo" daba
    numerales diminutos. Convertido a malla, `dimensions` es la caja del glifo
    de verdad y el §3 se puede cumplir al píxel (altura de mayúscula 20 px).
    """
    datos = bpy.data.curves.new(nombre, 'FONT')
    datos.body = cadena
    datos.align_x = alineado
    datos.align_y = 'CENTER'
    datos.dimensions = '2D'
    datos.fill_mode = 'BOTH'      # sin esto los glifos salen en hueco, sólo el contorno
    if extrusion:
        datos.extrude = extrusion
    if ruta_fuente:
        try:
            datos.font = bpy.data.fonts.load(ruta_fuente)
        except Exception:
            pass       # sin la fuente del tema se usa la de Blender
    obj = bpy.data.objects.new(nombre, datos)
    destino = col or bpy.context.scene.collection
    destino.objects.link(obj)

    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.view_layer.objects.active
    obj.name = nombre

    if obj.dimensions.y > 0:
        factor = alto / obj.dimensions.y
        obj.scale = (factor, factor, factor)
    obj.location.z = z
    bpy.context.view_layer.update()
    return obj


def instancia(original, nombre, loc, rot_z=0.0, escala=1.0, col=None):
    """Duplicado ENLAZADO: comparte la malla con el original (§6.5)."""
    obj = bpy.data.objects.new(nombre, original.data)
    obj.location = (loc[0], loc[1], loc[2] if len(loc) > 2 else original.location.z)
    obj.rotation_euler = (original.rotation_euler[0], original.rotation_euler[1],
                          original.rotation_euler[2] + math.radians(rot_z))
    base = original.scale
    obj.scale = (base[0] * escala, base[1] * escala, base[2] * escala)
    if col:
        col.objects.link(obj)
    return obj


def encajar_en(obj, ancho_max, alto_max):
    """Escala uniformemente hasta que quepa en la caja pedida. Los tamaños
    máximos del §4.1 no son orientativos: es lo que mantiene contable la carta."""
    bpy.context.view_layer.update()
    dim = obj.dimensions
    if dim.x <= 0 or dim.y <= 0:
        return obj
    factor = min(ancho_max / dim.x, alto_max / dim.y)
    obj.scale = (obj.scale[0] * factor, obj.scale[1] * factor, obj.scale[2] * factor)
    bpy.context.view_layer.update()
    return obj


def escalar_a_alto(obj, alto):
    """Escala por la ALTURA, dejando que el ancho caiga donde caiga. Es lo que
    quiere una fila de siluetas anchas: si se encaja por ancho, las siete se
    encogen hasta no verse."""
    bpy.context.view_layer.update()
    if obj.dimensions.y <= 0:
        return obj
    factor = alto / obj.dimensions.y
    obj.scale = tuple(s * factor for s in obj.scale)
    bpy.context.view_layer.update()
    return obj


def centrar_en(obj, x, y):
    """Coloca el centro de la caja envolvente del objeto en (x, y)."""
    bpy.context.view_layer.update()
    centro = sum((obj.matrix_world @ __import__('mathutils').Vector(v)
                  for v in obj.bound_box), __import__('mathutils').Vector()) / 8.0
    obj.location.x += x - centro.x
    obj.location.y += y - centro.y
    return obj


# ==========================================================================
# 4. Fondo y marco (lo que comparten los 64 temas)
# ==========================================================================

def carta_base(ctx, material):
    """El campo del fondo: la carta entera con sus esquinas redondeadas. Fuera
    de este polígono no hay geometría, así que el alfa sale transparente (§2)."""
    puntos = puntos_rect_redondeado(spec.ANCHO, spec.ALTO, spec.RADIO_ESQUINA, 12)
    obj = malla_poligono('BG_campo', puntos, spec.Z_BG, ctx.col['BG'])
    return poner_material(obj, material)


def placas_numeral(ctx, hex_banda, rugosidad=0.5):
    """Ensancha la banda en las dos esquinas del numeral.

    **Desviación deliberada del DECK_SPEC §3, y por qué.** El spec pide dos
    cosas a la vez que no caben juntas: la caja del numeral mide 8..46 px (38
    px) con 20 px de altura de mayúscula, pero la banda sólo tiene 17 px de
    ancho — y a la vez exige que el numeral esté *sobre la banda, nunca sobre
    el interior*, con 4.5:1 de contraste. Con un interior claro, un numeral
    claro cae encima del interior y desaparece; se comprobó renderizando.

    La salida es engordar la banda dentro de la propia caja 8..46: una placa
    del mismo material y la misma altura, que se funde con la esquina. No
    cambia el ancho de la banda, ni su posición, ni el radio, ni la caja del
    numeral — sólo hace que el sitio donde el spec pone el numeral sea banda de
    verdad. Es compartida por los 64 temas, así que la mesa mixta sigue atada.
    """
    # 36 px de lado: cubre el glifo con holgura y deja libre la esquina de la
    # ventana, por donde en el 7 asoma la pinta de arriba.
    lado = 0.36
    centro = spec.BANDA_DE + lado / 2
    material = material_pbr('mat_placa', hex_banda, rugosidad)

    creadas = []
    for signo in (1, -1):
        cx = signo * (-spec.MEDIO_X + centro)
        cy = signo * (spec.MEDIO_Y - centro)
        puntos = puntos_rect_redondeado(lado, lado, 0.11, 8, (cx, cy))
        placa = malla_poligono(f'FRAME_placa{signo}', puntos, spec.Z_MARCO,
                               ctx.col['FRAME'])
        dar_grosor(placa, spec.RELIEVE_MARCO, spec.BISEL_MARCO)
        poner_material(placa, material)
        creadas.append(placa)
    return creadas


def marco(ctx, hex_banda, rugosidad=0.5, hex_filete=None):
    """La banda del §3: bucle cerrado, ancho uniforme, relieve con bisel.
    Un tema puede cambiarle el color, el material y añadirle un filete interior,
    pero no el ancho, la posición ni el radio."""
    segmentos = 10
    exterior = puntos_rect_redondeado(
        spec.ANCHO - 2 * spec.BANDA_DE, spec.ALTO - 2 * spec.BANDA_DE,
        spec.RADIO_BANDA_EXT, segmentos)
    interior = puntos_rect_redondeado(
        spec.ANCHO - 2 * spec.BANDA_A, spec.ALTO - 2 * spec.BANDA_A,
        spec.RADIO_BANDA_INT, segmentos)

    banda = malla_anillo('FRAME_banda', exterior, interior, spec.Z_MARCO, ctx.col['FRAME'])
    dar_grosor(banda, spec.RELIEVE_MARCO, spec.BISEL_MARCO)
    poner_material(banda, material_pbr('mat_marco', hex_banda, rugosidad))

    if ctx.pieza != 'back':
        placas_numeral(ctx, hex_banda, rugosidad)

    if hex_filete:
        # Filete interior de 1 px, pegado al borde interno de la banda.
        fuera = puntos_rect_redondeado(
            spec.ANCHO - 2 * spec.BANDA_A + 0.02, spec.ALTO - 2 * spec.BANDA_A + 0.02,
            spec.RADIO_BANDA_INT + 0.01, segmentos)
        dentro = puntos_rect_redondeado(
            spec.ANCHO - 2 * spec.BANDA_A + 0.01, spec.ALTO - 2 * spec.BANDA_A + 0.01,
            spec.RADIO_BANDA_INT + 0.005, segmentos)
        filete = malla_anillo('FRAME_filete', fuera, dentro,
                              spec.Z_MARCO + spec.RELIEVE_MARCO + 0.001, ctx.col['FRAME'])
        poner_material(filete, material_plano('mat_filete', hex_filete))
    return banda


def numerales(ctx, pieza, hex_color, ruta_fuente=None, glifo_tematico=None,
              hex_latino=None):
    """Los dos numerales del §3, puntualmente simétricos.

    Si el tema no usa dígitos latinos (`glifo_tematico`), se aplica la regla de
    doble numeral: arriba-izquierda el glifo del tema a tamaño completo y
    abajo-derecha el dígito latino al 70 % y al 65 % de opacidad. Nadie debería
    tener que descifrar una carta para poder jugarla.
    """
    if pieza == 'back':
        return []
    latino = str(int(pieza))
    principal = glifo_tematico if glifo_tematico is not None else latino
    creados = []

    # Los numerales van 4 milésimas por encima de la cara de la banda: a la
    # misma altura exacta habría parpadeo de profundidad, y el ornamento de
    # esquina tiene que poder colarse entre medias.
    z = spec.Z_NUMERAL + 0.004
    mat = material_plano('mat_numeral', hex_color)
    sup = texto('NUM_sup', principal, ruta_fuente, spec.NUM_ALTURA_MAYUSCULA,
                z, col=ctx.col['FRAME'])
    poner_material(sup, mat)
    x, y = spec.caja_numeral('sup-izq')
    centrar_en(sup, x, y)
    creados.append(sup)

    if glifo_tematico is None:
        inf = texto('NUM_inf', latino, ruta_fuente, spec.NUM_ALTURA_MAYUSCULA,
                    z, col=ctx.col['FRAME'])
        poner_material(inf, mat)
        inf.rotation_euler[2] = math.pi          # rotado 180°
    else:
        inf = texto('NUM_inf', latino, ruta_fuente,
                    spec.NUM_ALTURA_MAYUSCULA * 0.70, z,
                    col=ctx.col['FRAME'])
        poner_material(inf, material_plano('mat_numeral_latino',
                                           hex_latino or hex_color, 0.65))
        inf.rotation_euler[2] = math.pi
    x, y = spec.caja_numeral('inf-der')
    centrar_en(inf, x, y)
    creados.append(inf)
    return creados


# ==========================================================================
# 5. Render
# ==========================================================================

def render(escena, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    escena.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    return ruta
