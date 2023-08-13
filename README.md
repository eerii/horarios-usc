# Horarios USC ⏳

Pequeña utilidad que escanea los horarios de la página oficial de la USC y permite organizar las asignaturas, ver cómo cuadran los distintos grupos y probar todas las combinaciones deseadas.

https://github.com/josekoalas/horarios-usc/assets/22449369/ed177120-d904-4460-91fe-8d73611cfca0

- Horarios completos por curso
- Añadir o quitar asignaturas independientemente del curso
- Cambio de grupo global o por cada asignatura
- Grupos expositivos, interactivos y de seminario independientes
- Descarga los datos automáticamente
- Exportar el horario final

### Cómo utilizarlo 🌱

1. Descarga el proyecto o bien usando 'Code > Download ZIP' o poniendo:

```
git clone https://github.com/josekoalas/horarios-usc
```

2. Abre una terminal con python en la carpeta del proyecto

3. Instala los paquetes necesarios

```
pip install -r requirements.txt
```

4. Ejecuta el programa con

```
python horario.py
```

5. Se debería de abrir una ventana en el navegador. Te pedirá que introduzcas la url de tu carrera. Vienen algunas por defecto pero si no es la página del centro, del estilo `https://www.usc.gal/es/centro/NOMBRE`

6. Si todo va bien, debería de cargar los nombres de los grados ✨

https://github.com/josekoalas/horarios-usc/assets/22449369/014ae040-7388-4a48-bcca-27b3bfc42bf4
 
### Problemas conocidos 🚧

- Al iniciar el programa, tiene que descargar todos los datos del grado seleccionado. Esto puede tardar uno o dos minutos.
- De la misma manera, si se cambia de grado, hay que realizar la descarga de nuevo.
- Cambiar la fecha no está optimizado. Con cada nueva semana tiene que descargar los datos de la misma. Esto es intencional, ya que si no habría que descargar todos al principio y tardaría mucho más. Una solución asíncrona sería mejor pero está fuera del alcance de este proyecto. Solo se da esta opción para carreras que en las primeras semanas no tengan un horario completo.
- No hay una web del proyecto. Cómo escribí esto en python porque iba a ser un proyectito de un día y nada más, es difícil hostear esto sin mucho trabajo.
- El código es un desastre. En serio. Es terrible ;-;
