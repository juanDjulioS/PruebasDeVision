# Función para detectar la forma, se usa tanto en forma como tamaño
def detect_shape(c):
    # Inicializar el nombre de la forma y el perímetro aproximado
    shape = "unidentified"
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.04 * peri, True)

    # Si el contorno tiene 3 vértices, entonces es un triángulo
    if len(approx) == 3:
        shape = "Triangle"

    # Si el contorno tiene 4 vértices, entonces es un cuadrado o un rectángulo
    elif len(approx) == 4:
        shape = "Square" 

    # Si el contorno es un círculo
    else:
        shape = "Circle"

    # Devolver el nombre de la forma
    return shape
