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

    # Devolver la imagen final
    return servo_code, frame
