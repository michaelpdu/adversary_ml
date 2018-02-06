if __name__ == "__main__":
    from manipulate2 import *
else:
    from .manipulate2 import *

import sys

class PEModifier:
    """"""

    def __init__(self):
        self.bytez = bytes()

    def load_pe(self, file_path):
        with open(file_path, 'rb') as fh:
            self.bytez = bytes(fh.read())

    def save_pe(self, file_path):
        with open(file_path, 'wb') as fh:
            fh.write(self.bytez)

    def modify(self, dna):
        self.bytez = bytes(modify(self.bytez, dna))

help_msg = """
Usage:
    python pe_modifier.py input_pe  output_pe

"""

if __name__ == '__main__':
    input_pe = sys.argv[1]
    output_pe = sys.argv[2]

    pem = PEModifier()
    pem.load_pe(input_pe)
    # pem.modify({'imports_append_list': [("ADVAPI32.DLL", "CryptSetProvParam")]})
    # pem.modify({'imports_append_list': [("ADVAPI32.DLL", "LsaEnumerateAccounts")]})
    # pem.modify({'section_add_list': [[12,13,14,15,16,17], [22,23,24,25,26,27,28,29], [31,13,34,35,36,37,38]]})
    pem.modify({'section_add': None})
    pem.modify({'section_add': None})
    pem.save_pe(output_pe)