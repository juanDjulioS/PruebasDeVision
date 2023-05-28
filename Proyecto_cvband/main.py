import PySimpleGUI as sg
import cv2
import tkinter as tk
import matplotlib.pyplot as plt
import time
import serial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from threading import Thread, Event
from cvband import *
from collections import deque
from statistics import mode

pixels_per_cm = None
processed_frame = None
pwm_value = 0
ser = None
servo_code='2'
cap = cv2.VideoCapture(CAMERA_WEB)

sg.theme("DarkBlue")
stop_event = Event()
data_deque = deque(maxlen=MAX_SAMPLES)
CAMERA_ZISE = (600,600)
layout = [
    [
        sg.Column([
            [sg.Canvas(key="graph", size=(400, 200))],
            [sg.Text("PWM", font=("Helvetica", 16,'bold'),text_color='white')],
            [sg.Slider(range=(0, 255), key="pwm_slider", enable_events=True, orientation="h", pad=((0, 0), (0, 15)),size=(20, 20)),
             sg.InputText(key="pwm_text", enable_events=True, size=(20, 1),pad=((65,0), (0,0))),sg.Button("Update", font=("Helvetica", 12,'bold'), button_color=('white', '#1B6497'), size=(10, 1),pad=((15,0), (0,0)))],
            [sg.Text("Obstacle Sensor State",font=("Helvetica", 16,'bold'), text_color='white')],
            [sg.Canvas(key="led", size=(40, 40))],
            [sg.Text("Classifier",font=("Helvetica", 16, 'bold'), text_color='white')],
            [sg.Checkbox("Color", key="color_checkbox", enable_events=True, font=("Helvetica", 12), text_color='white', size=(10, 1))],
            [sg.Checkbox("Shape", key="shape_checkbox", enable_events=True, font=("Helvetica", 12), text_color='white', size=(10, 1))],
            [sg.Checkbox("Size", key="size_checkbox", enable_events=True, font=("Helvetica", 12), text_color='white', size=(10, 1))],
            [sg.Button("Calibrate Camera", size=(15, 1), font="Helvetica 16  bold",button_color=('white','#1B6497')),sg.Button("Stop", size=(10, 1), font="Helvetica 16 bold",button_color=('white','red'), pad=((179,0), (0,0)))],
        ]),
        sg.Column([
            [sg.Frame(title="", layout=[[sg.Image(filename="", key="webcam", size=CAMERA_ZISE)]], border_width=5,title_color='#1B6497')],
        ], element_justification='center', pad=((50, 50), (50, 50))),
    ],
]
window = sg.Window("CVBand GUI", layout)
window.read(timeout=0)
window.Maximize()

start_time_read = time.time()
graph = window["graph"].TKCanvas

fig, ax = plt.subplots(figsize=(5.1,2.2))

ax.set_facecolor('#1A2835')
ax.tick_params(colors='white')
ax.xaxis.label.set_color('white')
ax.yaxis.label.set_color('white')
ax.spines['bottom'].set_color('white')
ax.spines['top'].set_color('white')
ax.spines['left'].set_color('white')
ax.spines['right'].set_color('white')

ax.set_ylim(0, 430)
ax.set_xlabel('time (s)')
ax.set_ylabel('velocity (rpm)')
ax.set_title("Real-time rpm reading",color='white', fontname='Arial', fontweight='bold', fontsize=20, fontstyle='italic')


line, =ax.plot([],[],linewidth=2, linestyle='solid')
fig.set_facecolor('#1A2835')
line.set_color('white')
ax.fill_between([], [], color='white', alpha=0.9)
fig.tight_layout()
plt.close(fig)

canvas = FigureCanvasTkAgg(fig, master=window["graph"].TKCanvas)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
LED = window["led"].TKCanvas
# LED apagado
LED.create_oval(5, 5, 35, 35, fill='#555555', outline='#555555')
LED.create_oval(4, 4, 36, 36, outline='#666666', width=1)
LED.create_oval(3, 3, 37, 37, outline='#777777', width=1)
LED.create_oval(2, 2, 38, 38, outline='#888888', width=1)
LED.create_oval(1, 1, 39, 39, outline='#999999', width=1)

def update_graph(time_values, rpm_values):
    window_size = 5
    if len(rpm_values) >= window_size:
        smoothed_rpm_values = moving_average(rpm_values, window_size)
        line.set_data(time_values[window_size-1:], smoothed_rpm_values)
        canvas.draw()
        ax.relim()
        ax.autoscale_view()

