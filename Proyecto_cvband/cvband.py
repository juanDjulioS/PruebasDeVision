import cv2
import numpy as np
import serial.tools.list_ports

MAX_SAMPLES = 100  # número máximo de muestras a almacenar
WEBCAM = 1
LARGE_SIZE_THRESHOLD = 5.0
MEDIUM_SIZE_THRESHOLD = 4.0
SMALL_SIZE_THRESHOLD = 2.0
CIRCLE_DIAMETER = 5.0
DETECTION_DELAY = 2
PROCESSING_TIME = 2

INTERVAL = 0
BAUDRATE = 9600
CAMERA_ZISE = (600,600)

# Función para detectar la forma, se usa tanto en forma como tamaño
def detect_shape(c):

    servo_code = None

    # Inicializar el nombre de la forma y el perímetro aproximado
    shape = None
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.04 * peri, True)

    # Si el contorno tiene 3 vértices, entonces es un triángulo
    if len(approx) == 3:
        shape = "Triangle"
        servo_code = '0'

    # Si el contorno tiene 4 vértices, entonces es un cuadrado o un rectángulo
    elif len(approx) == 4:
        # Calcular la relación de aspecto de la figura
        (x, y, w, h) = cv2.boundingRect(approx)
        ar = w / float(h)

        # Un cuadrado tendrá una relación de aspecto cercana a uno,
        # mientras que un rectángulo tendrá una relación de aspecto mayor o menor que uno
        if ar >= 0.95 and ar <= 1.05:
            shape = "Square"
            servo_code = '1'
        else:
            shape = "Rectangle"
            servo_code = '1'

    # Si el contorno es un círculo
    else:
        shape = "Circle"
        servo_code = '2'

    # Devolver el nombre de la forma
    return servo_code, shape

