# API para buscar horarios de materias en la USC

from dataclasses import dataclass, field, asdict
from enum import Enum

import datetime as dt
import re
from rapidfuzz import fuzz
from colorsys import hsv_to_rgb

import pandas as pd

import requests
from bs4 import BeautifulSoup

import json
from dacite import from_dict, Config as dcConfig

# Definiciones de datos
# ---

class TipoMateria(str, Enum):
    FORMACION_BASICA = 'Formación básica'
    OBLIGATORIO = 'Obligatorio'
    OPTATIVO = 'Optativo'

class TipoClase(str, Enum):
    EXPOSITIVA = 'CLE'
    INTERACTIVA = 'CLIL'
    SEMINARIO = 'CLIS'

class DiaSemana(str, Enum):
    LUNES = 'Lunes'
    MARTES = 'Martes'
    MIERCOLES = 'Miércoles'
    JUEVES = 'Jueves'
    VIERNES = 'Viernes'

@dataclass
class HoraClase:
    grupo: int
    dia_semana: DiaSemana
    hora_inicio: dt.time
    hora_fin: dt.time
    aula: str
    tipo: TipoClase

@dataclass
class Examen:
    fecha: dt.datetime
    aula: set[str]

@dataclass
class Materia:
    nombre: str
    abreviatura: str
    enlace: str
    curso: int
    cuatrimestre: int
    tipo: TipoMateria
    grupo_seleccionado: int
    horario: list[HoraClase] = field(default_factory=list)
    examenes: list[Examen] = field(default_factory=list)
    
@dataclass
class Horario:
    df: pd.DataFrame
    materias: dict[str, Materia] = field(default_factory=dict)

log = ''

# Obtener y procesar la lista de materias desde la web de la USC
# ---

# Obtiene una lista de los grados disponibles
def obtener_grados(url_base):
    gr = set()

    try:
        r = requests.get(url_base + '/horarios/materias')
    except:
        return None

    soup = BeautifulSoup(r.text, 'html.parser')

    descripciones = soup.findAll('div', class_='at-text')
    for g in descripciones:
        grado = g.findAll('p')[0].text
        gr.add(grado)

    return list(gr)

# Crea una lista offline con todos los datos de las materias
def generar_lista_materias(archivo: str, url_base, grado):
    print('Obteniendo lista de materias...')
    l = []

    r = requests.get(url_base + '/horarios/materias')
    soup = BeautifulSoup(r.text, 'html.parser')

    tb_grei = soup.findAll('p', text=re.compile(grado))
    for m in tb_grei:
        data = m.parent.parent
        titulo = data.find('a')
        curso, cuatrimestre, tipo, _ = data.find('p', text=re.compile('Curso')).text.split(' | ')

        l.append(Materia(
            nombre = titulo.text,
            abreviatura = ''.join(filter(lambda x: x.isupper(), titulo.text)),
            enlace = 'https://www.usc.gal' + titulo['href'],
            curso = int(curso[0]),
            cuatrimestre = int(cuatrimestre[0]) if cuatrimestre[0].isnumeric() else 0,
            tipo = TipoMateria(tipo),
            grupo_seleccionado = 0
        ))

    for m in l:
        yield m.nombre
        m = asdict(datos_materia(m))

    def writer(o):
        if isinstance(o, dt.datetime) or isinstance(o, dt.time):
            return o.isoformat()
        if isinstance(o, set):
            return list(o)
        return o.__dict__

    f = open(archivo, 'w')
    f.write(json.dumps(l, default = writer, sort_keys = True, indent = 4, ensure_ascii = False))
    f.close()

# Lee la lista generada de materias
def lista_materias():
    materias: list(Materia) = []

    f = open('materias.json', 'r')
    conf = dcConfig(cast = [Enum, set], type_hooks = {dt.datetime: dt.datetime.fromisoformat, dt.time: dt.time.fromisoformat})
    for m in json.load(f):
        materias.append(from_dict(data_class=Materia, data=m, config=conf))
    f.close()

    return materias

# Obtiene los horarios y fechas de exámen de una materia
def datos_materia(materia: Materia):
    dia = DiaSemana.LUNES

    print(f"Obteniendo datos de '{materia.nombre}'...")
    r = requests.get(materia.enlace)
    soup = BeautifulSoup(r.text, 'html.parser')

    tb_cl = soup.find('caption', text=re.compile('[cuatrimestre|Anual]'))
    if not tb_cl:
        return materia
    tb_cl = tb_cl.parent

    tb_ex = soup.find('caption', text=re.compile('Exámenes')).parent

    # todo: múltiples fechas
    for c in tb_cl.findAll('tr'):
        if c.find('th'):
            dia = DiaSemana(c.find('th').text)
            continue

        tipo, grupo = c.find_all('td')[1].text.split(' ')[-1][1:].split('_')
        if not tipo in set(i.value for i in TipoClase):
            for t in TipoClase:
                if tipo in t.value:
                    tipo = t
                    break
        tipo = TipoClase(tipo)
        hora_inicio, hora_fin = list(map(lambda x: dt.datetime.strptime(x, '%H:%M').time(), c.find_all('td')[0].text.split('-')))
        
        materia.horario.append(HoraClase(
            grupo = int(grupo),
            dia_semana = dia,
            hora_inicio = hora_inicio,
            hora_fin = hora_fin,
            aula = c.find_all('td')[2].text.split(' ')[-1],
            tipo = tipo
        ))

    for e in tb_ex.findAll('tr', class_='target-items-selector'):
        str_fecha, _ = e.find_all('td')[0].text.split('-')
        fecha = dt.datetime.strptime(str_fecha, '%d.%m.%Y %H:%M')
        aula = e.find_all('td')[2].text.split(' ')[-1]

        examen = next(filter(lambda e: e.fecha == fecha, materia.examenes), None)
        if examen is None:
            materia.examenes.append(Examen(
                fecha = fecha,
                aula = {aula}
            ))
            continue
        examen.aula.add(aula)

    return materia

