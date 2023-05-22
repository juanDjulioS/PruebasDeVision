import PySimpleGUI as sg
import cv2 # Importar la biblioteca OpenCV
from PIL import Image, ImageTk # Importar las bibliotecas PIL para redimensionar imágenes
import tkinter as tk
import matplotlib.pyplot as plt # Importar la biblioteca matplotlib para crear gráficos
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # Importar la clase
import time # Importar la biblioteca time para usar un temporizador
import serial
from threading import Thread
from queue import Queue
from threading import Event

# Crear un objeto VideoCapture para acceder a la cámara web
cap = cv2.VideoCapture(0)

# Crea un objeto Event para señalar cuándo el hilo debe detenerse
stop_event = Event()

# Crear el layout de la GUI
layout = [
    # 1. Recuadro para la cámara web y gráfico de rpm vs tiempo en la misma fila
    [sg.Canvas(key="graph", size=(400, 200)),
     sg.Image(filename="", key="webcam", size=(300, 300), pad=((50, 50), (50, 50)))],
    # 3. Deslizador y cuadro de texto para la pwm
    [sg.Text("pwm:"), sg.Slider(range=(0, 255), key="pwm_slider", enable_events=True, orientation="h")],
    [sg.InputText(key="pwm_text", enable_events=True), sg.Button("Update")],
    # 5. Circulo y etiqueta para el sensor de obstáculos
    [sg.Text("Obstacle Sensor State"), sg.Canvas(key="circle",size=(40,40))],
    # 6. Etiqueta y botones para el clasificador
    [sg.Text("Classifier")],
    [sg.Button("Color"), sg.Button("Shape"), sg.Button("Size"), sg.Button("Calibrate Camera")],
    # 7. Botón para detener la interfaz
    [sg.Button("Stop", size=(10, 1), pad=((0, 280), 3), font="Helvetica 14")]
]


# Crear la ventana de la GUI
window = sg.Window("GUI en python", layout)

# Leer la ventana una vez para inicializarla
window.read(timeout=0)

# Crear el gráfico de rpm vs tiempo (Requerimiento 2)
time_values = []
start_time = time.time()

graph = window["graph"].TKCanvas
# Aquí se pueden añadir los datos del gráfico usando el método plot del objeto graph

# Crear un objeto Figure y un objeto Axes para el gráfico (Requerimiento 2)
fig, ax = plt.subplots(figsize=(4,3))
ax.set_ylim(0, 400) # Establecer los límites del eje y
ax.set_xlabel('Tiempo (s)') # Establecer la leyenda del eje x
ax.set_ylabel('Velocidad (rpm)') # Establecer la leyenda del eje y
fig.tight_layout()

# Cierra la figura para que no se muestre en la salida del notebook
plt.close(fig)

# Crear un objeto FigureCanvasTkAgg para mostrar el gráfico en el widget Canvas (Requerimiento 2)
canvas = FigureCanvasTkAgg(fig, master=window["graph"].TKCanvas)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# Crear el circulo para el sensor de obstáculos (Requerimiento 5)
circle = window["circle"].TKCanvas
# Aquí se puede dibujar el circulo usando el método create_oval del objeto circle
circle.create_oval(5, 5, 35, 35, fill='gray') # Dibujar un circulo rojo

# Crear una función para actualizar el gráfico con los nuevos datos
def update_graph(time_values, rpm_values, max_values=10):
    if len(time_values) != len(rpm_values) or len(time_values) < max_values:
        return
    ax.clear() # Limpiar gráfico anterior
    ax.set_ylim(0, 400)
    ax.set_xlabel('Tiempo (s)')
    ax.set_ylabel('Velocidad (rpm)')
    # Mostrar solo los últimos max_values valores en la gráfica
    ax.plot(time_values[-max_values:], rpm_values[-max_values:])
    fig.canvas.draw() # Redibujar gráfico
    fig.tight_layout() # Ajustar automáticamente el tamaño y la posición de los elementos del gráfico
 
# Crear una función para actualizar el círculo con el nuevo estado del sensor
def update_circle(obstacle_sensor_state_value):
    #print(obstacle_sensor_state_value)
    if window.was_closed():
        return
    if obstacle_sensor_state_value == 1:   # Si estado sensor obstáculo es 1 (Requerimiento adicional)
        circle.itemconfig(1, fill='green')   # Cambiar color círculo a verde (Requerimiento adicional)
    else:   # Si estado sensor obstáculo es 0 (Requerimiento adicional)
        circle.itemconfig(1, fill='red')   # Cambiar color círculo a rojo (Requerimiento adicional)

# Crear una cola para comunicar los datos recibidos desde el puerto serial al hilo principal de la aplicación
data_queue = Queue()

