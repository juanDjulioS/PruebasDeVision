import PySimpleGUI as sg
import tkinter as tk
import matplotlib.pyplot as plt
import time
import serial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from threading import Thread, Event
from cvband import *
from collections import deque, Counter

pixels_per_cm = None
processed_frame = None
pwm_value = 0
ser = None
servo_code='2'
cap = cv2.VideoCapture(WEBCAM)
DETECTION_TIME = 2
sg.theme("DarkBlue")
stop_event = Event()
data_deque = deque(maxlen=MAX_SAMPLES)


layout = [
    [
        sg.Column([
            [sg.Image(filename="logo.png",size=(100,100)), sg.Text("CVBAND Project", font=("Helvetica", 24))],
            [sg.Canvas(key="graph", size=(400, 200))],
            [sg.Text("PWM", font=("Helvetica", 16,'bold'),text_color='white')],
            [sg.Slider(range=(0, 255), key="pwm_slider", enable_events=True, orientation="h", pad=((0, 0), (0, 15)),size=(20, 20)),
             sg.InputText(key="pwm_text", enable_events=True, size=(20, 1),pad=((80,0), (0,0))),sg.Button("Update", font=("Helvetica", 12,'bold'), button_color=('white', '#1B6497'), size=(10, 1),pad=((14,0), (0,0)))],
            [sg.Text("Obstacle Sensor State",font=("Helvetica", 16,'bold'), text_color='white'), sg.Text("px/cm: ",key="calibration_text", font = "Helvetica 12 normal")],
            [sg.Canvas(key="led", size=(40, 40))],
            [sg.Text("Classifier",font=("Helvetica", 16, 'bold'), text_color='white')],
            [sg.Checkbox("Color", key="color_checkbox", enable_events=True, font=("Helvetica", 12), text_color='white', size=(10, 1))],
            [sg.Checkbox("Shape", key="shape_checkbox", enable_events=True, font=("Helvetica", 12), text_color='white', size=(10, 1))],
            [sg.Checkbox("Size", key="size_checkbox", enable_events=True, font=("Helvetica", 12), text_color='white', size=(10, 1))],
            [sg.Button("Calibrate Camera", size=(15, 1), font="Helvetica 16  bold",button_color=('white','#1B6497')),sg.Button("Stop", size=(10, 1), font="Helvetica 16 bold",button_color=('white','red'), pad=((180,0), (0,0)))]
        ],expand_x=True),
        sg.Column([
            [sg.Frame(title="", layout=[[sg.Image(filename="", key="webcam", size=CAMERA_ZISE)]], border_width=5,title_color='#1B6497')],
            [sg.Text("Powered by "),sg.Image(filename="bing.png"),sg.Image(filename="chatgpt.png")]
        ], element_justification='center',expand_x=True),
    ],
]


# Crear la ventana principal
window = sg.Window("VISABAT Inc.", layout, finalize=True, resizable=True)
window.read(timeout=0)
window.Maximize()

# Ocultar la ventana principal mientras se cargan y posicionan los elementos
window.Hide()

start_time_read = time.time()
graph = window["graph"].TKCanvas

fig, ax = plt.subplots(figsize=(5.3,2.2))
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
ax.set_title("REAL-TIME RPM READING",color='white', fontname='Arial', fontweight='bold', fontsize=20, fontstyle='italic')


line, =ax.plot([],[],linewidth=2, linestyle='solid')
fig.set_facecolor('#1A2835')
line.set_color('white')
ax.fill_between([], [], color='white', alpha=0.9)
fig.tight_layout()
plt.close(fig)

canvas = FigureCanvasTkAgg(fig, master=window["graph"].TKCanvas)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
LED = window["led"].TKCanvas
update_led(LED,0)

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
    if frame is not None:   
        frame = cv2.resize(frame, CAMERA_ZISE)
    imgbytes = cv2.imencode('.png', frame)[1].tobytes()
    window["webcam"].update(data=imgbytes)
    window.refresh()

def read_serial_data(baudrate):
    global ser
    port = None
    while not stop_event.is_set():
        port = get_arduino_port()
        if port is not None:
            break
        time.sleep(1)
    ser = serial.Serial(port, baudrate)
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

