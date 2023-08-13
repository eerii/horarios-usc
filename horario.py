# todo: múltiples fechas
# todo: carga en diferido

import api

from pywebio.input import *
from pywebio.pin import *
from pywebio.output import *
from pywebio.session import run_js, set_env

import os
from unidecode import unidecode
import webbrowser

# Funciones ayuda
# ---

def materia(nombre: str):
    l = api.lista_materias() # datos precargados
    m = api.encontrar_materia(l, nombre)[0][0]
    return m

def comprobar_semana():
    global horario, semanas, primera_semana
    with use_scope('aviso_cambio_semana', clear = True):
        put_warning('Descargar los datos de una semana diferente lleva un tiempo, lo siento :c Cargando...')
    for m in horario.materias.values():
        if m.cuatrimestre != cuatrimestres[pin.cuatri]:
            continue
        if m.semana == '':
            m.semana = primera_semana[pin.cuatri]
        if m.semana != pin.semana:
            m.semana = pin.semana
            api.cambiar_semana(m)
    with use_scope('aviso_cambio_semana', clear = True):
        pass
    api.actualizar_horario(horario)

def refrescar_curso(e):
    global horario, cursos, cuatrimestres
    horario = api.horario_curso(cursos[e], cuatrimestres[pin.cuatri])
    comprobar_semana()
    widget_grupos(pin.semana)
    render()
def refrescar_cuatri(e):
    global horario, cursos, cuatrimestres
    horario = api.horario_curso(cursos[pin.curso], cuatrimestres[e])
    comprobar_semana()
    widget_grupos(pin.semana)
    render()

def refrescar_grupo(tipo):
    global horario, cursos
    def wrapper(e):
        for m in horario.materias.values():
            if m.curso == cursos[pin.curso] and m.tipo != api.TipoMateria.OPTATIVO:
                m.grupo_seleccionado[tipo.value] = min(m.num_grupos[tipo.value], e)
        api.actualizar_horario(horario)
        render()
    return wrapper

def refrescar_semana(e):
    global horario, semanas
    comprobar_semana()
    render()

def incluir_materia():
    global horario, semanas
    m = materia(pin.buscar)
    api.incluir_en_horario(horario, m)
    comprobar_semana()
    widget_grupos()
    render()

def cambiar_grupo_materia(nombre, tipo):
    global horario
    def wrapper(e):
        horario.materias[nombre].grupo_seleccionado[tipo] = e
        api.actualizar_horario(horario)
        render()
    return wrapper

def eliminar_materia(nombre):
    global horario
    def wrapper():
        api.eliminar_de_horario(horario, nombre)
        widget_grupos()
        render()
    return wrapper

def resetear():
    confirmar = actions('Confirmas descartar todos los cambios?', ['Si', 'No'], help_text = 'La aplicación volverá a descargar la lista de grados y materias')
    if confirmar != 'Si':
        return

    global url, grados, grado
    url, grados, grado = None, None, None

    os.remove('materias.json')
    run_js('location.reload()')

def guardar():
    global horario
    # save
    with open('horario.html', 'w', encoding='utf-8') as f:
        f.write('<meta charset="UTF-8">')
        f.write(api.formato_horario(horario).to_html())
    with open('horario.csv', 'w') as f:
        f.write(horario.df.to_csv())

    confirmar = actions('Horario guardado! Quieres abrirlo?', ['Si', 'No'], help_text = 'El horario se ha guardado en html y csv en la carpeta del programa. Si quieres imprimirlo puedes abrir el html y guardarlo como pdf')
    if confirmar == 'Si':
        webbrowser.open('file://' + os.path.realpath('horario.html'), new=2)

def generar_semanas(lista):
    global semanas, primera_semana
    semanas = {}
    primera_semana = {}
    for m in lista:
        if not 'Primero' in semanas and m.cuatrimestre == 1:
            (semanas['Primero'], primera_semana['Primero']) = api.lista_semanas(m)
        if not 'Segundo' in semanas and m.cuatrimestre == 2:
            (semanas['Segundo'], primera_semana['Segundo']) = api.lista_semanas(m)

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
        grados = sorted(api.obtener_grados(url))
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
            grado = '^' + grado.replace('(', '[(]').replace(')', '[)]') + '$'
        grado = 'Grao en Ingeniería Informática (2ªed)'

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
    
    for n in api.generar_lista_materias(url, grado):
        if 'ERROR' in n:
            with use_scope('error'):
                put_error(f"Error obteniendo datos de '{n.split(' ')[1]}', inténtalo de nuevo más tarde")
        else:
            with use_scope('cargando', clear = True):
                put_info(f"Obteniendo datos de '{n}'")
    
    remove('cargando')
    remove('error')
    remove('grado')
    remove('url')

