import serial
import time
import sys
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()

def unlock():
    port = '/dev/serial0'
    pin = os.getenv("SIM_PIN")
    if not pin:
        print("❌ SIM PIN nicht in .env gefunden!")
        return False
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        # Check if already ready
        ser.write(b'AT+CPIN?\r\n')
        time.sleep(1)
        res = ser.read_all().decode()
        if 'READY' in res:
            print('SIM already unlocked.')
            return True
        
        # Try unlock
        print(f'Unlocking with PIN {pin}...')
        ser.write(f'AT+CPIN="{pin}"\r\n'.encode())
        time.sleep(2)
        res = ser.read_all().decode()
        if 'OK' in res or 'READY' in res:
            print('SIM unlocked successfully.')
            return True
        else:
            print(f'Unlock failed: {res}')
            return False
    except Exception as e:
        print(f'Error: {e}')
        return False

if __name__ == '__main__':
    unlock()
