# API para buscar horarios de materias en la USC
# Uso: introduce los datos pedidos (los valores por defecto son para Ingeniería Informática) y busca una materia
# Requiere instalar: requests, beautifulsoup4, rapidfuzz

from dataclasses import dataclass, field
from enum import Enum
from pprint import pprint

import datetime as dt
import re
from rapidfuzz import fuzz

import requests
from bs4 import BeautifulSoup

# Definiciones de datos
# ---

class TipoMateria(Enum):
    FORMACION_BASICA = 'Formación básica'
    OBLIGATORIO = 'Obligatorio'
    OPTATIVO = 'Optativo'

class TipoClase(Enum):
    EXPOSITIVA = 'CLE'
    INTERACTIVA = 'CLIL'
    SEMINARIO = 'TODO'

class DiaSemana(Enum):
    LUNES = 'Lunes'
    MARTES = 'Martes'
    MIERCOLES = 'Miércoles'
    JUEVES = 'Jueves'
    VIERNES = 'Viernes'

@dataclass
class Materia:
    nombre: str
    enlace: str
    curso: int
    semestre: int
    tipo: TipoMateria

@dataclass
class HoraClase:
    grupo: int
    dia_semana: DiaSemana
    hora_inicio: dt.time
    duracion: dt.timedelta
    aula: str
    tipo: TipoClase

@dataclass
class Examen:
    fecha: dt.datetime
    duracion: dt.timedelta
    aula: set[str]

@dataclass
class Clase:
    horario: list[HoraClase] = field(default_factory=list)
    examenes: list[Examen] = field(default_factory=list)

# Funciones de la API
# ---

# Obtiene una lista de las materias del grado indicado con la url a la página específica
url_base = 'https://www.usc.gal/es/centro/escuela-tecnica-superior-ingenieria'
grado = 'Grao en Ingeniería Informática.*2'
def lista_materias(url_base = url_base, grado = grado):
    materias: list(Materia) = []

    r = requests.get(url_base + '/horarios/materias')
    soup = BeautifulSoup(r.text, 'html.parser')

    tb_grei = soup.findAll('p', text=re.compile(grado))
    for m in tb_grei:
        data = m.parent.parent
        titulo = data.find('a')
        curso, semestre, tipo, _ = data.find('p', text=re.compile('Curso')).text.split(' | ')
        
        materias.append(Materia(
            nombre = titulo.text,
            enlace = 'https://www.usc.gal' + titulo['href'],
            curso = int(curso[0]),
            semestre = int(semestre[0]) if semestre[0].isnumeric() else 0,
            tipo = TipoMateria(tipo)
        ))

    return materias

# Obtiene los horarios y fechas de exámen de una materia
def datos_clase(materia: Materia):
	clase = Clase()
	dia = DiaSemana.LUNES

	r = requests.get(materia.enlace)
	soup = BeautifulSoup(r.text, 'html.parser')

	tb_cl = soup.find('caption', text=re.compile('semestre')).parent
	tb_ex = soup.find('caption', text=re.compile('Exámenes')).parent

	# todo: múltiples fechas
	for c in tb_cl.findAll('tr'):
		if c.find('th'):
			dia = DiaSemana(c.find('th').text)
			continue

		tipo, grupo = c.find_all('td')[1].text.split(' ')[-1][1:].split('_')
		hora_inicio, hora_fin = list(map(lambda x: dt.datetime.strptime(x, '%H:%M'), c.find_all('td')[0].text.split('-')))

		clase.horario.append(HoraClase (
			grupo = int(grupo),
			dia_semana = dia,
			hora_inicio = hora_inicio.time(),
			duracion = hora_fin - hora_inicio,
			aula = c.find_all('td')[2].text.split(' ')[-1],
			tipo = TipoClase(tipo)
		))

	for e in tb_ex.findAll('tr', class_='target-items-selector'):
		str_fecha, str_hora_fin = e.find_all('td')[0].text.split('-')
		fecha = dt.datetime.strptime(str_fecha, '%d.%m.%Y %H:%M')
		hora_fin = dt.datetime.combine(fecha.date(), dt.datetime.strptime(str_hora_fin, '%H:%M').time())
		aula = e.find_all('td')[2].text.split(' ')[-1]

		examen = next(filter(lambda e: e.fecha == fecha, clase.examenes), None)
		if examen is None:
			clase.examenes.append(Examen(
				fecha = fecha,
				duracion = hora_fin - fecha,
				aula = { aula }
			))
			continue
		examen.aula.add(aula)

	return clase

# Utiliza fuzzy matching para encontrar el nombre de una materia
def encontrar_materia(materias: list[Materia], busqueda: str):
    nombres = map(lambda m: (m, fuzz.ratio(busqueda, m.nombre) + 100 * (busqueda in m.nombre)), materias)
    return list(sorted(nombres, key = lambda x: x[1], reverse = True))[:5]

# Ejemplo de aplicación
# ---

def preguntar(texto, defecto = ""):
    print(f"{texto}\nValor por defecto: '{defecto}'")
    return input(f"> ") or defecto

url_base = preguntar("Introduce la URL de la facultad", url_base)
grado = preguntar("Introduce una cadena regex con el nombre del grado", grado)
materia = preguntar("Materia a buscar")

l = lista_materias(url_base, grado)
m = encontrar_materia(l, materia)[0][0]
c = datos_clase(m)

print(f"\n{m.nombre}\n{m.curso}º - Semestre {m.semestre} - {m.tipo.value}")
pprint(c)