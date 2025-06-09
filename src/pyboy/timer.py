from typing import Callable


class Timer:
    _tac_enabled: bool
    _div_counter: int
    _tma: int
    _tima: int
    _tac_div_bit: int
    _tac: int

    @property
    def TIMA(self):
        return self._tima
    
    @TIMA.setter
    def TIMA(self, value: int):
        self._tima = value

    @property
    def TMA(self):
        return self._tma
    
    @TMA.setter
    def TMA(self, value: int):
        self._tma = value

    @property
    def DIV(self):
        return self._div_counter >> 8

    @DIV.setter
    def DIV(self, _):
        self._div_counter = 0

    @property
    def TAC(self):
        return self._tac

    @TAC.setter
    def TAC(self, value: int):
        self._tac = value
        self._tac_enabled = (value & 0x4) != 0

        match (value & 0x3):
            case 0:
                self._tac_div_bit = 9
            case 1:
                self._tac_div_bit = 3
            case 2:
                self._tac_div_bit = 5
            case 3:
                self._tac_div_bit = 7

    def add_cycles(self, count: int):
        for _ in range(count):
            new_div_counter = (self._div_counter + 1) & 0xFFFF


            if self._tac_enabled:
                old_bit = (self._div_counter >> self._tac_div_bit) & 1
                new_bit = (new_div_counter >> self._tac_div_bit) & 1

                if old_bit == 1 and new_bit == 0:
                    self._tima += 1
                    # OVERFLOW
                    if self._tima > 0xFF:
                        self._tima = self._tma
                        self._overflow_callback()

            self._div_counter = new_div_counter

    def __init__(self, overflow_callback: Callable):
        self._tac_enabled = False
        self._tac = 0
        self._tima = 0
        self._tma = 0
        self._div_counter = 0
        self._overflow_callback = overflow_callback

