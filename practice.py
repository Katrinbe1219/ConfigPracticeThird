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
        self.test_mode = False
        self.text_ = None

        self.mapping = {
            'const': self.down_const,
            'read': self.read_,
            'write':self.write_,
            'gt': self.qt_
        }
        self.machine_code = None
        self.command_count = None

        
        self.start_executing(self.config)
        


    
         
    def _set_up_args(self) -> dict[str, Any]:
            parser = argparse.ArgumentParser(
                 description="Разработка Ассемблера",
                 epilog=""
            )

            parser.add_argument(
                 '--textFile',
                 required=True,
                 type=str,
                 help="Путь к исходному файлу с текстом программы."
            )

            parser.add_argument(
                 '--binFile',
                 required=True,
                 type=str,
                 help="Путь к двоичному файлу-результату."
            )

            parser.add_argument(
                 '--test',
                 required=False,
                 help = "Режим тестирования",
                 action='store_true'
            )

            return vars(parser.parse_args())
    
    def _resolve_path(self, text_path):
        path = Path(text_path)

        if path.is_absolute():
            return path

        base_url = [
              Path.cwd(), #cur_dir
              Path(__file__).parent, #script dir
              Path.home()

         ]
        

        for base in base_url:
            possible_path = base / path
            if possible_path.exists():
                return possible_path
            
        return Path.cwd()/path
        
    def translate(self):
        program = self.text_
        command_count   = 0
        machine_code = b''

        for cmd in program:
            mnemonic = cmd['op']
            args_ = cmd['args']

            if mnemonic not in self.mapping:
                return "Команды не существует"
            

            if cmd['op'] == "const":
                machine_code += self.mapping[mnemonic](args_[0]['A'], args_[1]['B'], args_[2]['C'])
            elif cmd['op'] == "read":
                machine_code += self.mapping[mnemonic](args_[0]['A'], args_[1]['B'], args_[2]['C'], args_[3]['D'])
            elif cmd['op'] == "write":
                machine_code += self.mapping[mnemonic](args_[0]['A'], args_[1]['B'], args_[2]['C'], args_[3]['D'])
            elif cmd['op'] == "qt":
                machine_code += self.mapping[mnemonic](args_[0]['A'], args_[1]['B'], args_[2]['C'], args_[3]['D'], args_[4]['E'])

            command_count +=1
        
        self.machine_code =machine_code
        self.command_count = command_count
        return ""
        

    
    def start_executing(self, args: dict[str, Any]):  
        checking = self.checking_args(args)

        if checking != "":
            sys.exit(checking)

        
        
        if self.test_mode:
            translation = self.translate()
            if translation != "":
                sys.exit(translation)

            self.assemble_to_file(args['binFile'])

    def assemble_to_file(self, path):

        with open(path, 'wb') as file:
            file.write(self.machine_code)

        print("Ассемблировано комамнд: ", self.command_count)
        print("Размер машинного кода: ", len(self.machine_code))
        print("Результат записанный в файле: ", self.machine_code)



    
    def execute_code(self, ):
        program = self.text_
        
        for cmd in program:
            args_ = cmd['args']
            self._print_args(args_)
            if cmd['op'] == "const":
                print("Const: [ " + self.down_const(args_[0]['A'], args_[1]['B'], args_[2]['C']) + "]\n")
            elif cmd['op'] == "read":
                print("Read: [ " + self.read_(args_[0]['A'], args_[1]['B'], args_[2]['C'], args_[3]['D'])+ "]\n")
            elif cmd['op'] == "write":
                print( "Write: [ " + self.write_(args_[0]['A'], args_[1]['B'], args_[2]['C'], args_[3]['D'])+ "]\n")
            elif cmd['op'] == "qt":
                print("Qt: [ " + self.write_(args_[0]['A'], args_[1]['B'], args_[2]['C'], args_[3]['D'], args_[4]['E'])+ "]\n")

    def _print_args(self, args: dict):
        print("TEST")
        for item in args:
            for key, data in item.items():
                print(f"{key} = {data}", end = " ")
        print()
            

    def checking_args(self, args: dict[str, Any]):
        file = args['textFile']
        absolute_path = self._resolve_path(file)

        if not absolute_path.exists():
            return f"Такого пути в textFile не сущетсвует"
        else:
            with open(absolute_path, "r")  as file:
                data = yaml.load(file, Loader=yaml.FullLoader)    

            self.text_= data['program']
        
        binFile = args['binFile']

        absolute_path = self._resolve_path(binFile)
        if not absolute_path:
            Path.touch(absolute_path)


        if args.get("test", None) != None and args.get("test", None) != False:
            self.test_mode = True

        
        return ""


    def mask(self, n):
         return (1<<n) -1
    
    def down_const(self,a,b,c):
        mask_b = self.mask(19)
        mask_c = self.mask(27)

        cmd = (a & self.mask(6))

        cmd |= (b & mask_b) << 6
        cmd |=(c & mask_c) << 25

        
        return cmd.to_bytes(7, "little")
    

    def read_(self,a,b,c,d):
        cmd = a & self.mask(6)
        cmd |= (b & self.mask(27)) << 6
        cmd |= (c & self.mask(27)) << 33
        cmd |= (d & self.mask(14)) << 60

        
        return cmd.to_bytes(10, "little")
    
    def write_(self,a,b,c,d):
        cmd = a & self.mask(6)
        cmd |= (b& self.mask(27)) << 6
        cmd |= (c & self.mask(14)) << 33
        cmd |= (d & self.mask(27)) << 47

        return cmd.to_bytes(10, "little")
    

    def  qt_(self,a,b,c,d,e):
        cmd = a & self.mask(6)
        cmd |= (b& self.mask(27)) << 6
        cmd |= (c & self.mask(14)) << 33
        cmd |= (d & self.mask(27)) << 47
        cmd |= (e & self.mask(27)) << 74

        return cmd.to_bytes(13, "little")



if __name__ == "__main__":
    asc = Assembler()
    # const_ =  asc.down_const(6,402, 932)
    # print(f"Результат: {const_}")

    # read_ = asc.read_(16,497,492,684)
    # print(f"Результат: {read_}")

    # write_ = asc.write_(54,954,745,995)
    # print(f"Результат: {write_}")

    # qt_ = asc.qt_(44,1020,443,997,1021)
    # print(f"Результат: {qt_}")
