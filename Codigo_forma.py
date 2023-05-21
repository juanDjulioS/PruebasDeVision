import cv2
import numpy as np

# Cargar la imagen desde la cámara web
cap = cv2.VideoCapture(0)

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
        # Calcular el bounding box del contorno y usar el bounding box para calcular la relación de aspecto
        (x, y, w, h) = cv2.boundingRect(approx)
        ar = w / float(h)

        # Un cuadrado tendrá una relación de aspecto aproximadamente igual a uno, de lo contrario, el contorno es un rectángulo
        shape = "Square" if ar >= 0.95 and ar <= 1.05 else "Rectangle"

    # Si el contorno es un círculo
    else:
        shape = "Circle"

    # Devolver el nombre de la forma
    return shape

while True:
    # Capturar un nuevo frame
    ret, frame = cap.read()

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
                shape = detect_shape(c)
                cv2.drawContours(frame, [c], -1, (0, 255, 0), 2)
                cv2.putText(frame, shape, (cX - 20 , cY - 20),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Mostrar la imagen final
    cv2.imshow('frame',frame)

    # Verificar si el usuario presionó la tecla 'q' para salir
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
