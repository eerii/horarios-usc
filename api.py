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
    semestre: int
    tipo: TipoMateria
    horario: list[HoraClase] = field(default_factory=list)
    examenes: list[Examen] = field(default_factory=list)
    
@dataclass
class Horario:
    df: pd.DataFrame
    materias: list[(Materia, int)] = field(default_factory=list)

# Obtener y procesar la lista de materias desde la web de la USC
# ---

# Obtiene una lista de las materias del grado indicado con la url a la página específica
url_base = 'https://www.usc.gal/es/centro/escuela-tecnica-superior-ingenieria'
grado = 'Grao en Ingeniería Informática.*2'
def lista_materias(url_base=url_base, grado=grado):
    materias: list(Materia) = []

    if 'http' in url_base:
        print('Obteniendo lista de materias...')
        r = requests.get(url_base + '/horarios/materias')
        soup = BeautifulSoup(r.text, 'html.parser')

        tb_grei = soup.findAll('p', text=re.compile(grado))
        for m in tb_grei:
            data = m.parent.parent
            titulo = data.find('a')
            curso, semestre, tipo, _ = data.find('p', text=re.compile('Curso')).text.split(' | ')

            materias.append(Materia(
                nombre = titulo.text,
                abreviatura = ''.join(filter(lambda x: x.isupper(), titulo.text)),
                enlace = 'https://www.usc.gal' + titulo['href'],
                curso = int(curso[0]),
                semestre = int(semestre[0]) if semestre[0].isnumeric() else 0,
                tipo = TipoMateria(tipo)
            ))
    else:
        f = open(url_base, 'r')
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

    tb_cl = soup.find('caption', text=re.compile('[semestre|Anual]'))
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

# Crea una lista offline con todos los datos de las materias
def generar_lista_materias(archivo: str):
    l = lista_materias()
    for m in l:
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

# Horarios
# ---

# Crea un nuevo horario (pandas dataframe) para guardar las clases
def iniciar_horario():
    horas = pd.date_range(start = '09:00', end = '20:00',freq = '30min').strftime('%H:%M')
    dias = [d.value for d in DiaSemana]

    return Horario(pd.DataFrame(index=horas, columns=dias), [])

# Añade una materia al horario especificado en el grupo indicado
def horario_materia(horario: Horario, materia: Materia, grupo: int):
    for h in materia.horario:
        if h.grupo != grupo and h.tipo == TipoClase.INTERACTIVA:
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
        
    horario.materias += [(materia, grupo)]
    return horario

# Crea un horario del curso indicado
def horario_curso(curso: int, semestre: int, grupo: int, url_base=url_base, grado=grado):
    horario = iniciar_horario()

    for m in lista_materias(url_base, grado):
        if m.curso != curso or (m.semestre > 0 and m.semestre != semestre):
            continue
        if 'http' in url_base:
            m = datos_materia(m)
        horario_materia(horario, m, grupo)

    return horario

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
        styler.set_caption("Horario")
        styler.set_table_styles([
            {'selector': 'th', 'props': [('background', '#fac27d')]},
            {'selector': 'td', 'props': []},
            {'selector': '*', 'props': [('color', 'black'), ('text-align', 'center')]},
        ])
        styler.applymap(color, subset=pd.IndexSlice[:, ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']])
        return styler

    return horario.df.fillna('').style.pipe(make_pretty)