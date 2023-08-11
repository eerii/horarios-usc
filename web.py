import api
from pywebio.pin import *
from pywebio.output import *
from unidecode import unidecode

# Funciones ayuda
# ---

def materia(nombre: str):
    l = api.lista_materias('materias.json') # datos precargados
    m = api.encontrar_materia(l, nombre)[0][0]
    return m

def refrescar_curso(e):
    global horario
    horario = api.horario_curso(cursos[e], cuatrimestres[pin.cuatri], pin.grupo, 'materias.json')
    render()
def refrescar_cuatri(e):
    global horario
    horario = api.horario_curso(cursos[pin.curso], cuatrimestres[e], pin.grupo, 'materias.json')
    render()
def refrescar_grupo(e):
    global horario
    for m in horario.materias.values():
        if m.curso == cursos[pin.curso]:
            m.grupo_seleccionado = e
    api.actualizar_horario(horario)
    render()

def incluir_materia():
    global horario
    api.incluir_en_horario(horario, materia(pin.buscar), 1)
    render()

def cambiar_grupo_materia(nombre):
    global horario
    def wrapper(e):
        api.incluir_en_horario(horario, materia(nombre), e)
        render()
    return wrapper

def eliminar_materia(nombre):
    global horario
    def wrapper():
        api.eliminar_de_horario(horario, nombre)
        render()
    return wrapper

# Widgets
# ---

cursos = { "Primero": 1, "Segundo": 2, "Tercero": 3, "Cuarto": 4, "Quinto": 5 }
cuatrimestres = { "Primero": 1, "Segundo": 2 }

put_row([
    put_select('curso', options = cursos.keys(), label = 'Curso'),
    None,
    put_select('cuatri', options = cuatrimestres.keys(), label = 'Cuatrimestre'),
    None,
    put_select('grupo', options = list(range(1, 6)), label = 'Grupo'),
])

# Display
# ---

def render():
    global horario

    with use_scope('buscar', clear = True):
        materias = [ m.nombre for m in api.lista_materias('materias.json') if m.cuatrimestre == cuatrimestres[pin.cuatri] and not m.nombre in horario.materias ]

        put_row([
            put_input('buscar', placeholder = 'Busca una materia', datalist = materias),
            None,
            put_button('Añadir', onclick = incluir_materia)
        ], 'auto 10px 76px')

    with use_scope('horario', clear = True):
        def cambio_grupo(nombre, grupo):
            n = 'cambio' + unidecode(nombre.replace(' ', '_'))
            select = put_select(n, options = list(range(1, 6)), value = grupo)
            pin_on_change(n, cambiar_grupo_materia(nombre), clear = True)
            return select

        materias = [ [ 'Materia', 'Abr.', 'Grupo', 'Quitar' ] ]
        materias += [ [ m.nombre, m.abreviatura, cambio_grupo(m.nombre, m.grupo_seleccionado), put_button('X', onclick = eliminar_materia(m.nombre)) ] for m in horario.materias.values() ]

        put_row([
            put_html(api.formato_horario(horario).to_html(border = 0)),
            None,
            put_table(materias)
        ])

pin_on_change('curso', refrescar_curso, init_run = True)
pin_on_change('cuatri', refrescar_cuatri)
pin_on_change('grupo', refrescar_grupo)