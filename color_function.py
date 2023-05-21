def color_detector(frame):

    # Definir los rangos de colores en HSV
    red_lower = np.array([0, 120, 70])
    red_upper = np.array([10, 255, 255])
    blue_lower = np.array([100, 150, 0])
    blue_upper = np.array([140, 255, 255])
    green_lower = np.array([36, 25, 25])
    green_upper = np.array([70, 255,255])

    # Convertir la imagen a HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Crear máscaras para cada color
    mask_red = cv2.inRange(hsv, red_lower, red_upper)
    mask_blue = cv2.inRange(hsv, blue_lower, blue_upper)
    mask_green = cv2.inRange(hsv, green_lower, green_upper)

    # Aplicar una operación de apertura a las máscaras para eliminar pequeños grupos de píxeles falsos positivos
    kernel = np.ones((5,5),np.uint8)
    mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, kernel)
    mask_blue = cv2.morphologyEx(mask_blue, cv2.MORPH_OPEN, kernel)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)

    # Contar el número de píxeles de cada color
    red_count = cv2.countNonZero(mask_red)
    blue_count = cv2.countNonZero(mask_blue)
    green_count = cv2.countNonZero(mask_green)

    # Determinar el color dominante
    if red_count > blue_count and red_count > green_count:
        color = "red"
        color_code = (0, 0, 255)
    elif blue_count > red_count and blue_count > green_count:
        color = "blue"
        color_code = (255, 0, 0)
    else:
        color = "green"
        color_code = (0, 255, 0)

    # Crear una máscara para todos los colores
    mask = cv2.bitwise_or(mask_red, mask_blue)
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
    return frame
