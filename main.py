"""Pico main code"""
from src.picointerface import Pico

if __name__ == "__main__":
    pico = Pico()
    while True:
        op, args = pico.decode_csv()
        pico.handle_csv(op, args)
