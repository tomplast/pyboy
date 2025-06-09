def test_timer_overflow_and_interrupt():
    import logging
    from pyboy.cpu import CPU  # byt ut mot din modul

    logger = logging.getLogger()
    cpu = CPU(logger)
    cpu.load_program(bytes([0x00] * 0x8000))  # dummy ROM
    mem = cpu._state.memory

    # Aktivera timer: TAC = 0x05 (enable, 262144 Hz, divider_bit = 3)
    mem.write(0xFF07, 0x05)
    mem.write(0xFF06, 0xAB)  # TMA = 0xAB
    mem.write(0xFF05, 0xFE)  # TIMA = 0xFE

    # Aktivera timer interrupt i IE
    mem.write(0xFFFF, 0x04)

    # Kör några cykler som räcker för overflow
    cpu.run_n_cycles(16)  # justera vid behov
    cpu.run_n_cycles(16)  # justera vid behov

    # Kontrollera att TIMA har reloadat till TMA
    assert mem.read(0xFF05) == 0xAB, f"TIMA should reload to TMA, got {mem.read(0xFF05):02X}"

    # Kontrollera att interrupt-flaggan (IF) är satt
    assert mem.read(0xFF0F) & 0x04, "Timer interrupt flag should be set in IF"

    print("Test passed!")

"""
def test_timer_interrupt_timing():
    import logging
    from pyboy.cpu import CPU

    logger = logging.getLogger()
    cpu = CPU(logger)
    cpu.load_program(bytes([0x00] * 0x8000))  # dummy ROM
    mem = cpu._state.memory

    # Set up timer
    mem.write(0xFF07, 0x05)  # TAC = 0x05
    mem.write(0xFF05, 0x00)  # TIMA = 0
    mem.write(0xFF06, 0x00)  # TMA = 0
    mem.write(0xFF0F, 0x00)  # IF = 0

    # Run ~500 cycles → should NOT set IF yet
    cpu.run_n_cycles(500)
    assert (mem.read(0xFF0F) & 0x04) == 0, "Timer interrupt flag set too early"

    # Run another ~500 cycles → should now set IF
    cpu.run_n_cycles(500)
    assert (mem.read(0xFF0F) & 0x04), "Timer interrupt flag was not set"

    print("Timing test passed!")

def test_minimal_timer_overflow_test():
    import logging
    from pyboy.cpu import CPU  # byt till din modul

    logger = logging.getLogger()
    cpu = CPU(logger)
    cpu.load_program(bytes([0x00] * 0x8000))
    mem = cpu._state.memory

    # Sätt upp timer
    mem.write(0xFF07, 0x05)  # TAC = 0x05 → enable, 262144 Hz → divider bit 3
    mem.write(0xFF06, 0xAA)  # TMA = 0xAA
    mem.write(0xFF05, 0xFF)  # TIMA = 0xFF → overflow direkt vid nästa tick
    mem.write(0xFF0F, 0x00)  # IF = 0

    # Kör bara en tick (16 cykler)
    cpu.run_n_cycles(16)

    # Läs resultat
    tima = mem.read(0xFF05)
    tma = mem.read(0xFF06)
    if_flag = mem.read(0xFF0F) & 0x04

    print(f"TIMA: {tima:02X}, TMA: {tma:02X}, IF flag: {if_flag}")

    # Kontroll
    assert tima == 0xAA, f"TIMA should reload TMA, got {tima:02X}"
    assert if_flag, "IF timer interrupt flag not set"

    print("Minimal test passed!")
"""