def widget_grupos(semana = None):
    with use_scope('seleccion_grupos', clear = True):
        global horario, semanas
        num_grupos = { t: -1 for t in api.TipoClase }
        for m in horario.materias.values():
            for t in m.grupo_seleccionado:
                num_grupos[t] = max(num_grupos[t], m.num_grupos[t])

        select_grupo = []
        for t in sorted(num_grupos.keys(), key = lambda x: api.tipo_clase_ch[x]):
            if num_grupos[t] < 1:
                continue
            select_grupo.append(put_select(f"grupo_{t.value}", options = list(range(1, num_grupos[t]+1)), value = 1, label = f"Grupo {t.value}"))
            select_grupo.append(None)
            pin_on_change(f"grupo_{t.value}", refrescar_grupo(t), clear = True)

        select_grupo.append(put_select('semana', options = semanas[pin.cuatri], label = 'Semana', value = semana))
        pin_on_change('semana', refrescar_semana, clear = True)

        put_row(select_grupo)
    
    with use_scope('aviso_cambio_semana', clear = True):
        pass

def widget_curso():
    global horario, cursos, cuatrimestres
    cursos = { 'Primero': 1, 'Segundo': 2, 'Tercero': 3, 'Cuarto': 4, 'Quinto': 5, 'Sexto': 6 }
    cursos = dict(filter(lambda x: x[1] <= max(m.curso for m in api.lista_materias()), cursos.items()))
    cuatrimestres = { 'Primero': 1, 'Segundo': 2 }

    with use_scope('seleccion', clear = True):
        put_row([
            put_select('curso', options = cursos.keys(), label = 'Curso'),
            None,
            put_select('cuatri', options = cuatrimestres.keys(), label = 'Cuatrimestre'),
        ])

        pin_on_change('curso', refrescar_curso)
        pin_on_change('cuatri', refrescar_cuatri)

def widget_buscar():
    global horario
    with use_scope('buscar', clear = True):
        materias = [ m.nombre for m in api.lista_materias() if m.cuatrimestre == cuatrimestres[pin.cuatri] and not m.nombre in horario.materias ]

        put_row([
            put_input('buscar', placeholder = 'Busca una materia', datalist = materias),
            None,
            put_button('Añadir', onclick = incluir_materia)
        ], 'auto 10px 76px')

def widget_bottom():
    with use_scope('bottom'):
        put_button('Guardar horario', onclick = guardar)
        put_button('Resetear o cambiar de grado', onclick = resetear)

# Display
# ---

def render():
    global horario
    with use_scope('horario', clear = True):
        def cambio_grupo(nombre, tipo, grupos, num_grupos):
            l = []
            for t in sorted(grupos.keys(), key = lambda x: api.tipo_clase_ch[x]):
                n = 'cambio' + t + unidecode(nombre.replace(' ', '_'))
                g = grupos[t]
                if g == -1:
                    l.append(put_select(n, options = [ '-' ]))
                    continue
                select = put_select(n, options = list(range(1 if tipo != api.TipoMateria.OPTATIVO else 0, num_grupos[t]+1)), value = g)
                pin_on_change(n, cambiar_grupo_materia(nombre, t), clear = True)
                l.append(select)
            l.append(put_button('X', onclick = eliminar_materia(nombre)))
            return put_row(l)

        grupos = '|'.join([api.tipo_clase_ch[t] for t in api.TipoClase])
        materias = [ [ put_html('<p style="margin:8px 0px;"><strong>Materia</strong></p>'), put_markdown(f"<p style='margin:8px 0px;'><strong>Grupos {grupos}</strong></p>") ] ]
        materias += [ [ f"{m.nombre} ({m.abreviatura})", cambio_grupo(m.nombre, m.tipo, m.grupo_seleccionado, m.num_grupos) ] for m in horario.materias.values() ]

        put_row([
            put_html(api.formato_horario(horario).to_html(border = 0)),
            None,
            put_grid(materias, cell_height='48px')
        ])

def main():
    set_env(output_max_width = '1000px')

    elegir_grado()
    generar_semanas(api.lista_materias())

    global horario
    horario = api.horario_curso(1, 1)

    widget_curso()
    widget_grupos()
    widget_buscar()
    render()
    widget_bottom()

if __name__ == '__main__':
    main()