def read_serial_data(port, baudrate):
    """
    Función que lee datos desde un puerto serial y actualiza un gráfico y un círculo con los datos recibidos.
    :param port: El nombre del puerto serial.
    :type port: str.
    
    :param baudrate: La velocidad en baudios.
    :type baudrate: int.
    
    :return: None.
    
    """
    # Verifica si se ha señalado el evento de detenerse
    while not stop_event.is_set():
        try:
            # Crear un objeto Serial para comunicarse con el puerto serial (Requerimiento adicional)
            ser = serial.Serial(port, baudrate)
            break
        except serial.SerialException as e:
            # Mostrar un mensaje de error si ocurre una excepción al intentar crear el objeto Serial
            print(f"Error al conectar al puerto serial {port}")
            time.sleep(1) # Espera 1 segundo antes de volver a intentarlo

    # Crear una variable para guardar el estado del sensor
    obstacle_sensor_state_value = 0

    # Lee datos del puerto serial
    while not stop_event.is_set():
        line = ser.readline().decode('utf-8',errors='ignore').strip()   # Leer una línea desde el puerto serial (Requerimiento adicional)
        data_list = line.split('_')   # Dividir los datos recibidos por '_' (Requerimiento adicional)
        if len(data_list) == 2:
            try:
                rpm_value = int(data_list[0])   # Obtener valor RPM como entero (Requerimiento adicional)
                obstacle_sensor_state_value = int(data_list[1])   # Obtener valor estado sensor obstáculo como entero (Requerimiento adicional)
                
                current_time = time.time() - start_time
                time_values.append(current_time)

                # Enviar los datos recibidos a la cola
                data_queue.put((rpm_value, obstacle_sensor_state_value))
                #print(f"Queue size after put: {data_queue.qsize()}")

            except ValueError:
                pass

# Crear un objeto Thread para ejecutar la función read_serial_data en un hilo de ejecución separado
thread = Thread(target=read_serial_data, args=("COM3", 9600))

# Iniciar el hilo de ejecución
thread.start()

# Crear una lista vacía para guardar los valores de rpm (Requerimiento adicional)
rpm_values = []

# Crear una variable para guardar el estado del sensor de obstáculos (Requerimiento adicional)
obstacle_sensor_state_value = 0

# Crear una función que capture y muestre los fotogramas de la cámara web en el widget Image usando el método update() del objeto window["webcam"] (Requerimiento 1)
def show_webcam():
    # Leer un fotograma de la cámara web
    ret, frame = cap.read()
    if ret: # Si se ha leído correctamente

        # Redimensionar la imagen al tamaño del widget Image (300x300)
        frame = cv2.resize(frame, (300, 300))

        imgbytes = cv2.imencode('.png', frame)[1].tobytes() # Convertir la imagen a bytes

        window["webcam"].update(data=imgbytes) # Actualizar el widget Image con los bytes de la imagen

        # Actualizar la interfaz gráfica con el método refresh()
        window.refresh()

# Crear una variable para guardar el tiempo actual en milisegundos
current_time = int(round(time.time() * 1000))

# Crear una variable para guardar el intervalo de tiempo entre llamadas a la función show_webcam() en milisegundos
interval = 10

# Llamar a la función show_webcam una vez para iniciar el bucle de captura y muestra de los fotogramas de la cámara web (Requerimiento 1)
show_webcam()

# Crear un bucle de eventos para manejar las acciones del usuario
while True:
    event, values = window.read(timeout=10)
    if event == "Stop" or event == sg.WIN_CLOSED:
        # Señala el evento de detenerse para detener el hilo
        stop_event.set()
        break # Salir del bucle si se cierra la ventana o se pulsa el botón Stop (Requerimiento 7)
    elif event == "Update":
        # Actualizar el valor del deslizador según el cuadro de texto (Requerimiento 4)
        try:
            pwm_value = int(values["pwm_text"])
            window["pwm_slider"].update(value=pwm_value)
        except ValueError:
            pass # Ignorar si el valor no es un entero válido
    elif event == "pwm_slider":
        # Actualizar el valor del cuadro de texto según el deslizador (Requerimiento 4)
        pwm_value = int(values["pwm_slider"])
        window["pwm_text"].update(value=pwm_value)
    elif event == "Color" or event == "Shape" or event == "Size":
        # Aquí se puede añadir el código para clasificar la imagen según el botón pulsado (Requerimiento 6)
        pass
    elif event == "Calibrate Camera":
        # Aquí se puede añadir el código para calibrar la cámara (Requerimiento 6)
        pass

    # Obtener el tiempo actual en milisegundos
    now = int(round(time.time() * 1000))

    # Si ha pasado el intervalo de tiempo desde la última llamada a show_webcam(), llamar a la función nuevamente (Requerimiento 1)
    if now - current_time >= interval:
        show_webcam()
        current_time = now
    
    # Verificar si hay datos disponibles en la cola
    if not data_queue.empty():
        
        # Obtener los datos desde la cola
        rpm_value, obstacle_sensor_state_value = data_queue.get()
        rpm_values.append(rpm_value)   # Agregar valor RPM a lista RPM values (Requerimiento adicional)

        update_graph(time_values,rpm_values,10)
        update_circle(obstacle_sensor_state_value)
        
window.close() # Cerrar la ventana al salir del bucle (Requerimiento 7)
cap.release() # Liberar los recursos de la cámara web (Requerimiento 7)
