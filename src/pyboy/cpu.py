from dataclasses import dataclass
from typing import Optional

from pyboy.opcodes import check_interrupts, execute_opcode, instruction_table
from pyboy.timer import Timer


class IdleLoopException(Exception):
    pass

class Memory:
    #_div: int
    #_div_previous: int
    #_div_divider_bit: int
    #_tima: int
    #_tma: int
    #_tack_enabled: bool
    _timer: Timer
    _ly: int
    _ly_cycles: int
 
    def _on_timer_overflow(self):
        current_if = self.read(0xFF0F)
        self.write(0xFF0F, current_if | 0x4)

    def __init__(self, logger, rom_data: bytes):
        self._logger = logger
        self._rom_data = list(rom_data)
        self._ram = [0] * 0x2000
        self._vram = bytearray(0x2000)
        self._hram = [0x0] * 0x7F
        self._iohram = bytearray(0x100)
        self._external_ram = bytearray(0x2000)  # 8 KB
        self._oam = [0] * 0xA0 
        self._timer = Timer(self._on_timer_overflow)
        self._interrupt_enable = 0x00
        self._ly = 0
        self._ly_cycles = 0
        self._lcdc = 0
        self._stat = 0
        #self._div = 0
        #self._div_divider_bit = 9
        #self._tima = 0
        #self._tma = 0
        #self._tac_enabled = False
        #self._tima_reload_pending = False



    def read(self, address: int) -> int:
        if 0x0000 <= address <= 0x7FFF:
            return self._rom_data[address]
        elif 0x8000 <= address <= 0x9FFF:
            return self._vram[address - 0x8000]
        elif 0xC000 <= address <= 0xDFFF:
            return self._ram[address - 0xC000]
        elif 0xFE00 <= address <= 0xFE9F:
            return self._oam[address - 0xFE00]
        elif 0xA000 <= address <= 0xBFFF:
            return self._external_ram[address - 0xA000]
        elif 0xFEA0 <= address <= 0xFEFF:
            return 0
        elif 0xFF00 <= address <= 0xFF7F:
            if address == 0xFF04:
                return self._timer.DIV
            elif address == 0xFF40:
                return self._lcdc
            elif address == 0xFF41:
                raise NotImplementedError()
            elif address == 0xFF00:
                return 0b11011111
            elif address == 0xFF05:
                return self._timer.TIMA
            elif address == 0xFF06:
                return self._timer.TMA
            elif address == 0xFF07:
                return self._timer.TAC
            elif address == 0xFF44:
                return self._ly
            else:
                return self._iohram[address - 0xFF00]
        elif 0xFF80 <= address <= 0xFFFE:
            return self._hram[address - 0xFF80]
        elif address == 0xFFFF:
            return self._interrupt_enable
        else:
            return 0xFF

    def write(self, address: int, value: int):
        value &= 0xFF

        #print(f'Writing {value:0X} to {address:02X}')

        if 0x8000 <= address <= 0x9FFF:
            self._vram[address - 0x8000] = value

        elif 0xFE00 <= address <= 0xFE9F:
            self._oam[address - 0xFE00] = value
        
        elif 0xA000 <= address <= 0xBFFF:
            self._external_ram[address - 0xA000] = value

        elif 0xFEA0 <= address <= 0xFEFF:
            pass

        elif 0x2000 <= address <= 0x3FFF:
            # For now, no MBC support → just ignore the write
            self._logger.debug(f"Ignored ROM bank switch: {value}")
        
        elif 0xC000 <= address <= 0xDFFF:
            self._ram[address - 0xC000] = value

        elif 0xFF00 <= address <= 0xFF7F:
            if address == 0xFF04:
                self._timer.DIV = value
            #TAC
            elif address == 0xFF07:
                self._timer.TAC = value
            elif address == 0xFF05:
                self._timer.TIMA = value
                
            elif address == 0xFF06:
                self._timer.TMA = value

            elif address == 0xFF44:
                self._ly = 0
            elif address == 0xFF40:
                self._lcdc = value

            elif address == 0xFFF00:
                raise NotImplementedError()

            elif address == 0xFF41:
                self._stat = value
            
            elif address == 0xFF0F:
                self._iohram[address - 0xFF00] = value
            else:
                self._iohram[address - 0xFF00] = value
        
        elif 0xFF80 <= address <= 0xFFFE:
            self._hram[address - 0xFF80] = value
        elif 0xE000 <= address <= 0xFDFF:
            self.write(address - 0x2000, value)
        elif address == 0xFFFF:
            self._interrupt_enable = value
        #elif 0xFEA0 <= address <= 0xFEFF:
        #    pass  # Ignore writes
        elif 0x0000 <= address <= 0x7FFF:
            pass
        else:
            raise Exception(f'Writing {value} to to an unknown memory area (address {address:02X})!')

    def add_cycles(self, count: int):
        self._ly_cycles += count
        if self._ly_cycles > 456:
            self._ly_cycles -= 456
            self._ly = (self._ly + 1) % 154

            if self._ly == 144:
                # VBlank startar vid scanline 144
                if_reg = self.read(0xFF0F)
                self.write(0xFF0F, if_reg | 0x01)  # Sätt VBlank-flagga

        self._timer.add_cycles(count)


    @property
    def DIV(self):
        return self._div

    @property
    def CYCLES(self):
        return self._ly_cycles
    


