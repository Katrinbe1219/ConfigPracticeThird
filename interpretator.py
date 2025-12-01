import argparse
import re, os
from pathlib import Path
import requests, json
from typing import Any
import sys
import yaml

class Assembler:
    def __init__(self):
          self.config = self._set_up_args()
          #0-5 первые младшие биты были тем самым opcode, по которым будем различать команды
          self.commands  = {
             6: 7 ,#"const",
             16: 10, #'read',
             54: 10, #write,
             44: 13, #  qt

          }
        
          with open(self.config['binFile'], 'rb') as f:
               prog = f.read() 

          # память команд и данных должны быть обьединены
          #адреса инструкции находятся там же, где и адреса данных
          # интерпретатр должен ичтать команды из той же самой памяти, где он потом будет записывать
          self.memory = bytearray(prog)
          # создается последовательность изменяемая из байтов, двоичные файл  остсоит из байтов

          
          self.command_count = 0
          self.running = True
          self.run()
        
    def mask(self, n):
         return (1 << n) - 1
    

    def _set_up_args(self) -> dict[str, Any]:
            parser = argparse.ArgumentParser(
                 description="Разработка Ассемблера",
                 epilog=""
            )

          #   parser.add_argument(
          #        '--dampFile',
          #        required=True,
          #        type=str,
          #        help="Путь к файлу, куда будет сохранен дамп памяти после выполнения программы."
          #   )

            parser.add_argument(
                 '--binFile',
                 required=True,
                 type=str,
                 help="Путь к двоичному файлу-результату."
            )

          #   parser.add_argument(
          #        '--d',
          #        required=True,
          #        help = "Диапазон адресов памяти для вывода дампа.",
          #        action=int
          #   )

            return vars(parser.parse_args())
    

    def get_instruction(self, opcode):
         return self.commands.get(opcode, None)
    
    def read_bits(self, bit_pos, nbits) -> int:
          if nbits == 0:
              return 0
          value = 0

          for i in range(nbits):
               bindex = (bit_pos + i) // 8
               byte_ = (bit_pos + i)%8

               if bindex >= len(self.memory):
                   bit = 0
               else:
                    # получаем байт, сдивгаем до нужного бита - чтоб он стал младшим и оставляем его
                    bit = (self.memory[bindex] >> byte_) & 1

               value |= (bit << i) # по принципу младший бит первым
          return value
                   
         

    
    def read_instruction(self, file):
        # текущая позиция
        current_poss = file.tell()


        # прочитали первый байт
        first_byte = file.read(1)

        if  not first_byte:
             return None
        

        # чтобы поулчить opcode - нужно прочитать первые 0-5 бита
        opcode = first_byte[0] & 0x3F
        size = self.get_instruction(opcode)

        #прочитвыаем целую команду
        file.seek(current_poss)
        data = file.read(size)

        if len(data) < size:
            return None

        return data
    
    def write_bits(self, bit_pos, value, nbits):
          if nbits == 0:
              return
          last_bit = bit_pos + nbits -1
          self.ensure_mem_bits(last_bit)
          for i in range(nbits):
               bit = (value >> i) & 1
               bindex = (bit_pos + i) // 8
               boff = (bit_pos + i) % 8
               # маска нужна, чтобы мы записали один бит, а другие не изменились
               mask = 1 << boff

               if bit:
                    # | - or ставит бит в 1
                    self.memory[bindex] |= mask
               else:
                    # если бит был 1, то он сбрасывается благодаря отрицанию и AND, остальное для того, что бы было 8 бит
                    self.memory[bindex] &= (~mask) & 0xFF
         
    def ensure_mem_bits(self, last_bit_index: int):
        """Ensure memory can address bit index last_bit_index (inclusive)."""
        if last_bit_index < 0:
            raise IndexError("Negative bit access")
        needed_bytes = (last_bit_index // 8) + 1
        if needed_bytes > len(self.memory):
            self.memory.extend(b'\x00' * (needed_bytes - len(self.memory)))

    def decode_instruction(self, data):
        opcode = data[0] & 0x3F #opcode
        cmd = int.from_bytes(data, 'little')
        if opcode == 6:
            
            b = (cmd >> 6) & self.mask(19)
            c = (cmd >> 25) & self.mask(27)
            return ('const', opcode, b,c)
        
        elif opcode == 16:
             
             b = (cmd >> 6) & self.mask(27)
             c = (cmd >> 33) & self.mask(27)
             d = (cmd >> 60) & self.mask(14)
             return ("read", opcode, b,c,d)
        
        elif opcode == 54:
             b = (cmd >> 6) & self.mask(27)
             c = (cmd >> 33) & self.mask(14)
             d = (cmd >> 47) & self.mask(27)
             return ("write", opcode,b,c,d)
        
        elif opcode == 44:
             b = (cmd >> 6) & self.mask(27)
             c = (cmd >> 33) & self.mask(14)
             d = (cmd >> 47) & self.mask(27)
             e = (cmd >> 74) & self.mask(27)
             return ("qt", opcode,b,c,d,e)
        else:
             return('unknown', opcode)

    def execute_instruction(self, inst):
        op = inst[0]

        if op == "const":
              b,c = inst[2], inst[3]
              self.write_bits(c,b,19)

     #    elif op == "read":
     #        b,c,d = inst[2], inst[3], inst[4]
     #        adress_temp = self.read_bits(c,27)
     #        final_adress = adress_temp + d
     #        value_to_copy = self.read_bits(final_adress, 64)
     #        self.write_bits(b, value_to_copy, 64)

     #    elif op == "write":
     #        b,c,d = inst[2], inst[3], inst[4]
     #        base = self.read_bits(b, 27)
     #        dest = base+c
     #        val = self.read_bits(d, 64)
     #        self.write_bits(dest,val, 64)
        
        elif op == "qt":
            b,c,d,e = inst[2], inst[3], inst[4], inst[5]
            op1 = self.read_bits(b,64)
            op2 = self.read_bits(e,64)

            adress = self.read_bits(d,27)
            final = adress + c

            self.write_bits(final, op1+op2, 64)
        elif op == "read":
          b,c,d = inst[2], inst[3], inst[4]
          final_address = (c + d  )   *8  # просто складываем адрес и смещение
          value_to_copy = self.read_bits(final_address,64)
          self.write_bits(b, value_to_copy,64)

          # Исправленный write
        elif op == "write":
          b,c,d = inst[2], inst[3], inst[4]
          val = self.read_bits(d*8,64)  # читаем значение с адреса d
          dest = (b + c  )    *8             # адрес назначения
          self.write_bits(dest,val,64)
        else:
             self.running = False

        
         
    def run(self):
        
     pc = 0
     while self.running:
          if (pc//8) >= len(self.memory):
               break

          opcode = self.read_bits(pc,6)
          instr = self.get_instruction(opcode)
          if instr is None:
               break

          insrt_bits = instr*8
          start_byte = pc //8

          self.ensure_mem_bits(pc + insrt_bits -1)
          data = bytes(self.memory[start_byte:start_byte + instr])
          decode_instr = self.decode_instruction(data)
          self.execute_instruction(decode_instr)
          self.command_count+=1
          pc += insrt_bits
        

def test_for_original(asm):

     const_val = asm.read_bits(932, 19)
     assert const_val == 402, f"Ошибка: const записан {const_val}, ожидается 402"

     
     read_val = asm.read_bits(497, 64)
     expected_read = asm.read_bits(492, 27)  
     assert read_val == expected_read, f"Ошибка read: {read_val} != {expected_read}"


     write_val = asm.read_bits(954+745, 64)
     expected_write = asm.read_bits(995, 64)
     assert write_val == expected_write, f"Ошибка write: {write_val} != {expected_write}"


     qt_val = asm.read_bits(1021, 64)
     expected_qt = asm.read_bits(1020, 64) + asm.read_bits(997, 64)
     assert qt_val == expected_qt, f"Ошибка qt: {qt_val} != {expected_qt}"

     print("Все assert проверки пройдены успешно!")

def verify_array_copy(asm, source_start, dest_start, length, element_size: int = 64):

    for i in range(length):
        source_val = asm.read_bits(source_start + i * element_size, element_size)
        dest_val = asm.read_bits(dest_start + i * element_size, element_size)
        assert dest_val == source_val, (
            f"Ошибка копирования элемента {i}: значение в исходном массиве {source_val}, "
            f"в целевом массиве {dest_val}"
        )
    print(f"Все {length} элементов успешно скопированы из {source_start} в {dest_start}.")


if __name__ == "__main__":
     inter = Assembler()
     test_for_original(inter)
     source_start = 1000
     dest_start = 2000
     array_length = 5  # количество элементов

     #verify_array_copy(inter, source_start, dest_start, array_length)

     
    