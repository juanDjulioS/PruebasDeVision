# Función para detectar la forma, se usa tanto en forma como tamaño
def detect_shape(c):
    
    servo_code = None
    
    # Inicializar el nombre de la forma y el perímetro aproximado
    shape = None
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.04 * peri, True)

    # Si el contorno tiene 3 vértices, entonces es un triángulo
    if len(approx) == 3:
        # Calcular la distancia entre dos puntos del contorno
        side = np.sqrt((approx[0][0][0] - approx[1][0][0]) ** 2 + (approx[0][0][1] - approx[1][0][1]) ** 2)
       
        # Calcular la altura esperada de un triángulo equilátero
        expected_height = np.sqrt(3) / 2 * side
        
        # Obtener la altura real del contorno
        (_, _, _, h) = cv2.boundingRect(c)
        
        # Verificar si la altura real es similar a la altura esperada
        if abs(expected_height - h) <= 0.1 * expected_height:  # Ajusta este valor según sea necesario
            shape = "Triangle"
            servo_code = '0'

    # Si el contorno tiene 4 vértices, entonces es un cuadrado o un rectángulo
    elif len(approx) == 4:
        shape = "Square"
        servo_code = '1'

    # Si el contorno es un círculo
    else:
        (_, _, w, h) = cv2.boundingRect(c)
        if abs(w - h) <= 0.1 * w:  # Ajusta este valor según sea necesario
            shape = "Circle"
            servo_code = '2'

    # Devolver el nombre de la forma
    return servo_code, shape