# FUNCIONES DE CLASIFICACIÓN DE VISION
def color_detector(frame,draw=True):

    servo_code = None
    red_lower = np.array([0, 120, 70])
    red_upper = np.array([10, 255, 255])
    yellow_lower = np.array([20, 100, 100])
    yellow_upper = np.array([30, 255, 255])
    green_lower = np.array([31, 16, 17])
    green_upper = np.array([78, 255,255])

    #frame = cv2.resize(frame,CAMERA_ZISE)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask_red = cv2.inRange(hsv, red_lower, red_upper)
    mask_yellow = cv2.inRange(hsv, yellow_lower, yellow_upper)
    mask_green = cv2.inRange(hsv, green_lower, green_upper)

    kernel = np.ones((5,5),np.uint8)
    mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, kernel)
    mask_yellow = cv2.morphologyEx(mask_yellow, cv2.MORPH_OPEN, kernel)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)

    red_count = cv2.countNonZero(mask_red)
    yellow_count = cv2.countNonZero(mask_yellow)
    green_count = cv2.countNonZero(mask_green)

    if red_count > yellow_count and red_count > green_count:
        color = "red"
        color_code = (0, 0, 255)
        servo_code = '0'
    elif yellow_count > red_count and yellow_count > green_count:
        color = "yellow"
        color_code = (0, 255, 255)
        servo_code = '1'
    elif green_count > red_count and green_count > yellow_count:
        color = "green"
        color_code = (0, 255, 0)
        servo_code = '2'
    else:
        return None, frame, None
    mask = cv2.bitwise_or(mask_red, mask_yellow)
    mask = cv2.bitwise_or(mask, mask_green)

    kernel = np.ones((5,5),np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    color_area_threshold = 250

    max_area = 0
    max_c = None
    for c in contours:
        area = cv2.contourArea(c)
        if area > color_area_threshold and area > max_area:
            max_area = area
            max_c = c

    if draw:
        if max_c is not None:
            x,y,w,h = cv2.boundingRect(max_c)
            cv2.rectangle(frame,(x,y),(x+w,y+h),color_code,2)
        cv2.putText(frame,color,(frame.shape[1]-100,50),cv2.FONT_HERSHEY_SIMPLEX,1,color_code,2,cv2.LINE_AA)

    return servo_code, frame, mask

def shape_detector(frame):
    _, _, mask = color_detector(frame,draw=False)
        # Verificar que la máscara no esté vacía
    if mask is None or mask.size == 0:
        return None, None
    
    # Suavizar la máscara
    mask = cv2.medianBlur(mask, 7)
    
    # Encontrar los contornos en la máscara
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Ordenar los contornos por área y tomar el más grande
    contour = sorted(contours, key=cv2.contourArea, reverse=True)[0]
    
    # Aproximar el contorno a una forma geométrica
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
        
    # Inicializar las variables shape y code
    shape = None
    code = None
    
    # Asignar valores a shape y code según la forma geométrica detectada
    if len(approx) == 3:
        shape = "Triangle"
        code = '0'
    elif len(approx) == 4:
            shape = "Square"
            code = '1'
    elif len(approx) > 4:
        # Calcular la relación entre el área del contorno y el área del círculo que lo circunscribe
        area = cv2.contourArea(contour)
        (x, y), radius = cv2.minEnclosingCircle(contour)
        circle_area = np.pi * (radius ** 2)
        circle_ratio = area / circle_area
        
        # Verificar si la relación entre el área del contorno y el área del círculo es cercana a 1
        if 0.7 <= circle_ratio <= 1.3:
            shape = "Circle"
            code = '2'
    # Dibujar formas geométricas correspondientes
    if shape == "Triangle":
        # Dibujar triángulo
        cv2.drawContours(frame, [approx], -1, (0, 255, 0), 2)
    elif shape == "Square":
        # Obtener el rectángulo delimitador mínimo que ajusta al contorno
        rotated_rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rotated_rect)
        box = np.int0(box)
            
        # Dibujar rectángulo rotado
        cv2.drawContours(frame, [box], 0, (0, 255, 0), 2)
    elif shape == "Circle":
        # Obtener el centro y el radio del círculo
        (x, y), radius = cv2.minEnclosingCircle(approx)
        center = (int(x), int(y))
        radius = int(radius)
        # Dibujar círculo
        cv2.circle(frame, center, radius, (0, 255, 0), 2)
    M = cv2.moments(contour)
    if M["m00"] != 0:
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        cv2.putText(frame, shape, (cX, cY), cv2.FONT_HERSHEY_SIMPLEX,0.5, (255, 255, 255), 2)

    return code, frame

