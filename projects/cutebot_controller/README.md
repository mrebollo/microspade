# Plan de Integración: Control de Elecfreaks Cutebot con Microspade

Este proyecto tiene como objetivo utilizar el framework multiagente `microspade` para controlar un coche inteligente **Elecfreaks Cutebot** de forma autónoma empleando una arquitectura basada en agentes (BDI).

---

## 1. Arquitectura de Control con Agentes

Para evitar acoplamiento de código y mantener una arquitectura limpia, dividimos el coche en tres capas de comportamientos concurrentes que se comunican mediante la base de conocimientos (`KB`) del agente:

```text
    +------------------------------------------+
    |            Entrada (Sensores)            |
    |          SensorReader - Periodic         |
    +--------------------+---------------------+
                         |
                         v (set_kb)
    +--------------------+---------------------+
    |           Knowledge Base (KB)            |
    +--------------------+---------------------+
                         |
                         +-----------------------------+
                         |                             |
                         v (get_kb)                    v (get_kb)
    +--------------------+---------------------+ +-----+---------------------+
    |        Cerebro: AvoidObstacles           | |         Cerebro: FollowLine         |
    |            Cyclic (yield)                | |           Cyclic (yield)            |
    +--------------------+---------------------+ +-----+---------------------+
                         |                             |
                         +--------------+--------------+
                                        |
                                        v (set_kb: target_speed)
    +-----------------------------------+------+
    |           Knowledge Base (KB)            |
    +-----------------------------------+------+
                                        |
                                        v (get_kb)
    +-----------------------------------+------+
    |            Salida (Actuadores)           |
    |          MotorActuator - Periodic        |
    +--------------------+---------------------+
                         |
                         v (Escritura I2C)
             [ Motores Cutebot Reales ]
```

* **Capa de Entrada (`SensorReader`):** Lee periódicamente los pines físicos del hardware (sonar y巡线/line tracker) y actualiza la KB del agente (`distance` y `line`).
* **Capa de Decisión (`AvoidObstacles` / `FollowLine`):** Comportamientos cíclicos que leen de la KB los sensores, calculan las velocidades ideales para cada rueda y las guardan en la KB (`left_speed` y `right_speed`). Usan la nueva sintaxis `yield` para cooperar y no colgar la CPU.
* **Capa de Salida (`MotorActuator`):** Comportamiento periódico de alta prioridad que lee las velocidades objetivo de la KB y las escribe mediante I2C a la placa controladora de motores del Cutebot.

---

## 2. Detalles Técnicos de Hardware (Cutebot)

El Cutebot se comunica mediante el bus I2C estándar del micro:bit y pines GPIO específicos:

### A. Motores (Dirección por I2C)
* **Dirección I2C del Cutebot:** `0x10` (decimal `16`).
* **Protocolo de escritura de motores:**
  Enviamos un búfer de 4 bytes por el bus I2C para cada rueda:
  `[motor_id, direccion, velocidad, 0]`
  
  * **`motor_id`**: `0x01` (Rueda Izquierda), `0x02` (Rueda Derecha).
  * **`direccion`**: `0x02` (Hacia adelante), `0x01` (Hacia atrás).
  * **`velocidad`**: `0` a `100` (entero).
  
  *Código de ejemplo I2C:*
  ```python
  # Rueda izquierda adelante a velocidad 50
  i2c.write(0x10, bytearray([0x01, 0x02, 50, 0]))
  ```

### B. Sensor de Ultrasonidos (Sonar)
* **Pin Trigger (Pulsador):** `pin8`
* **Pin Echo (Receptor):** `pin12`
* **Cálculo de Distancia (MicroPython):**
  ```python
  pin12.read_digital() # Reset
  pin8.write_digital(1)
  sleep_us(10)
  pin8.write_digital(0)
  duration = time_pulse_us(pin12, 1, 25000)
  distance_cm = round(duration * 34 / 2 / 1000)
  ```

### C. Sensor de Líneas (Infrarrojos)
* **Pin Izquierdo:** `pin13`
* **Pin Derecho:** `pin14`
* Ambos sensores deben configurarse con resistencia de pull-up (`PULL_UP`).
* **Estados devueltos (`read_digital()`):**
  * `0`: Sensor detecta superficie reflectante (blanca).
  * `1`: Sensor detecta superficie absorbente (negra).

---

## 3. Plan de Implementación (Hitos)

* [ ] **Hito 1: Carga y verificación de la librería `microspade`**
  Subir el archivo compilado `dist/microspade.py` al sistema de archivos del micro:bit del coche.
* [ ] **Hito 2: Implementación de la Capa de Entrada (`SensorReader`)**
  Escribir el código para tomar la distancia del sonar y el estado de la línea infrarroja, almacenándolos en la KB.
* [ ] **Hito 3: Implementación de la Capa de Salida (`MotorActuator`)**
  Escribir el Driver I2C para encender y parar motores según variables `left_speed` y `right_speed`. Validar en modo suspendido (coche apoyado en alto).
* [ ] **Hito 4: Lógica de Evitación de Obstáculos (`AvoidObstacles`)**
  Desarrollar el comportamiento usando la concurrencia basada en `yield`. Si `distance < 20` cm, frenar y girar hasta liberar camino.
* [ ] **Hito 5: Lógica de Sigue-líneas (`FollowLine`)**
  Implementar el control proporcional utilizando las lecturas del line tracker.
* [ ] **Hito 6 (Opcional): Control Remoto por Radio**
  Implementar un agente en un segundo micro:bit que actúe de mando y envíe mensajes de telecontrol (`Message(to="cutebot", body="...")`) usando el transceptor de radio de `microspade`.
