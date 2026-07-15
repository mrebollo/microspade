#!/usr/bin/env python3
"""
flash_all.py — Flashea el proyecto de dist/ a todas las micro:bit detectadas.
Controla el retardo de arranque tras el reset físico para garantizar
una conexión robusta libre de bloqueos.
"""

import os
import sys
import time
import glob
import serial

DIST_DIR = "dist"
MICROSPADE_DIST_DIR = os.path.join(DIST_DIR, "microspade")
BAUD_RATE = 115200

# Código de limpieza para borrar todos los archivos viejos de la placa
CLEANUP_CODE = """
import os
def rm_rf(p):
    try:
        if os.stat(p)[0] & 0x4000:
            for f in os.listdir(p): rm_rf(p + '/' + f)
            os.rmdir(p)
        else: os.remove(p)
    except: pass
for f in os.listdir(): rm_rf(f)
"""

def get_ports():
    """Detecta los puertos serie de micro:bit en macOS."""
    return glob.glob("/dev/cu.usbmodem*")

def send_raw_code(ser, code):
    """Envía código Python al Raw REPL y devuelve la salida (stdout, stderr)."""
    # Enviar código seguido de Ctrl-D para ejecutar
    ser.write(code.encode("utf-8") + b"\x04")
    
    # El dispositivo responde con "OK" inmediatamente, luego ejecuta y devuelve la salida
    # con formato: OK\x04<stdout>\x04<stderr>\x04>
    response = ser.read_until(b"\x04>")
    if not response.startswith(b"OK"):
        raise IOError(f"El dispositivo no aceptó el comando. Respuesta: {response}")
    
    # Separar stdout y stderr
    content = response[2:-2] # Eliminar OK y \x04>
    parts = content.split(b"\x04", 1)
    stdout = parts[0]
    stderr = parts[1] if len(parts) > 1 else b""
    
    if stderr:
        raise RuntimeError(stderr.decode("utf-8").strip())
    
    return stdout

def flash_device(port, files_to_upload):
    """Establece conexión robusta y flashea una placa."""
    print(f"\nConectando a {port}...")
    
    # 1. Abrir puerto. Esto provocará un reset físico DTR/RTS en la placa
    ser = serial.Serial(port, BAUD_RATE, timeout=2)
    ser.dtr = True
    ser.rts = True
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    # 2. Inundar el puerto con Ctrl-C durante 2 segundos mientras la placa arranca
    print("Inundando el puerto con Ctrl-C para interrumpir el arranque antes de main.py...")
    start_time = time.time()
    while time.time() - start_time < 2.0:
        ser.write(b"\r\x03")
        ser.flush() # Forzar a macOS a transmitir el byte inmediatamente
        time.sleep(0.02) # Enviar cada 20ms para no desbordar
        
    # Limpiar buffer de entrada de mensajes de bienvenida / logs
    ser.reset_input_buffer()
    
    # 4. Entrar en modo Raw REPL enviando Ctrl-A
    print("Entrando en modo Raw REPL...")
    ser.write(b"\r\x01")
    raw_repl_msg = b"raw REPL; CTRL-B to exit\r\n>"
    response = ser.read_until(raw_repl_msg)
    
    if not response.endswith(raw_repl_msg):
        # Intentar una vez más
        ser.write(b"\r\x01")
        response = ser.read_until(raw_repl_msg)
        if not response.endswith(raw_repl_msg):
            print(f"DEBUG: Última respuesta leída del puerto: {repr(response)}")
            ser.close()
            raise IOError("No se pudo establecer conexión con el Raw REPL de la placa.")
            
    print("¡Conectado con éxito al Raw REPL!")
    
    # 5. Ejecutar limpieza de archivos antiguos
    print("Limpiando archivos antiguos de la placa...")
    send_raw_code(ser, CLEANUP_CODE)
    
    # 6. Subir archivos
    for local_path, remote_name in files_to_upload:
        print(f"Subiendo {remote_name}...")
        with open(local_path, "rb") as f:
            content = f.read()
            
        # Abrir archivo en la placa
        send_raw_code(ser, f"fd = open({repr(remote_name)}, 'wb')")
        
        # Escribir en bloques de 256 bytes para evitar desbordar el buffer de entrada serie
        chunk_size = 256
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            send_raw_code(ser, f"fd.write({repr(chunk)})")
            
        # Cerrar archivo
        send_raw_code(ser, "fd.close()")
        
    # 7. Reiniciar la placa para arrancar el nuevo código
    print("Reiniciando placa (Soft Reset)...")
    ser.write(b"\x04") # Ctrl-D (Soft Reset)
    ser.read_until(b"soft reboot\r\n")
    time.sleep(0.2)
    
    # Salir de modo Raw REPL para que la ejecución del REPL estándar y main.py continúe normal
    ser.write(b"\x02") # Ctrl-B
    
    ser.close()
    print(f"¡Placa {port} flasheada y ejecutando main.py correctamente!")

def main():
    if not os.path.exists(DIST_DIR) or not os.path.exists(os.path.join(DIST_DIR, "main.py")):
        print("Error: No se encontró la carpeta 'dist/' con los archivos compilados.")
        print("Por favor, ejecuta primero build_module.py. Ejemplo:")
        print("   uv run tools/build_module.py examples/counter_agent.py")
        sys.exit(1)
        
    ports = get_ports()
    if not ports:
        print("Error: No se detectó ninguna micro:bit conectada en /dev/cu.usbmodem*")
        sys.exit(1)
        
    print(f"Encontradas {len(ports)} placa(s) en: {', '.join(ports)}")
    
    # Recopilar archivos a subir
    files_to_upload = []
    
    # Leer dependencias
    deps_file = os.path.join(DIST_DIR, "dependencies.txt")
    if os.path.exists(deps_file):
        with open(deps_file, "r") as f:
            for line in f:
                filename = line.strip()
                if filename:
                    local_path = os.path.join(MICROSPADE_DIST_DIR, filename)
                    if os.path.exists(local_path):
                        files_to_upload.append((local_path, filename))
                        
    # Añadir main.py
    main_py = os.path.join(DIST_DIR, "main.py")
    files_to_upload.append((main_py, "main.py"))
    
    # Flashear cada placa secuencialmente
    for port in ports:
        try:
            flash_device(port, files_to_upload)
        except Exception as e:
            print(f"Error al flashear la placa en {port}: {e}")
            sys.exit(1)
            
    print("\n¡Proceso completado con éxito para todas las placas!")

if __name__ == "__main__":
    main()