def size_detector(frame, pixels_per_cm, large_size_threshold, medium_size_threshold):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    servo_code = None
    _, _, mask = color_detector(frame, draw=False)
    
    if mask is None:
        edged = cv2.Canny(blurred, 50, 100)
    else:
        edged = cv2.bitwise_and(blurred, blurred, mask=mask)
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    shape_area_threshold = 150
    
    if contours:
        c = max(contours, key=cv2.contourArea)
        
        if cv2.contourArea(c) > shape_area_threshold:
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
            
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            
            shape = None
            
            if len(approx) == 3:
                shape = "Triangle"
            elif len(approx) == 4:
                shape = "Square"
            elif len(approx) > 4:
                area = cv2.contourArea(c)
                (x, y), radius = cv2.minEnclosingCircle(c)
                circle_area = np.pi * (radius ** 2)
                circle_ratio = area / circle_area
                
                if 0.7 <= circle_ratio <= 1.3:
                    shape = "Circle"
            
            (x, y, w, h) = cv2.boundingRect(c)
            
            if shape == "Circle":
                diameter = w / pixels_per_cm
                if diameter >= large_size_threshold:
                    size_text = "Large. D = {:.1f} cm".format(diameter)
                    servo_code = '2'
                elif diameter >= 0.9*medium_size_threshold:
                    size_text = "Medium. D = {:.1f} cm".format(diameter)
                    servo_code = '1'
                else:
                    size_text = "Small. D = {:.1f} cm".format(diameter)
                    servo_code = '0'
    
                cv2.putText(frame, size_text, (cX - 20, cY - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
            elif shape == "Triangle":
                side = w / pixels_per_cm
                if side >= large_size_threshold:
                    size_text = "Large. l = {:.1f} cm".format(side)
                    servo_code = '2'
                elif side >= medium_size_threshold:
                    size_text = "Medium. l = {:.1f} cm".format(side)
                    servo_code = '1'
                else:
                    size_text = "Small. l = {:.1f} cm".format(side)
                    servo_code = '0'
                cv2.putText(frame, size_text, (cX - 20, cY - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            else:
                width = w / pixels_per_cm
                height = h / pixels_per_cm
                if width >= large_size_threshold and height >= large_size_threshold:
                    size_text = "Large: {:.1f} cm x {:.1f} cm".format(width, height)
                    servo_code = '2'
                elif width >= medium_size_threshold and height >= medium_size_threshold:
                    servo_code = '1'
                    size_text = "Medium: {:.1f} cm x {:.1f} cm".format(width, height)
                else:
                    size_text = "Small: {:.1f} cm x {:.1f} cm".format(width, height)
                    servo_code = '0'
                cv2.putText(frame, size_text, (cX - 20, cY - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    return servo_code, frame

def calibrate_camera(frame, circle_diameter):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, _, mask = color_detector(frame, draw=False)
    
    if mask is None:
        edged = cv2.Canny(blurred, 50, 100)
    else:
        edged = cv2.bitwise_and(blurred, blurred, mask=mask)
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    shape_area_threshold = 150
    
    if contours:
        c = max(contours, key=cv2.contourArea)
        
        if cv2.contourArea(c) > shape_area_threshold:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            
            shape = None
            
            if len(approx) == 3:
                shape = "Triangle"
            elif len(approx) == 4:
                shape = "Square"
            elif len(approx) > 4:
                area = cv2.contourArea(c)
                (_, _), radius = cv2.minEnclosingCircle(c)
                circle_area = np.pi * (radius ** 2)
                circle_ratio = area / circle_area
                
                if 0.7 <= circle_ratio <= 1.3:
                    shape = "Circle"
            
            if shape == "Circle":
                (_, _, w, _) = cv2.boundingRect(c)
                
                if w != 0:
                    pixels_per_cm = w / circle_diameter
                    return pixels_per_cm
    
    return None

def classifier_selector(frame,option="color",circle_diameter=4.0, large_size_threshold=4.0,medium_size_threshold=3.0):
    if option == "color":
        return color_detector(frame)
    elif option == "shape":
        return shape_detector(frame)
    elif option == "size":
        pixels_per_cm = calibrate_camera(frame, circle_diameter)
        if pixels_per_cm is None:
             return None, None
        else:
            return size_detector(frame,pixels_per_cm,large_size_threshold,medium_size_threshold)

# FUNCIONES DE LA INTERFAZ
def moving_average(values, window_size):
    return np.convolve(values, np.ones(window_size)/window_size, mode='valid')

def update_led(LED,obstacle_sensor_state_value):
    if obstacle_sensor_state_value == 1:
        # LED encendido
        LED.create_oval(5, 5, 35, 35, fill='#ff0000', outline='#ff0000')
        LED.create_oval(4, 4, 36, 36, outline='#ff3333', width=1)
        LED.create_oval(3, 3, 37, 37, outline='#ff6666', width=1)
        LED.create_oval(2, 2, 38, 38, outline='#ff9999', width=1)
        LED.create_oval(1, 1, 39, 39, outline='#ffcccc', width=1)
        LED.create_oval(0, 0, 40, 40, outline='#ffffff', width=1)
    else:
        # LED apagado
        LED.create_oval(5, 5, 35, 35, fill='#555555', outline='#555555')
        LED.create_oval(4, 4, 36, 36, outline='#666666', width=1)
        LED.create_oval(3, 3, 37, 37, outline='#777777', width=1)
        LED.create_oval(2, 2, 38, 38, outline='#888888', width=1)
        LED.create_oval(1, 1, 39, 39, outline='#999999', width=1)

def get_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if "Arduino" in port.description:
            return str(port.device)
    return None