def handle_checkbox_event(event, values):
    if event == "color_checkbox" and values["color_checkbox"]:
        window["shape_checkbox"].update(value=False)
        window["size_checkbox"].update(value=False)

    elif event == "shape_checkbox" and values["shape_checkbox"]:
        window["color_checkbox"].update(value=False)
        window["size_checkbox"].update(value=False)

    elif event == "size_checkbox" and values["size_checkbox"]:
        if not calibrated:
            sg.popup_non_blocking("Debes calibrar la cámara antes de poder usar la función de detección de tamaño. Coloca un círculo debajo de la cámara con un diámetro conocido y presiona el botón 'Calibrate Camera'.")
            window["size_checkbox"].update(value=False)
        else:
            window["color_checkbox"].update(value=False)
            window["shape_checkbox"].update(value=False)

thread = Thread(target=read_serial_data, args=(BAUDRATE,))
thread.start()
current_time = int(round(time.time()*1000))
calibrated = False
obstacle_detected = False
start_time = None
servo_codes = Counter()
color_mask = None
# Mostrar la ventana principal una vez que todo esté listo
window.UnHide()
detection_start_time = None

while True:
    event, values = window.read(timeout=1)
    ret, frame = cap.read()
    if data_deque:
        _, _, obstacle_sensor_state_value = data_deque[-1]
        time_values = [data[0] for data in data_deque]
        rpm_values = [data[1] for data in data_deque]
        if obstacle_sensor_state_value == 1 and not obstacle_detected:
            obstacle_detected = True
            start_time = time.time()
        update_graph(time_values, rpm_values)
        update_led(LED,obstacle_sensor_state_value)
    if event == "Stop" or event == sg.WIN_CLOSED:
        stop_event.set()
        if ser is not None:
            ser.write(f"0_2\n".encode())
        cap.release()
        break
    
    elif event == "Calibrate Camera":
        pixels_per_cm = calibrate_camera(frame,CIRCLE_DIAMETER)
        if pixels_per_cm is not None:
            calibrated = True
            window["calibration_text"].update(f"px/cm: {pixels_per_cm:.2f}")
                 
    # Llamada a la función handle_checkbox_event para manejar los eventos de los checkboxes
    handle_checkbox_event(event, values)       
    
    # Eventos para modificar pwm_value       
    if event == "Update":
        try:
            pwm_value = int(values["pwm_text"])
            window["pwm_slider"].update(value=pwm_value)
            if ser is not None:
                ser.write(f"{pwm_value}_{servo_code}\n".encode())
        except ValueError:
            pass   
        
    elif event == "pwm_slider":
        pwm_value = int(values["pwm_slider"])
        window["pwm_text"].update(value=pwm_value)
        if ser is not None:   
            ser.write(f"{pwm_value}_{servo_code}\n".encode())
  
    # Eventos para modificar servo_code
    if values["color_checkbox"] and obstacle_detected:
        servo_code, processed_frame, color_mask = color_detector(frame)
        servo_codes[servo_code] += 1
        if processed_frame is not None:
            show_webcam(processed_frame)
    
        if time.time() - start_time >= PROCESSING_TIME:
            most_common_servo_code = servo_codes.most_common(1)[0][0]
            servo_code = most_common_servo_code
            if ser:
                ser.write(f"{pwm_value}_{servo_code}\n".encode())
                pass
            obstacle_detected = False
            start_time = None
            servo_codes.clear()
    elif values["shape_checkbox"] and obstacle_detected:
        servo_code, processed_frame = shape_detector(frame)
        servo_codes[servo_code] += 1
        if processed_frame is not None:
            show_webcam(processed_frame)
        if time.time() - start_time >= PROCESSING_TIME:
            most_common_servo_code = servo_codes.most_common(1)[0][0]
            servo_code = most_common_servo_code  # Actualizar el valor de servo_code
            if ser:
                ser.write(f"{pwm_value}_{most_common_servo_code}\n".encode())
            obstacle_detected = False
            start_time = None
            servo_codes.clear()
    
    elif values["size_checkbox"] and obstacle_detected:
        servo_code, processed_frame = size_detector(frame, pixels_per_cm, LARGE_SIZE_THRESHOLD, MEDIUM_SIZE_THRESHOLD)
        servo_codes[servo_code] += 1
        show_webcam(processed_frame)
        if time.time() - start_time >= PROCESSING_TIME:
            most_common_servo_code = servo_codes.most_common(1)[0][0]
            servo_code = most_common_servo_code  # Actualizar el valor de servo_code
            if ser is not None:  
                ser.write(f"{pwm_value}_{most_common_servo_code}\n".encode())
            obstacle_detected = False
            start_time = None
            servo_codes.clear()
    
    else:
        now = int(round(time.time()*1000))
        if now - current_time >= INTERVAL:
            show_webcam(frame)
            current_time = now
    window.refresh()
window.close()
cap.release()
