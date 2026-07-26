# ==========================================================================
# Prueba de extremo a extremo de analitica.py (Roadmap #24)
# --------------------------------------------------------------------------
# No levanta el servidor: monta una app Flask mínima con el módulo real y lo
# conduce con el cliente de pruebas. Usa una base de analítica temporal, así
# que NO toca analitica.db.
#
#   python3 tools/test_analitica.py
#
# El punto 6 necesita una cuenta de verdad para probar la atribución: la crea
# en mus.db y la BORRA al terminar (también si la prueba falla).
# ==========================================================================
import os, sys, json, time, datetime, tempfile, sqlite3, atexit

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

tmp = tempfile.mkdtemp()
os.environ['ANALYTICS_DB'] = os.path.join(tmp, 'analitica_test.db')

from flask import Flask
import analitica

app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = 'test'


class FakeSocketIO:
    def start_background_task(self, f, *a, **k):
        return None
    def sleep(self, n):
        return None


analitica.init_analitica(app, FakeSocketIO(), {'admin_requerido': lambda f: f})
c = app.test_client()

UA_MOVIL = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
            '(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
UA_ESCRITORIO = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                 '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')
UA_BOT = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'

USUARIO_PRUEBA = '___analitica_test___'


def _limpiar_cuenta_prueba():
    """La cuenta del punto 6 no puede quedarse en mus.db pase lo que pase."""
    try:
        c = sqlite3.connect('mus.db')
        c.execute("DELETE FROM Usuarios WHERE username = ?", (USUARIO_PRUEBA,))
        c.commit()
        c.close()
    except Exception as e:
        print(f'⚠️ no se pudo borrar la cuenta de prueba: {e}')


atexit.register(_limpiar_cuenta_prueba)

fallos = []


def comprobar(nombre, cond, extra=''):
    print(('  ✅ ' if cond else '  ❌ ') + nombre + (('  → ' + str(extra)) if extra else ''))
    if not cond:
        fallos.append(nombre)


print('\n1. Visitas y dimensiones')
# Visitante A: móvil, viene de reddit, juega contra el bot y termina.
c.get('/', headers={'User-Agent': UA_MOVIL, 'Referer': 'https://www.reddit.com/r/mus/',
                    'X-Forwarded-For': '10.0.0.1', 'Accept-Language': 'es-ES,es;q=0.9',
                    'CF-IPCountry': 'ES'})
with app.test_request_context('/', headers={'User-Agent': UA_MOVIL,
                                            'X-Forwarded-For': '10.0.0.1'}):
    analitica.evento('partida_inicio', modo='bot')
    analitica.evento('partida_fin', modo='bot', valor=420)
c.post('/api/a/latido', json={'activo': 90},
       headers={'User-Agent': UA_MOVIL, 'X-Forwarded-For': '10.0.0.1'})
c.post('/api/a/evento', json={'tipo': 'menu_jugar'},
       headers={'User-Agent': UA_MOVIL, 'X-Forwarded-For': '10.0.0.1'})

# Visitante B: escritorio, campaña utm, entra y no hace nada (rebote).
c.get('/?utm_source=newsletter&utm_medium=email&utm_campaign=lanzamiento',
      headers={'User-Agent': UA_ESCRITORIO, 'X-Forwarded-For': '10.0.0.2',
               'Accept-Language': 'en-GB,en;q=0.8', 'CF-IPCountry': 'GB'})

# Visitante C: directo, escritorio, no juega pero interactúa.
c.get('/', headers={'User-Agent': UA_ESCRITORIO, 'X-Forwarded-For': '10.0.0.3'})
c.post('/api/a/evento', json={'tipo': 'menu_ranking'},
       headers={'User-Agent': UA_ESCRITORIO, 'X-Forwarded-For': '10.0.0.3'})

# Un crawler: tiene que quedarse fuera de las cifras.
c.get('/', headers={'User-Agent': UA_BOT, 'X-Forwarded-For': '10.0.0.9'})

# Ruido que NO debe contar como visita.
c.get('/static/app.js', headers={'User-Agent': UA_MOVIL, 'X-Forwarded-For': '10.0.0.1'})
c.get('/api/leaderboard', headers={'User-Agent': UA_MOVIL, 'X-Forwarded-For': '10.0.0.1'})