#Testa med: 0xC44D, C36D
class CPUState:
    #__slots__ = ['pc', 'sp', 'cf', 'hf', 'zf', 'nf', 'ime', '_h', '_l', '_e', '_a', '_b', '_c', '_d']
    pc: int
    _sp: int
    cf: int
    _bc: int
    _a: int
    _ie: int
    _if: int
    _b: int
    _c: int
    _h: int
    _l: int
    _d: int
    _e: int
    nf: int
    zf: int
    memory: Memory
    ime: int
    ime_pending: bool
    #_div: int
    _halted: bool


    @property
    def A(self):
        return self._a

    @A.setter
    def A(self, value: int):
        self._a = value & 0xFF

    @property
    def B(self):
        return self._b

    @B.setter
    def B(self, value: int):
        self._b = value & 0xFF

    @property
    def BC(self):
        return (self._b << 8) | self._c

    @BC.setter
    def BC(self, value: int):
        value = value & 0xFFFF
        self._b = (value >> 8) & 0xFF
        self._c = value & 0xFF


    @property
    def C(self):
        return self._c

    @C.setter
    def C(self, value: int):
        self._c = value & 0xFF

    @property
    def D(self):
        return self._d

    @D.setter
    def D(self, value: int):
        self._d = value & 0xFF

    @property
    def E(self):
        return self._e

    @E.setter
    def E(self, value: int):
        self._e = value & 0xFF

    @property
    def DE(self):
        return (self._d << 8) | self._e

    @DE.setter
    def DE(self, value: int):
        value = value & 0xFFFF
        self._d = (value >> 8) & 0xFF
        self._e = value & 0xFF
    
    @property
    def HL(self):
        return (self._h << 8) | self._l

    @HL.setter
    def HL(self, value: int):
        value = value & 0xFFFF
        self._h = (value >> 8) & 0xFF
        self._l = value & 0xFF

    @property
    def H(self):
        return self._h

    @H.setter
    def H(self, value):
        self._h = value & 0xFF

    @property
    def L(self):
        return self._l

    @L.setter
    def L(self, value: int):
        self._l = value & 0xFF

    @property
    def SP(self):
        return self._sp

    @SP.setter
    def SP(self, value):
        self._sp = value

    def __init__(self):
        self.pc = 0
        self._sp = 0
        self.cf = 0
        self.hf = 0
        self._h = 0
        self._l = 0
        self._a = 0
        self._b = 0
        self._c = 0
        self._d = 0
        self._e = 0
        self.nf = 0
        self.zf = 0
        self.ime = 0
        self._ly = 0
        self._ly_cycles = 0
        self.new_cycles = 0

        self.DE= 0xFF56
        self.HL =0x000D
        self._sp = 0xFFFE
        self._a = 0x11
        self.zf = 1
        self.enable_interrupts_after_next_instruction = False
        self._delay_enable_ime = False
        #self.div = 0
        self._halted = False

    def get_flags_byte(self):
        flags = 0
        if self.zf:
            flags |= 1 << 7
        if self.nf:
            flags |= 1 << 6
        if self.hf:
            flags |= 1 << 5
        if self.cf:
            flags |= 1 << 4

        return flags & 0xF0

    def set_flags_from_byte(self, flags):
        self.zf = (flags >> 7) & 1
        self.nf = (flags >> 6) & 1
        self.hf = (flags >> 5) & 1
        self.cf = (flags >> 4) & 1


