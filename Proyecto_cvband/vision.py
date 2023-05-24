import cv2
import numpy as np
      
           
# FUNCIONES DE CLASIFICACIÓN DE VISION
def color_detector(frame):

    servo_code = None
    # Definir los rangos de colores en HSV
    red_lower = np.array([0, 120, 70])
    red_upper = np.array([10, 255, 255])
    yellow_lower = np.array([20, 100, 100])
    yellow_upper = np.array([30, 255, 255])
    green_lower = np.array([36, 25, 25])
    green_upper = np.array([70, 255,255])

    # Convertir la imagen a HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Crear máscaras para cada color
    mask_red = cv2.inRange(hsv, red_lower, red_upper)
    mask_yellow = cv2.inRange(hsv, yellow_lower, yellow_upper)
    mask_green = cv2.inRange(hsv, green_lower, green_upper)

    # Aplicar una operación de apertura a las máscaras para eliminar pequeños grupos de píxeles falsos positivos
    kernel = np.ones((5,5),np.uint8)
    mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, kernel)
    mask_yellow = cv2.morphologyEx(mask_yellow, cv2.MORPH_OPEN, kernel)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)

    # Contar el número de píxeles de cada color
    red_count = cv2.countNonZero(mask_red)
    yellow_count = cv2.countNonZero(mask_yellow)
    green_count = cv2.countNonZero(mask_green)

    # Determinar el color dominante
    if red_count > yellow_count and red_count > green_count:
        color = "red"
        color_code = (0, 0, 255)
        servo_code = '0'
    elif yellow_count > red_count and yellow_count > green_count:
        color = "yellow"
        color_code = (0, 255, 255)
        servo_code = '1'
    else:
        color = "green"
        color_code = (0, 255, 0)
        servo_code = '2'

    # Crear una máscara para todos los colores
    mask = cv2.bitwise_or(mask_red, mask_yellow)
    mask = cv2.bitwise_or(mask, mask_green)

    # Aplicar una operación de apertura a la máscara para eliminar pequeños grupos de píxeles blancos
    kernel = np.ones((5,5),np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    # Encontrar los contornos en la máscara
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Definir el valor umbral para el área del contorno
    color_area_threshold = 250

    # Dibujar un recuadro alrededor de cada contorno cuya área sea mayor que el umbral
    for c in contours:
        if cv2.contourArea(c) > color_area_threshold:
            x,y,w,h = cv2.boundingRect(c)
            cv2.rectangle(frame,(x,y),(x+w,y+h),color_code,2)

    # Mostrar el nombre del color en la esquina superior derecha
    cv2.putText(frame,color,(frame.shape[1]-100,50),cv2.FONT_HERSHEY_SIMPLEX,1,color_code,2,cv2.LINE_AA)

    # Devolver la imagen final
    return servo_code, frame

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
        shape = "Square"
        servo_code = '1'

    # Si el contorno es un círculo
    else:
        shape = "Circle"
        servo_code = '2'

    # Devolver el nombre de la forma
    return servo_code, shape

def shape_detector(frame):
    
    servo_code = None
    
    # Convertir la imagen a escala de grises y aplicar un desenfoque para suavizarla
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Realizar una detección de bordes y encontrar los contornos en la imagen
    edged = cv2.Canny(blurred, 50, 100)
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    
    # Definir el valor umbral para el área del contorno
    shape_area_threshold = 150
    
    # Recorrer cada contorno
    for c in contours:
            # Verificar si el contorno es cerrado
        if cv2.contourArea(c) > shape_area_threshold:
            # Calcular el centro del contorno y dibujar un círculo en el centro
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                servo_code, shape = detect_shape(c)
                cv2.drawContours(frame, [c], -1, (0, 255, 0), 2)
                cv2.putText(frame, shape, (cX - 20 , cY - 20),cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255, 255, 255), 2)

    # Devuelve la imagen final
    return servo_code, frame

def size_detector(frame, pixels_per_cm, large_size_threshold, medium_size_threshold):
    
    servo_code = None
    
    # Convertir la imagen a escala de grises y aplicar un desenfoque para suavizarla
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Realizar una detección de bordes y encontrar los contornos en la imagen
    edged = cv2.Canny(blurred, 50, 100)
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    
    # Definir el valor umbral para el área del contorno
    shape_area_threshold = 150
    
    # Recorrer cada contorno
    for c in contours:
            # Verificar si el contorno es cerrado
        if cv2.contourArea(c) > shape_area_threshold:
            # Calcular el centro del contorno y dibujar un círculo en el centro
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                _, shape = detect_shape(c)
                cv2.drawContours(frame, [c], -1, (0, 255, 0), 2)
                (x, y, w, h) = cv2.boundingRect(c)
                
                if shape =="Circle":
                    diameter = w / pixels_per_cm
                    if diameter >= large_size_threshold:
                        size_text = "Large. D = {:.1f} cm".format(diameter)
                        servo_code = '0'
                    elif diameter >= medium_size_threshold:
                        size_text = "Medium. D = {:.1f} cm".format(diameter)
                        servo_code = '1'
                    else:
                        size_text = "Small. D = {:.1f} cm".format(diameter)
                        servo_code = '2'
                    cv2.putText(frame,size_text,(cX - 20 , cY - 20),cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255, 255, 255), 2)
                elif shape == "Triangle":
                    side = w / pixels_per_cm
                    if side >= large_size_threshold:
                        size_text = "Large. l = {:.1f} cm".format(side)
                        servo_code = '0'
                    elif side >= medium_size_threshold:
                        size_text = "Medium. l = {:.1f} cm".format(side)
                        servo_code = '1'
                    else:
                        size_text = "Small. l = {:.1f} cm".format(side)
                        servo_code = '2'
                    cv2.putText(frame, size_text, (cX - 20 , cY - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                else:
                    width = w / pixels_per_cm
                    height = h / pixels_per_cm
                    if width >= large_size_threshold and height >= large_size_threshold:
                        size_text = "Large: {:.1f} cm x {:.1f}cm".format(width, height)
                        servo_code = '0'
                    elif width >= medium_size_threshold and height >= medium_size_threshold:
                        servo_code = '1'
                        size_text = "Medium: {:.1f}cm x {:.1f}cm".format(width, height)
                    else:
                        size_text = "Small: {:.1f} cm x {:.1f} cm".format(width, height)
                        servo_code = '2'
                    cv2.putText(frame,size_text,(cX - 20 , cY - 20),cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255, 255, 255), 2)

    # Devolver la imagen final y el codigo del servo
    return servo_code, frame

def calibrate_camera(frame, circle_diameter=4.0):
    
    # Convertir la imagen a escala de grises y aplicar un desenfoque para suavizarla
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Realizar una detección de bordes y encontrar los contornos en la imagen
    edged = cv2.Canny(blurred, 50, 100)
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    # Definir el valor umbral para el área del contorno
    shape_area_threshold = 150

    # Recorrer cada contorno
    for c in contours:
        # Verificar si el contorno es cerrado
        if cv2.contourArea(c) > shape_area_threshold:
            # Calcular el centro del contorno y dibujar un círculo en el centro
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                _, shape = detect_shape(c)
                if shape == "Circle":
                    (x, y, w, h) = cv2.boundingRect(c)
                    pixels_per_cm = w / circle_diameter
                    return pixels_per_cm

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
        