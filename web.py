import api
from pywebio.pin import *
from pywebio.output import *

# Funciones ayuda
# ---

def materia(nombre: str):
    l = api.lista_materias('materias.json') # datos precargados
    m = api.encontrar_materia(l, nombre)[0][0]
    return m

# Widgets
# ---

cursos = { "Primero": 1, "Segundo": 2, "Tercero": 3, "Cuarto": 4, "Quinto": 5 }
cuatrimestres = { "Primero": 1, "Segundo": 2 }

put_row([
    put_select('curso', options = cursos.keys(), label = 'Curso'),
    put_select('cuatri', options = cuatrimestres.keys(), label = 'Cuatrimestre'),
    put_select('grupo', options = list(range(1, 6)), label = 'Grupo'),
])

# Display
# ---

inicio = True
while True:
    with use_scope('horario', clear = True):
        horario = api.horario_curso(cursos[pin.curso], cuatrimestres[pin.cuatri], pin.grupo, 'materias.json')
        materias = [ [ 'Materia', 'Abr.', 'Grupo' ] ]
        materias += [ [ m.nombre, m.abreviatura,  ] for m, g in horario.materias ]

        put_row([
            put_html(api.formato_horario(horario).to_html(border = 0)),
            put_table(materias)
        ])
    pin_wait_change('curso', 'cuatri', 'grupo')