#from pyboy.emulator import Emulator
#from pyboy.cpu import CPU
import argparse

from pyboy.cpu import CPU
from pyboy.emulator import Emulator

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--rom-file', required=False, default='rtc3test.gb')
    parser.add_argument('-d', '--debug', required=False, action='store_true')

    arguments = parser.parse_args()

    """cpu = CPU(logger)
    
    rom_data = open(sys.argv[1], 'rb').read()
    cpu.load_program(rom_data)
    cpu.run_n_instructions(20000000)

    print(f'MBC Type: {rom_data[0x147]:0X}')"""
    if not arguments.debug:
        import os
        os.environ["LOGURU_LEVEL"] = 'INFO'

    from loguru import logger


    emulator = Emulator(logger, arguments.debug)
    emulator.load_rom_file(arguments.rom_file)
    emulator.run()

    """
    instruction_operand_count = {0x00: 0x0, 0xC3: 2, 0x21: 2, 0x47: 0, 0x11: 2, 0x0E: 1, 0x12:0, 0x1C: 0, 0x20: 1, 0x2A: 0, 0x14: 0}

    memory = [0] * 65536
    for d in range(len(rom_data)):
        memory[d] = rom_data[d]
    
    instruction = []
    remaining_operand_count = 0

    i = 0
    pc = 0x0100
    hl = 0
    hf = 0
    a = 0
    b = 0
    de = 0
    c = 0
    e = 0
    zf = 0
    d = 0
    while True:
        if i > 500000:
            break

        if instruction and remaining_operand_count == 0:
            #print(f'HO Got complete instruction: {instruction}')
            
            if instruction[0] == 0xC3:
                address = instruction[1] | (instruction[2] << 8)
                #print(f'Received address {address:02x}')

                #print(f'Setting PC to {address:02X}')
                pc = address
                instruction = []
                continue
            elif instruction[0] == 0x21:
                hl = instruction[1] | (instruction[2] << 8)
            elif instruction[0] == 0x47:
                b = a
                print('LD B, A')
                instruction = []
            elif instruction[0] == 0x11:
                value = instruction[1] | (instruction[2] << 8)
                de = value
                instruction = []
            elif instruction[0] == 0x0E:
                value = instruction[1]
                c = value
                instruction = []
            elif instruction[0] == 0x12:
                memory[de] = a
                instruction = []
            elif instruction[0] == 0x1C:
                e = (e + 1) &  0xFF
                zf = 1 if e == 0 else 0
                nf = 0
                hf = 1 if (e & 0x0F) == 0 else 0
                instruction = []
            elif instruction[0] == 0x20:
                value = instruction[1]
                if value & 0x80:
                    value = value - 0x100 
                
                instruction = []

                if not zf:
                    pc = pc + value
                    continue

            elif instruction[0] == 0x2A:
                a = memory[hl]
                hl = (hl + 1) & 0xFFFF
                instruction = []
            elif instruction[0] == 0x14:
                d = (d + 1) &  0xFF
                zf = 1 if d == 0 else 0
                nf = 0
                hf = 1 if (d & 0x0F) == 0 else 0

            instruction = []

        b = memory[pc]
        print(f'{hex(pc)}: {memory[pc]:02X}')
        if not instruction:
            if not b in instruction_operand_count:
                raise Exception(f'Unsupported instruction {b:0X}')
            instruction_operand_count.get(b)
            #print(f'Got instruction: {b:0X}')
            instruction.append(b)
            #print(f'{b:0X}','gris')              
            remaining_operand_count = instruction_operand_count[b]
        else:
            #print(f'Received operand {b:0X}')
            instruction.append(b)
            remaining_operand_count -= 1

        i = i + 1
        pc = pc + 1
    """