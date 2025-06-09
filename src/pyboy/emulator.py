import time
import pygame
from typing import List
from pyboy.cpu import CPU, IdleLoopException
import readline


"""
    Gearboy visar en vit rad längst upp i början innan något körs
"""

class Emulator:
    def __init__(self, logger, debug: bool = False, scaling_factor: int=5):
        self._logger = logger
        self._debug = debug
        self._breakpoints: List[int] = []
        self._scaling_factor = scaling_factor

        self._cpu = CPU(logger=self._logger, debug=self._debug)
        self._cpu.set_addresses()

        self._PALETTE = [
            (255, 255, 255),  # White
            (192, 192, 192),  # Light gray
            (96, 96, 96),     # Dark gray
            (0, 0, 0),        # Black
        ]

    def load_rom_file(self, filepath: str):
        rom_data: bytes

        with open(filepath, "rb") as f:
            rom_data = f.read()

        self._cpu.load_program(rom_data)

    def _wait_for_command(self):
        while True:
            print(
                f"ZF: {self._cpu._state.zf}, NF: {self._cpu._state.nf}, CF: {self._cpu._state.cf}"
            )
            
            for k,v in self._cpu._state.__dict__.items():
                if len(k) > 3:
                    continue
                print(f'{k} == 0x{v:02X}')
            command = input(f"0x{self._cpu._state.pc:04X} ) ")

            if command == "exit":
                raise StopIteration()
            elif command.startswith("mem"):
                start_mem, count = command.split(" ")[1:3]
                start_mem = int(start_mem, 16)
                count = int(count)
                for i in range(0, count):
                    print(f'{self._cpu._state.memory.read(start_mem+i):0X}', end=' ')
                print('')

            elif command == "info registers" or command == "ir":
                print(
                    f"ZF: {self._cpu._state.zf}, NF: {self._cpu._state.nf}, CF: {self._cpu._state.cf}"
                )
                print(
                    f"A: {self._cpu._state.A}, B: {self._cpu._state.B}, C: {self._cpu._state.C}, D: {self._cpu._state.D}, E: {self._cpu._state.E}, HL: {self._cpu._state.HL}"
                )
            elif (command == "step" or command.startswith("step ")) or (
                command == "s" or command.startswith("s ")
            ):
                number_of_steps = 1
                try:
                    number_of_steps = int(command.split(" ", maxsplit=1)[1])
                except IndexError:
                    pass

                for _ in range(number_of_steps):
                    self._cpu.run_n_cycles(1)
                    print(
                        f"ZF: {self._cpu._state.zf}, NF: {self._cpu._state.nf}, CF: {self._cpu._state.cf}"
                    )
                    print(
                        f"A: {self._cpu._state.A}, B: {self._cpu._state.B}, C: {self._cpu._state.C}, D: {self._cpu._state.D}, E: {self._cpu._state.E}, HL: {self._cpu._state.HL}"
                    )

            elif command.startswith("breakpoint") or command.startswith("b"):
                address = int(command.split(" ")[1], 16)
                if address in self._breakpoints:
                    self._breakpoints.remove(address)
                    print(f"Removed breakpoint at address 0x{address:02X}!")
                else:
                    self._breakpoints.append(address)
                    print(f"Added breakpoint at address 0x{address:02X}")

            elif command == "continue" or command == "c":
                i = 0
                while True:
                    if i > 0 and self._cpu._state.pc in self._breakpoints:
                        print(f"Stopped at breakpoint at 0x{self._cpu._state.pc:02X}!")
                        break
                    else:
                        try:
                            self._cpu.run_n_cycles()
                        except Exception:
                            print(
                                f"ZF: {self._cpu._state.zf}, NF: {self._cpu._state.nf}, CF: {self._cpu._state.cf}"
                            )
                            print(
                                f"A: {self._cpu._state.A}, B: {self._cpu._state.B}, C: {self._cpu._state.C}, D: {self._cpu._state.D}, E: {self._cpu._state.E}, HL: {self._cpu._state.HL}"
                            )
                            raise

                        i = i + 1

            else:
                print(f"Invalid command {command}!")
    def _get_tile_pixels(self, cpu, tile_id):
        pixels = []

        # Läs LCDC-register (0xFF40)
        lcdc = cpu._state.memory.read(0xFF40)
        unsigned_ids = (lcdc & 0x10) != 0  # Bit 4: Tile data select

        # Korrekt base address beroende på tile ID-typ
        if unsigned_ids:
            base_address = 0x8000 + (tile_id * 16)
        else:
            tile_id_signed = tile_id if tile_id < 128 else tile_id - 256
            base_address = 0x8210 + (tile_id_signed * 16)

        for row in range(8):
            low = cpu._state.memory.read(base_address + row * 2)
            high = cpu._state.memory.read(base_address + row * 2 + 1)
            pixel_row = []

            for bit in reversed(range(8)):
                color = ((high >> bit) & 1) << 1 | ((low >> bit) & 1)
                pixel_row.append(color)
            pixels.append(pixel_row)

        return pixels

    
    def _render_tilemap(self, screen, cpu):
        
        tilemap_base= 0x9C00 if (cpu._state.memory.read(0xFF40) & 0x08) else 0x9800
        lcdc = cpu._state.memory.read(0xFF40)
        if (lcdc & 0x80) == 0:
            return
        for y in range(18):
            for x in range(20):
                tilemap_address = tilemap_base + (y * 32) + x
                tile_id = cpu._state.memory.read(tilemap_address)
                tile_pixels = self._get_tile_pixels(cpu, tile_id)

                for row in range(8):
                    for col in range(8):
                        color = self._PALETTE[tile_pixels[row][col]]
                        rect = pygame.Rect(
                            (x * 8 + col) * self._scaling_factor,
                            (y * 8 + row) * self._scaling_factor,
                            self._scaling_factor,
                            self._scaling_factor
                        )
                        pygame.draw.rect(screen, color, rect)

    def run(self):
        pygame.init()
        self._screen = pygame.display.set_mode((160*self._scaling_factor, 144*self._scaling_factor))
        pygame.display.set_caption("pyboy")

        if self._debug:
            try:
                self._wait_for_command()
            except IdleLoopException:
                print(f'Ended at {self._cpu._state.pc:02X}')
            except StopIteration:
                print("Execution ended")
                return
            except Exception as e:
                raise
            return
        clock = pygame.time.Clock()

        running = True
        while running:
            # Todo, run right amount of cycles per frame instead
            self._cpu.run_n_cycles(70224)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False


            self._screen.fill((255, 255, 255))
            self._render_tilemap(self._screen, self._cpu)
            pygame.display.flip()


            clock.tick(60)

        pygame.quit()