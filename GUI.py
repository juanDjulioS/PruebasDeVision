import PySimpleGUI as sg, cv2, tkinter as tk, matplotlib.pyplot as plt, time, serial
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from threading import Thread, Event
from queue import Queue
from vision import *

pixels_per_cm = None
processed_frame = None

cap = cv2.VideoCapture(0)
stop_event = Event()
layout = [[sg.Canvas(key="graph", size=(400, 200)), sg.Image(filename="", key="webcam", size=(300, 300), pad=((50, 50), (50, 50)))],
          [sg.Text("pwm:"), sg.Slider(range=(0, 255), key="pwm_slider", enable_events=True, orientation="h")],
          [sg.InputText(key="pwm_text", enable_events=True), sg.Button("Update")],
          [sg.Text("Obstacle Sensor State"), sg.Canvas(key="circle",size=(40,40))],
          [sg.Text("Classifier")], [[sg.Checkbox("Color", key="color_checkbox", enable_events=True)]
, [sg.Checkbox("Shape", key="shape_checkbox", enable_events=True)]
, [sg.Checkbox("Size", key="size_checkbox", enable_events=True)]
, sg.Button("Calibrate Camera")],
          [sg.Button("Stop", size=(10, 1), pad=((0, 280), 3), font="Helvetica 14")]]
window = sg.Window("GUI en python", layout)
window.read(timeout=0)
time_values = []
start_time = time.time()
graph = window["graph"].TKCanvas
fig, ax = plt.subplots(figsize=(4,3))
ax.set_ylim(0, 400)
ax.set_xlabel('Tiempo (s)')
ax.set_ylabel('Velocidad (rpm)')
fig.tight_layout()
plt.close(fig)
canvas = FigureCanvasTkAgg(fig, master=window["graph"].TKCanvas)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
circle = window["circle"].TKCanvas
circle.create_oval(5, 5, 35, 35, fill='gray')
def update_graph(time_values, rpm_values):
    if len(time_values) != len(rpm_values) or len(time_values) < 10:
        return
    ax.clear()
    ax.set_ylim(0, 400)
    ax.set_xlabel('Tiempo (s)')
    ax.set_ylabel('Velocidad (rpm)')
    ax.plot(time_values[-10:], rpm_values[-10:])
    fig.canvas.draw()
    fig.tight_layout()
def update_circle(obstacle_sensor_state_value):
    if window.was_closed():
        return
    if obstacle_sensor_state_value == 1:
        circle.itemconfig(1, fill='green')
    else:
        circle.itemconfig(1, fill='red')
data_queue = Queue()
def read_serial_data(port, baudrate):
    while not stop_event.is_set():
        try:
            ser = serial.Serial(port, baudrate)
            break
        except serial.SerialException as e:
            print(f"Error al conectar al puerto serial {port}")
            time.sleep(1)
    obstacle_sensor_state_value = 0
    while not stop_event.is_set():
        line = ser.readline().decode('utf-8',errors='ignore').strip()
        data_list = line.split('_')
        if len(data_list) == 2:
            try:
                rpm_value = int(data_list[0])
                obstacle_sensor_state_value = int(data_list[1])
                current_time = time.time() - start_time
                time_values.append(current_time)
                data_queue.put((rpm_value, obstacle_sensor_state_value))
            except ValueError:
                pass
thread = Thread(target=read_serial_data,args=("COM3",9600))
thread.start()
rpm_values = []
obstacle_sensor_state_value = 0
def show_webcam(frame):
    # Redimensionar la imagen al tamaño del widget Image (300x300)
    frame = cv2.resize(frame,(300,300))
    imgbytes=cv2.imencode('.png',frame)[1].tobytes()
    window["webcam"].update(data=imgbytes)
    window.refresh()

#show_webcam()
current_time=int(round(time.time()*1000))
interval=0
calibrated=False
while True:
 event, values=window.read(timeout=10)
 ret, frame = cap.read()
 if event=="Stop" or event==sg.WIN_CLOSED:
     stop_event.set()
     break
 elif event=="Update":
     try:
         pwm_value=int(values["pwm_text"])
         window["pwm_slider"].update(value=pwm_value)
     except ValueError:
         pass
 elif event=="pwm_slider":
     pwm_value=int(values["pwm_slider"])
     window["pwm_text"].update(value=pwm_value)

 elif event == "Calibrate Camera":
    pixels_per_cm = calibrate_camera(frame)
    if pixels_per_cm is not None:
        calibrated = True
        print(f"Pixels per cm: {pixels_per_cm}")

 now=int(round(time.time()*1000))
 if now - current_time >= interval:
    if not any([values["color_checkbox"], values["shape_checkbox"], values["size_checkbox"]]):
        show_webcam(frame)
    current_time = now

 if not data_queue.empty():
     rpm_value,obstacle_sensor_state_value=data_queue.get()
     rpm_values.append(rpm_value)
     update_graph(time_values,rpm_values)
     update_circle(obstacle_sensor_state_value)
     
 if event == "color_checkbox" and values["color_checkbox"]:
    window["shape_checkbox"].update(value=False)
    window["size_checkbox"].update(value=False)
 elif event == "shape_checkbox" and values["shape_checkbox"]:
    window["color_checkbox"].update(value=False)
    window["size_checkbox"].update(value=False)
 elif event == "size_checkbox" and values["size_checkbox"]:
    if not calibrated:
        sg.popup("Debes calibrar la cámara antes de poder usar la función de detección de tamaño. Coloca un círculo debajo de la cámara con un diámetro conocido y presiona el botón 'Calibrate Camera'.")
        window["size_checkbox"].update(value=False)
    else:
        window["color_checkbox"].update(value=False)
        window["shape_checkbox"].update(value=False)

 if values["color_checkbox"]:
    servo_code, processed_frame = classifier_selector(frame, option="color")
    show_webcam(processed_frame)
 elif values["shape_checkbox"]:
    servo_code, processed_frame = classifier_selector(frame, option="shape")
    show_webcam(processed_frame)
 elif values["size_checkbox"]:
    servo_code, processed_frame = classifier_selector(frame, option="size")
    if processed_frame is not None:
        show_webcam(processed_frame)
    else:
        show_webcam(frame)
window.close()
cap.release()