def show_webcam(frame):
    # Redimensionar la imagen al tamaño del widget Image (300x300)
    frame = cv2.resize(frame, CAMERA_ZISE)
    imgbytes = cv2.imencode('.png', frame)[1].tobytes()
    window["webcam"].update(data=imgbytes)
    window.refresh()

def read_serial_data(port, baudrate):
    global ser
    while not stop_event.is_set():
        try:
            ser = serial.Serial(port, baudrate)
            break
        except serial.SerialException as e:
            print(f"Error al conectar al puerto serial {port}")
            time.sleep(1)
    obstacle_sensor_state_value = 0
    while not stop_event.is_set():
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        data_list = line.split('_')
        if len(data_list) == 2:
            try:
                rpm_value = int(data_list[0])
                obstacle_sensor_state_value = int(data_list[1])
                current_time = time.time() - start_time_read
                data_deque.append((current_time, rpm_value, obstacle_sensor_state_value))
            except ValueError:
                pass

thread = Thread(target=read_serial_data, args=(get_arduino_port(), BAUDRATE))
thread.start()
current_time = int(round(time.time()*1000))
calibrated = False
obstacle_detected = False
start_time = None
servo_codes = []

while True:
    event, values = window.read(timeout=100)
    ret, frame = cap.read()
    
    if event == "Stop" or event == sg.WIN_CLOSED:
        stop_event.set()
        ser.write(f"0_2\n".encode())
        cap.release()
        break
    
    elif event == "Calibrate Camera":
        pixels_per_cm = calibrate_camera(frame)
        if pixels_per_cm is not None:
            calibrated = True
            print(f"Pixels per cm: {pixels_per_cm}")
                 
    elif event == "color_checkbox" and values["color_checkbox"]:
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
    # Eventos para modificar pwm_value       
    elif event == "Update":
        try:
            pwm_value = int(values["pwm_text"])
            window["pwm_slider"].update(value=pwm_value)
            ser.write(f"{pwm_value}_{servo_code}\n".encode())
        except ValueError:
            pass   
        
    elif event == "pwm_slider":
        pwm_value = int(values["pwm_slider"])
        window["pwm_text"].update(value=pwm_value)
        ser.write(f"{pwm_value}_{servo_code}\n".encode())
  
    # Eventos para modificar servo_code
    if values["color_checkbox"] and obstacle_detected:
        servo_code, processed_frame = color_detector(frame)
        servo_codes.append(servo_code)
        show_webcam(processed_frame)
        if time.time() - start_time >= DETECTION_TIME:
            most_common_servo_code = mode(servo_codes)
            servo_code = most_common_servo_code
            ser.write(f"{pwm_value}_{servo_code}\n".encode())
            window["color_checkbox"].update(value=False)
            obstacle_detected = False
            start_time = None
            servo_codes.clear()
    
    elif values["shape_checkbox"] and obstacle_detected:
        servo_code, processed_frame = shape_detector(frame)
        servo_codes.append(servo_code)
        show_webcam(processed_frame)
        if time.time() - start_time >= DETECTION_TIME:
            most_common_servo_code = mode(servo_codes)
            servo_code = most_common_servo_code  # Actualizar el valor de servo_code
            ser.write(f"{pwm_value}_{most_common_servo_code}\n".encode())
            window["shape_checkbox"].update(value=False)
            obstacle_detected = False
            start_time = None
            servo_codes.clear()
    
    elif values["size_checkbox"] and obstacle_detected:
        servo_code, processed_frame = size_detector(frame, pixels_per_cm, LARGE_SIZE_THRESHOLD, MEDIUM_SIZE_THRESHOLD)
        servo_codes.append(servo_code)
        show_webcam(processed_frame)
        if time.time() - start_time >= DETECTION_TIME:
            most_common_servo_code = mode(servo_codes)
            servo_code = most_common_servo_code  # Actualizar el valor de servo_code
            ser.write(f"{pwm_value}_{most_common_servo_code}\n".encode())
            window["size_checkbox"].update(value=False)
            obstacle_detected = False
            start_time = None
            servo_codes.clear()
    
    else:
        now = int(round(time.time()*1000))
        if now - current_time >= INTERVAL:
            show_webcam(frame)
            current_time = now
     
    if data_deque:
        _, _, obstacle_sensor_state_value = data_deque[-1]
        time_values = [data[0] for data in data_deque]
        rpm_values = [data[1] for data in data_deque]
        if obstacle_sensor_state_value == 1 and not obstacle_detected:
            obstacle_detected = True
            start_time = time.time()
        update_graph(time_values, rpm_values)
        update_led(LED,obstacle_sensor_state_value)
        
    window.refresh()

window.close()

cap.release()