# Utiliza fuzzy matching para encontrar el nombre de una materia
def encontrar_materia(materias: list[Materia], busqueda: str):
    nombres = map(lambda m: (m, fuzz.ratio(busqueda, m.nombre) + 100 * (busqueda in m.nombre)), materias)

    return list(sorted(nombres, key=lambda x: x[1], reverse = True))[:5]

# Horarios
# ---

# Crea un nuevo horario (pandas dataframe) para guardar las clases
def iniciar_horario():
    horas = pd.date_range(start = '09:00', end = '20:00',freq = '30min').strftime('%H:%M')
    dias = [d.value for d in DiaSemana]

    return Horario(pd.DataFrame(index=horas, columns=dias), {})

# Crea un horario del curso indicado
def horario_curso(curso: int, cuatrimestre: int, grupo: int):
    horario = iniciar_horario()

    for m in lista_materias():
        if m.curso != curso or (m.cuatrimestre > 0 and m.cuatrimestre != cuatrimestre):
            continue
        incluir_en_horario(horario, m, grupo)

    actualizar_horario(horario)
    return horario

# Añade una materia al horario especificado en el grupo indicado
def incluir_en_horario(horario: Horario, materia: Materia, grupo: int):
    if not materia.nombre in horario.materias:
        horario.materias[materia.nombre] = materia

    horario.materias[materia.nombre].grupo_seleccionado = grupo
    actualizar_horario(horario)

# Elimina una materia del horario
def eliminar_de_horario(horario: Horario, materia: Materia | str):
    horario.materias.pop(materia if isinstance(materia, str) else materia.nombre)
    actualizar_horario(horario)

# Actualiza el dataframe del horario
def actualizar_horario(horario: Horario):
    horario.df = pd.DataFrame(index=horario.df.index, columns=horario.df.columns)
    for materia in horario.materias.values():
        for h in materia.horario:
            if h.grupo != materia.grupo_seleccionado and h.tipo == TipoClase.INTERACTIVA:
                continue

            ch = { TipoClase.EXPOSITIVA: 'E', TipoClase.INTERACTIVA: 'I', TipoClase.SEMINARIO: 'S' }

            r = pd.date_range(start=h.hora_inicio.strftime('%H:%M'), end=h.hora_fin.strftime('%H:%M'), freq='30min')[:-1]

            # Comprobar conflictos
            conflicto = False
            for hora in r:
                m = horario.df.loc[hora.strftime('%H:%M'), h.dia_semana.value]
                if not pd.isna(m):
                    mm = f"{materia.abreviatura} {ch[h.tipo]}{h.grupo}"
                    if m == mm:
                        continue
                    if not conflicto:
                        print(f"[Conflicto] {mm} / {m} - {h.dia_semana.value} {hora.strftime('%H:%M')}")
                    conflicto = True

            for hora in r:
                m = set(str(horario.df.loc[hora.strftime('%H:%M'), h.dia_semana.value]).split(' / '))
                m.add(f"{materia.abreviatura} {ch[h.tipo]}{h.grupo}")
                m = list(filter(lambda x: x != 'nan', m))
                horario.df.loc[hora.strftime('%H:%M'), h.dia_semana.value] = ' / '.join(sorted(m))

# Formatear horario con colores y estilo
def formato_horario(horario: Horario):
    u = horario.df.stack()
    u = filter(lambda x: x != '' and not '/' in x, u)
    u = map(lambda x: x.split(' ')[0], u)
    u = set(u)
    color = lambda i, t: hsv_to_rgb((i + 1) / (t + 1), 0.4, 1.0)
    to_hex = lambda rgb: '#%02x%02x%02x' % tuple(map(lambda x: int(x*255), rgb))
    u_colors = {x: to_hex(color(i, len(u))) for i, x in enumerate(u)}

    def color(texto):
        if texto == '':
            return 'background: #fff6eb'
        if '/' in texto:
            return f'background: {to_hex(hsv_to_rgb(0.0, 0.4, 1.0))}'
        style = f'background: {u_colors[texto.split(" ")[0]]}'
        if 'E' in texto.split(' ')[-1]:
            style += '; font-style: italic'
        if 'I' in texto.split(' ')[-1]:
            style += '; font-weight: bold'
        return style

    def make_pretty(styler):
        styler.set_table_styles([
            {'selector': 'th', 'props': [('background', '#fac27d')]},
            {'selector': 'td', 'props': []},
            {'selector': '*', 'props': [('color', 'black'), ('text-align', 'center')]},
        ])
        styler.applymap(color, subset=pd.IndexSlice[:, ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']])
        return styler

    return horario.df.fillna('').style.pipe(make_pretty)