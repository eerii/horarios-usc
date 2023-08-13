import api

from pywebio.input import *
from pywebio.pin import *
from pywebio.output import *
from pywebio.session import run_js

import os
from unidecode import unidecode

# Funciones ayuda
# ---

def materia(nombre: str):
    l = api.lista_materias() # datos precargados
    m = api.encontrar_materia(l, nombre)[0][0]
    return m

def refrescar_curso(e):
    global horario
    horario = api.horario_curso(cursos[e], cuatrimestres[pin.cuatri], pin.grupo)
    render()
def refrescar_cuatri(e):
    global horario
    horario = api.horario_curso(cursos[pin.curso], cuatrimestres[e], pin.grupo)
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

def resetear():
    confirmar = actions('Confirmas descartar todos los cambios?', ['Si', 'No'],
                        help_text = 'La aplicación volverá a descargar la lista de grados y materias')
    if confirmar != 'Si':
        return

    global url, grados, grado
    url, grados, grado = None, None, None

    os.remove('materias.json')
    run_js('location.reload()')

# Widgets
# ---

def elegir_grado():
    if os.path.exists('materias.json'):
        return
    
    global url, grados, grado
    url, grados, grado = None, None, None
    
    urls = [
        'https://www.usc.gal/es/centro/escuela-tecnica-superior-ingenieria',
        'https://www.usc.gal/es/centro/facultad-fisica',
        'https://www.usc.gal/es/centro/facultad-filosofia'
    ]

    def elegir_url():
        global url, grados
        url = pin.url if 'http' in pin.url else f'https://{pin.url}'
        with use_scope('buscando_grados'):
            put_info('Buscando grados')
        grados = api.obtener_grados(url)
        remove('buscando_grados')
        if not grados:
            put_error(f"La url {url} parece ser incorrecta, prueba de nuevo")
            url = None

    with use_scope('url'):
        put_text('Url de la facultad')
        put_row([
            put_input('url', placeholder = urls[0], datalist = urls),
            None,
            put_button('Elegir', onclick = elegir_url),
        ], 'auto 10px 76px')

    while not url or not grados:
        pass

    def elegir_grado():
        global grado
        grado = pin.grado
        if grado in grados:
            grado = '^' + grado.replace('(', '.*').replace(')', '.*') + '$'

    with use_scope('grado'):
        put_text('Grado')
        put_row([
            put_input('grado', datalist = grados),
            None,
            put_button('Confirmar', onclick = elegir_grado),
        ], 'auto 10px 76px')
        put_text('Cuando presiones confirmar se cargará la lista de materias del grado correspondiente. Es posible que tarde un par de minutos, pero solo se hará una vez.')

    while not grado:
        pass
    
    for n in api.generar_lista_materias('materias.json', url, grado):
        with use_scope('cargando', clear = True):
            put_info(f"Obteniendo datos de '{n}'")
    print("done")
    
    remove('cargando')
    remove('grado')
    remove('url')

cursos = { "Primero": 1, "Segundo": 2, "Tercero": 3, "Cuarto": 4, "Quinto": 5 }
cuatrimestres = { "Primero": 1, "Segundo": 2 }

def widgets():
    put_row([
        put_select('curso', options = cursos.keys(), label = 'Curso'),
        None,
        put_select('cuatri', options = cuatrimestres.keys(), label = 'Cuatrimestre'),
        None,
        put_select('grupo', options = list(range(1, 6)), label = 'Grupo'),
    ])

    pin_on_change('curso', refrescar_curso)
    pin_on_change('cuatri', refrescar_cuatri)
    pin_on_change('grupo', refrescar_grupo)

# Display
# ---

def render():
    global horario

    with use_scope('buscar', clear = True):
        materias = [ m.nombre for m in api.lista_materias() if m.cuatrimestre == cuatrimestres[pin.cuatri] and not m.nombre in horario.materias ]

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

    with use_scope('resetear', clear = True):
        put_button('Resetear o cambiar de grado', onclick = resetear)

def main():
    elegir_grado()
    widgets()
    refrescar_curso('Primero')

if __name__ == '__main__':
    main()