analitica.volcar()
hoy = datetime.date.today().isoformat()
r = json.loads(c.get(f'/admin/api/analitica/resumen?desde={hoy}&hasta={hoy}').data)
t = r['actual']['totales']
print('   totales:', {k: t[k] for k in ('visitas', 'visitantes', 'jugaron', 'partidas',
                                        'partidas_fin', 'rebotes', 'interactuaron')})
comprobar('3 visitas humanas (el crawler y los estáticos fuera)', t['visitas'] == 3, t['visitas'])
comprobar('1 visita jugó', t['jugaron'] == 1, t['jugaron'])
comprobar('1 partida empezada y 1 terminada',
          t['partidas'] == 1 and t['partidas_fin'] == 1, (t['partidas'], t['partidas_fin']))
comprobar('1 rebote (el de la newsletter)', t['rebotes'] == 1, t['rebotes'])
comprobar('tiempo activo del latido registrado', t['activo_total'] == 90, t['activo_total'])
comprobar('tasa de juego = 33,3 %', abs(t['tasa_juego'] - 33.3) < 0.2, t['tasa_juego'])

print('\n2. Nada de IP ni de datos personales en disco')
import sqlite3
con = sqlite3.connect(os.environ['ANALYTICS_DB'])
crudo = ' '.join(str(x) for x in con.execute('SELECT * FROM Sesiones').fetchall())
comprobar('ninguna IP almacenada', '10.0.0.' not in crudo)
comprobar('ningún user-agent almacenado', 'Mozilla' not in crudo)
cols = [r[1] for r in con.execute("PRAGMA table_info(Sesiones)")]
comprobar('no existe columna de IP', not any('ip' == c.lower() for c in cols), cols)

print('\n3. Desgloses')
for dim, esperado in (('fuente', 'reddit.com'), ('dispositivo', 'móvil'),
                      ('pais', 'ES'), ('modo', 'bot'), ('campana', 'lanzamiento'),
                      ('medio', 'email'), ('navegador', 'Safari'), ('so', 'iOS'),
                      ('idioma', 'es')):
    d = json.loads(c.get(f'/admin/api/analitica/dimension?dim={dim}&desde={hoy}&hasta={hoy}').data)
    valores = [f['valor'] for f in d['filas']]
    comprobar(f'dimensión {dim} contiene {esperado!r}', esperado in valores, valores)

d = json.loads(c.get(f'/admin/api/analitica/dimension?dim=evento&desde={hoy}&hasta={hoy}').data)
tipos = {f['valor']: f['visitas'] for f in d['filas']}
comprobar('eventos registrados', tipos.get('pagina') == 4 and tipos.get('partida_fin') == 1, tipos)

print('\n4. Embudo')
emb = {p['paso']: p['n'] for p in r['embudo']}
print('   ', emb)
comprobar('embudo coherente', emb['Visitas'] == 3 and emb['Empiezan partida'] == 1, emb)

print('\n5. En vivo')
v = json.loads(c.get('/admin/api/analitica/en_vivo').data)['vivo']
comprobar('3 visitas vivas (sin el crawler)', v['visitas'] == 3, v['visitas'])
comprobar('1 jugando', v['jugando'] == 1, v['jugando'])

print('\n6. Atribución a cuenta y borrado del rastro')
import base_datos
uid = base_datos.obtener_id_usuario(USUARIO_PRUEBA)
if uid is None:
    base_datos.registrar_usuario(USUARIO_PRUEBA, 'Passw0rd!x', 'ES', '1990-01-01',
                                 'analitica_test@example.com')
    uid = base_datos.obtener_id_usuario(USUARIO_PRUEBA)
with app.test_request_context('/', headers={'User-Agent': UA_ESCRITORIO,
                                            'X-Forwarded-For': '10.0.0.7'}):
    analitica.pagina('/')
    analitica.evento('login', username=USUARIO_PRUEBA)
    analitica.evento('partida_inicio', modo='online2', username=USUARIO_PRUEBA)
analitica.evento('partida_fin', modo='online2', valor=600,
                 username=USUARIO_PRUEBA, por_usuario=True)
