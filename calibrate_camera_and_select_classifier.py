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

def classifier_selector(frame,option,circle_diameter, large_size_threshold,medium_size_threshold):
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
