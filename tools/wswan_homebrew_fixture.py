"""Original WonderSwan/Color V30MZ tile-scrolling and wavetable audio ROM.

Only source-generated NEC V30MZ/8086-compatible code and generated pixel
patterns are used. No copyrighted game assets or boot firmware are included.
The native Mednafen core runs the resulting temporary 128-KiB cartridge.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

ROM_SIZE=128 * 1024
CODE_OFFSET=ROM_SIZE - 65536
SYSTEMS=("ws", "wsc")


def build_wonder_probe_rom(system="ws"):
    if system not in SYSTEMS:
        raise ValueError("Unknown original WonderSwan test platform")
    code=bytearray()
    marks={}
    near=[]
    short=[]
    def emit(*values):
        code.extend(values)
    def mov_ax(value):
        emit(0xB8,value & 255,value >> 8)
    def mov_di(value):
        emit(0xBF,value & 255,value >> 8)
    def mov_cx(value):
        emit(0xB9,value & 255,value >> 8)
    def mov_mem_word(address,value):
        emit(0xC7,0x06,address & 255,address >> 8,value & 255,value >> 8)
    def output(port,value):
        emit(0xB0,value & 255,0xE6,port)
    def mark(name):
        marks[name]=len(code)
    def jmp(name):
        near.append((len(code),name))
        emit(0xE9,0,0)
    def jnz(name):
        short.append((len(code),name))
        emit(0x75,0)

    # Correct real-mode segments: cartridge code in CS=F000, all VRAM/audio
    # wave/palette data in the WonderSwan IRAM DS/ES=0. Never use INT BIOS.
    emit(0xFA)             # CLI
    mov_ax(0)
    emit(0x8E,0xD8,0x8E,0xC0,0x8E,0xD0) # DS,ES,SS=0
    emit(0xBC,0x00,0x1F)   # SP=$1F00 (outside sound wavetable $1800)
    output(0x14,0x00)      # LCD temporarily disabled
    # Screen 1 tile map starts at RAM $0800; all 1024 entries tile zero.
    mov_ax(0)
    mov_di(0x0800)
    mov_cx(0x0400)
    emit(0xF3,0xAB)        # REP STOSW
    # 2bpp tile zero (8 rows x 2 bytes) at IRAM $2000:
    # alternating dark/bright columns. Scrolling X changes every frame.
    mov_ax(0x00AA)
    mov_di(0x2000)
    mov_cx(8)
    emit(0xF3,0xAB)
    if system=="wsc":
        # WSC 2bpp color mode; palette RAM is $FE00 in bank zero.
        output(0x60,0x80)
        mov_mem_word(0xFE00,0x0000)
        mov_mem_word(0xFE02,0x000F)
        mov_mem_word(0xFE04,0x00F0)
        mov_mem_word(0xFE06,0x0FFF)
    else:
        output(0x60,0x00)
        output(0x1C,0xF0)   # Original mono grey LUT
        output(0x1D,0xE1)
        output(0x1E,0xD2)
        output(0x1F,0xC3)
        output(0x20,0x10)   # shade 1 for tile color index 1
        output(0x21,0x32)
    output(0x07,0x01)      # Screen 1 map at RAM $0800
    output(0x01,0x00)      # Black BG
    output(0x00,0x01)      # Enable Screen 1
    output(0x14,0x01)      # Enable the physical LCD

    # Each source-generated 4-bit wavetable sample is 2 per byte.
    # Channel #1 base $1800, hardware address $8F = $1800 >> 6 = 0x60.
    mov_di(0x1800)
    mov_ax(0xFFFF)
    mov_cx(8)
    emit(0xF3,0xAB)        # 16 'high' wave bytes; other half zero.
    mov_ax(0)
    mov_cx(8)
    emit(0xF3,0xAB)
    output(0x8F,0x60)
    output(0x80,0x00)      # Channel 1 frequency divisor=1792
    output(0x81,0x07)
    output(0x88,0xFF)      # full left + right volume
    output(0x91,0x09)      # speaker and headphone enabled
    output(0x90,0x01)      # wavetable channel 1 ON

    emit(0xBB,0,0)         # MOV BX,0 (scroll position)
    mark("animation")
    emit(0x88,0xD8)        # MOV AL,BL
    emit(0xE6,0x10)        # OUT screen1 horizontal scroll
    emit(0xFE,0xC3)        # INC BL
    mov_cx(0xFFFF)
    mark("delay")
    emit(0x49)             # DEC CX
    jnz("delay")
    jmp("animation")

    for pos,name in short:
        disp=marks[name]-(pos+2)
        if not -128<=disp<=127:
            raise ValueError("V30 short jump outside range")
        code[pos+1]=disp & 255
    for pos,name in near:
        disp=marks[name]-(pos+3)
        if not -32768<=disp<=32767:
            raise ValueError("V30 near jump outside range")
        code[pos+1:pos+3]=disp.to_bytes(2,"little",signed=True)
    if len(code)>8192:
        raise ValueError("Unexpectedly large original WonderSwan program")

    rom=bytearray([0xFF])*ROM_SIZE
    rom[CODE_OFFSET:CODE_OFFSET+len(code)]=code
    # Last 16 bytes include CPU reset far JMP to F000:0000 and
    # 10-byte hardware cartridge metadata.
    footer=bytearray(16)
    footer[:5]=bytes.fromhex("EA 00 00 00 F0")
    footer[5]=0x80   # Boot customization ignored
    footer[6]=0      # Original homebrew / no commercial publisher
    footer[7]=1 if system=="wsc" else 0
    footer[8]=0x30   # Original test title ID
    footer[9]=0      # Revision zero
    footer[10]=0     # 1Mbit / 128KiB
    footer[11]=0     # No save cartridge RAM
    footer[12]=0x04  # Standard horizontal orientation, 16-bit bus
    footer[13]=0
    rom[-16:]=footer
    rom[-2:]=(sum(rom[:-2])&0xFFFF).to_bytes(2,"little")
    return bytes(rom)


def write_wonder_probe(destination,system="ws"):
    path=Path(destination)
    if system not in SYSTEMS or path.suffix.casefold()!="."+system:
        raise ValueError("Original WonderSwan test extension mismatch")
    content=build_wonder_probe_rom(system)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(content)
    return {
        "system":system,"sha256":hashlib.sha256(content).hexdigest(),
        "bytes":len(content),
        "source":"original V30MZ WonderSwan tile/PSG diagnostic",
        "commercial_game":False,
    }