class CPU:
    def __init__(self, logger, state: Optional[CPUState] = None, debug: bool=False):
        self._logger = logger
        self._previous_pc = 0
        self._previous_pc_count = 0
        self._debug = debug
        self._steps = 0

        if state is not None:
            raise NotImplementedError("Loading of state is not implemented!")

        self._state = CPUState()

    def set_addresses(self, pc: int = 0x0100, sp: int = 0xFFFE):
        self._state.pc = pc
        self._state._sp = sp

    def load_program(self, data: bytes, address: int = 0):
        self._state.memory = Memory(self._logger, data)

    def run_next_instruction(self):
        instruction = self._get_next_instruction()
        cycles = execute_opcode(self, self._logger, instruction)
        return cycles

    def run_n_cycles(self, number: int = 1):
        cycles_run = 0
        while cycles_run < number:
            ei = self._state.ime
            
            #TODO: Protect against HLT bug?
            if self._state._halted:
                check_interrupts(self._logger, self)
                if self._state._halted:
                    cycle_count = 4
                    self._state.memory.add_cycles(4)
                    cycles_run += 4
                    continue
            else:
                instruction = self._get_next_instruction()
                cycle_count = execute_opcode(self, self._logger, instruction)

            #if ei:
            #    print(f"==> IME ENABLED efter nästa instruktion @ PC={self._state.pc:04X}")
            #    self._state.enable_interrupts_after_next_instruction = False
            #    self._state.ime = True
            if self._state._delay_enable_ime:
                self._logger.info(f'{self._state.pc} - ime: delay_enable_ime is set to True')
                self._state._delay_enable_ime = False
                self._state.enable_interrupts_after_next_instruction = True
            elif self._state.enable_interrupts_after_next_instruction:
                self._logger.info(f'{self._state.pc} - ime: enable_interrupts_after_next_instruction is set to True')
                self._state.enable_interrupts_after_next_instruction = False
                self._state.ime = True


            for _ in range(cycle_count):
                self._state.memory.add_cycles(1)
            #self._state.memory.add_cycles(cycle_count)
            #self._logger.info(f'Cycles at {self._state.memory.CYCLES!')
            cycles_run += cycle_count
            
            check_interrupts(self._logger, self)

    def _get_next_instruction(self):
        self._steps += 1
        instruction = []
        remaining_operand_count = 0

        while len(instruction) == 0 or remaining_operand_count > 0:
            b = self._state.memory.read(self._state.pc)

            #self._logger.debug(
            #    f"{hex(self._state.pc)}: {self._state.memory.read(self._state.pc):02X}"
            #)
            if not instruction:
                if self._debug:
                    if self._previous_pc != self._state.pc:
                        self._previous_pc = self._state.pc
                        self._previous_pc_count = 0
                    else:
                        self._previous_pc_count += 1

                    if self._previous_pc_count > 10:
                        raise IdleLoopException('Code is jumping to the same address, probably end of program!')

                # Handle CB prefix instructions
                if b == 0xCB:
                    instruction.append(0xCB)
                    self._state.pc += 1
                    instruction.append(self._state.memory.read(self._state.pc))
                    self._state.pc += 1
                    return instruction
                else:
                    #print(f'PC: 0x{self._state.pc:02X}')
                    if b not in instruction_table:
                        raise Exception(f"Unsupported instruction {b:0X}")
                instruction.append(b)
                remaining_operand_count = instruction_table[b].operand_count
            else:
                instruction.append(b)
                remaining_operand_count -= 1

            self._state.pc += 1
        return instruction
