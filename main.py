# Uso: introduce los datos pedidos (los valores por defecto son para Ingeniería Informática) y busca una materia
# Requiere instalar: requests, beautifulsoup4, rapidfuzz

import api
from pprint import pprint

def preguntar(texto, defecto = ""):
    print(f"{texto}\nValor por defecto: '{defecto}'")
    return input(f"> ") or defecto

url_base = preguntar("Introduce la URL de la facultad", api.url_base)
grado = preguntar("Introduce una cadena regex con el nombre del grado", api.grado)
materia = preguntar("Materia a buscar")

l = api.lista_materias(url_base, grado)
m = api.encontrar_materia(l, materia)[0][0]
c = api.datos_clase(m)

print(f"\n{m.nombre}\n{m.curso}º - Semestre {m.semestre} - {m.tipo.value}")
pprint(c)