analitica.volcar()
u = json.loads(c.get(f'/admin/api/analitica/usuarios?desde={hoy}&hasta={hoy}').data)['usuarios']
mio = [x for x in u if x['username'] == USUARIO_PRUEBA]
comprobar('la cuenta aparece en «por usuario»', len(mio) == 1, [x['username'] for x in u])
if mio:
    comprobar('con 1 partida empezada y 1 terminada',
              mio[0]['partidas'] == 1 and mio[0]['partidas_fin'] == 1, mio[0])
    det = json.loads(c.get(f"/admin/api/analitica/usuarios/{mio[0]['user_id']}").data)
    comprobar('el detalle por día responde', det['exito'] and det['detalle']['serie'])

analitica.olvidar_usuario(uid)
u2 = json.loads(c.get(f'/admin/api/analitica/usuarios?desde={hoy}&hasta={hoy}').data)['usuarios']
comprobar('tras olvidar, la cuenta desaparece del panel',
          not [x for x in u2 if x['username'] == USUARIO_PRUEBA])

print('\n7. Atribución cruzada (por_usuario no roba el evento a quien pulsa)')
analitica.borrar_todo()
with app.test_request_context('/', headers={'User-Agent': UA_MOVIL, 'X-Forwarded-For': '10.0.1.1'}):
    analitica.pagina('/')
    analitica.evento('login', username='jugadorA')
with app.test_request_context('/', headers={'User-Agent': UA_ESCRITORIO, 'X-Forwarded-For': '10.0.1.2'}):
    analitica.pagina('/')
    analitica.evento('login', username='jugadorB')
    # B se une a la sala de A: arranca la partida de los dos.
    analitica.evento('partida_inicio', modo='online2', username='jugadorB')
    analitica.evento('partida_inicio', modo='online2', username='jugadorA', por_usuario=True)
partidas = {s['username']: s['partidas'] for s in analitica._sesiones.values()}
comprobar('una partida a cada jugador, no dos a uno',
          partidas.get('jugadorA') == 1 and partidas.get('jugadorB') == 1, partidas)

print('\n8. Retención, CSV y purga')
coh = json.loads(c.get('/admin/api/analitica/retencion?semanas=8').data)
comprobar('endpoint de retención responde', coh['exito'])
csv = c.get(f'/admin/api/analitica/csv?desde={hoy}&hasta={hoy}')
comprobar('CSV se descarga', csv.status_code == 200 and b'visitas' in csv.data)
analitica.consolidar_pendientes()
analitica.purgar()
comprobar('mantenimiento no revienta', True)

print('\n9. Rangos largos leen agregados sin crudo')
# Simulamos un día viejo ya consolidado y sin filas crudas.
viejo = (datetime.date.today() - datetime.timedelta(days=200)).isoformat()
with analitica._conn() as cn:
    cn.execute("INSERT INTO Dia (dia,visitas,visitantes,duracion_total,activo_total,rebotes,"
               "interactuaron,jugaron,partidas,partidas_fin,segundos_juego,registros,logins,"
               "visitas_cuenta,cuentas,consolidado) VALUES (?,50,40,3000,2500,10,40,20,25,20,9000,3,7,12,9,?)",
               (viejo, time.time()))
r2 = json.loads(c.get(f'/admin/api/analitica/resumen?desde={viejo}&hasta={viejo}').data)
comprobar('un día de hace 200 días sigue teniendo cifras',
          r2['actual']['totales']['visitas'] == 50, r2['actual']['totales']['visitas'])

print('\n10. El endpoint público no acepta basura')
antes = len(analitica._eventos_pend)
c.post('/api/a/evento', json={'tipo': 'inventado_por_un_gracioso'},
       headers={'User-Agent': UA_MOVIL, 'X-Forwarded-For': '10.0.0.1'})
c.post('/api/a/evento', json={'tipo': 'partida_fin'},   # evento de servidor
       headers={'User-Agent': UA_MOVIL, 'X-Forwarded-For': '10.0.0.1'})
comprobar('eventos no permitidos descartados', len(analitica._eventos_pend) == antes)
c.post('/api/a/latido', json={'activo': 999999},
       headers={'User-Agent': UA_MOVIL, 'X-Forwarded-For': '10.0.0.1'})
maxi = max([s['activo'] for s in analitica._sesiones.values()] or [0])
comprobar('latido con tiempo absurdo se recorta', maxi <= 120, maxi)

print('\n' + ('❌ FALLOS: ' + ', '.join(fallos) if fallos else '✅ Todo correcto'))
sys.exit(1 if fallos else 0)
