# TODO:
# * modify exports using lief
# * zero out rich header (if it exists) --> requires updating OptionalHeader's checksum ("Rich Header" only in Microsoft-produced executables)
# * tinker with resources: https://lief.quarkslab.com/doc/tutorials/07_pe_resource.html

import lief  # pip install https://github.com/lief-project/LIEF/releases/download/0.7.0/linux_lief-0.7.0_py3.6.tar.gz
import json
import os
import sys
import array
import struct  # byte manipulations
import random
import tempfile
import subprocess
import functools
import signal
import multiprocessing

module_path = os.path.split(os.path.abspath(sys.modules[__name__].__file__))[0]

COMMON_SECTION_NAMES = open(os.path.join(
    module_path, 'section_names.txt'), 'r').read().rstrip().split('\n')
COMMON_IMPORTS = json.load(
    open(os.path.join(module_path, 'small_dll_imports.json'), 'r'))


class MalwareManipulator(object):
    def __init__(self, bytez):
        self.bytez = bytez
        self.min_append_log2 = 5
        self.max_append_log2 = 8

    def __random_length(self):
        return 2**random.randint(self.min_append_log2, self.max_append_log2)

    def __binary_to_bytez(self, binary, dos_stub=False, imports=False, overlay=False, relocations=False, resources=False, tls=False):
        # write the file back as bytez
        builder = lief.PE.Builder(binary)
        builder.build_dos_stub(dos_stub) # rebuild DOS stub

        builder.build_imports(imports) # rebuild IAT in another section
        builder.patch_imports(imports) # patch original import table with trampolines to new import table

        builder.build_overlay(overlay) # rebuild overlay
        builder.build_relocations(relocations) # rebuild relocation table in another section
        builder.build_resources(resources) # rebuild resources in another section
        builder.build_tls(tls) # rebuilt TLS object in another section

        builder.build() # perform the build process

        # return bytestring
        return array.array('B', builder.get_build()).tobytes()

    def overlay_append(self, seed=None):
        random.seed(seed)
        L = self.__random_length()
        # choose the upper bound for a uniform distribution in [0,upper]
        upper = random.randrange(256)
        # upper chooses the upper bound on uniform distribution:
        # upper=0 would append with all 0s
        # upper=126 would append with "printable ascii"
        # upper=255 would append with any character
        return self.bytez + bytes([random.randint(0, upper) for _ in range(L)])

    def imports_append(self, seed=None):
        # add (unused) imports
        random.seed(seed)
        binary = lief.PE.parse(self.bytez)
        # draw a library at random
        libname = random.choice(list(COMMON_IMPORTS.keys()))
        funcname = random.choice(list(COMMON_IMPORTS[libname]))
        lowerlibname = libname.lower()
        # find this lib in the imports, if it exists
        lib = None
        for im in binary.imports:
            if im.name.lower() == lowerlibname:
                lib = im
                break
        if lib is None:
            # add a new library
            lib = binary.add_library(libname)
        # get current names
        names = set([e.name for e in lib.entries])
        if not funcname in names:
            lib.add_entry(funcname)

        self.bytez = self.__binary_to_bytez(binary,imports=True)

        return self.bytez

    def imports_append_list(self, name_pair_list):
        # add (unused) imports
        # random.seed(seed)
        binary = lief.PE.parse(self.bytez)
        # draw a library at random
        # libname = random.choice(list(COMMON_IMPORTS.keys()))
        # funcname = random.choice(list(COMMON_IMPORTS[libname]))

        for libname, funcname in name_pair_list:
            lowerlibname = libname.lower()
            # find this lib in the imports, if it exists
            lib = None
            for im in binary.imports:
                if im.name.lower() == lowerlibname:
                    lib = im
                    break
            if lib is None:
                # add a new library
                lib = binary.add_library(libname)
            # get current names
            names = set([e.name for e in lib.entries])
            if not funcname in names:
                lib.add_entry(funcname)

        # # modify section name
        # for section in binary.sections:
        #     new_section_name = '.' + "".join(chr(random.randrange(ord('a'), ord('z'))) for _ in range(4))
        #     section.name = new_section_name

        # # add funcname in first lib
        # if len(binary.imports) > 1:
        #     lib = binary.imports[0]
        #     for libname, funcname in name_pair_list:
        #         names = set([e.name for e in lib.entries])
        #         if not funcname in names:
        #             lib.add_entry(funcname)

        self.bytez = self.__binary_to_bytez(binary,imports=True)

        return self.bytez

    # def exports_append(self,seed=None):
    # TODO: when LIEF has a way to create this
    #     random.seed(seed)
    #     binary = lief.PE.parse( self.bytez )

    #     if not binary.has_exports:
    #         return self.bytez
    #         # TO DO: add a lief.PE.DATA_DIRECTORY.EXPORT_TABLE to the data directory

    #     # find the data directory
    #     for i,e in enumerate(binary.data_directories):
    #         if e.type == lief.PE.DATA_DIRECTORY.EXPORT_TABLE:
    #             break

    # def exports_reorder(self,seed=None):
    #   # reorder exports
    #   pass

    def section_rename_random(self, seed=None):
        # rename a random section
        random.seed(seed)
        binary = lief.PE.parse(self.bytez)
        targeted_section = random.choice(binary.sections)
        targeted_section.name = random.choice(COMMON_SECTION_NAMES)[:7] # current version of lief not allowing 8 chars?

        self.bytez = self.__binary_to_bytez(binary)

        return self.bytez

    def section_rename(self, ori_section_name, new_section_name):
        # rename a random section
        # random.seed(seed)
        # binary = lief.PE.parse(self.bytez)
        # targeted_section = random.choice(binary.sections)
        # targeted_section.name = random.choice(COMMON_SECTION_NAMES)[:7] # current version of lief not allowing 8 chars?

        binary = lief.PE.parse(self.bytez)
        for section in binary.sections:
            if section.name == ori_section_name:
                section.name = new_section_name

        self.bytez = self.__binary_to_bytez(binary)

        return self.bytez

    def section_add(self, seed=None):
        random.seed(seed)
        binary = lief.PE.parse(self.bytez)
        new_section = lief.PE.Section(
            '.'+"".join(chr(random.randrange(ord('a'), ord('z'))) for _ in range(4)))

        # fill with random content
        upper = random.randrange(256)
        L = self.__random_length()
        new_section.content = [random.randint(0, upper) for _ in range(L)]

        # new_section.virtual_address = max(
        #     [s.virtual_address + s.size for s in binary.sections])
        # add a new empty section

        binary.add_section(new_section,
                           random.choice([
                               lief.PE.SECTION_TYPES.BSS,
                               lief.PE.SECTION_TYPES.DATA,
                               #lief.PE.SECTION_TYPES.EXPORT,
                               #lief.PE.SECTION_TYPES.IDATA,
                               #lief.PE.SECTION_TYPES.RELOCATION,
                               #lief.PE.SECTION_TYPES.RESOURCE,
                               lief.PE.SECTION_TYPES.TEXT,
                               #lief.PE.SECTION_TYPES.TLS_,
                               lief.PE.SECTION_TYPES.UNKNOWN,
                           ]) )

        self.bytez = self.__binary_to_bytez(binary)
        return self.bytez

    def section_add_list(self, section_content_list):
        # random.seed(seed)
        binary = lief.PE.parse(self.bytez)

        for content in section_content_list:
            # new_section = lief.PE.Section(
            #     "".join(chr(random.randrange(ord('.'), ord('z'))) for _ in range(6)))

            new_section = lief.PE.Section(
                '.' + "".join(chr(random.randrange(ord('a'), ord('z'))) for _ in range(4)))

            # assign new content
            new_section.content = content
            # new_section.virtual_address = max(
            #     [s.virtual_address + s.size for s in binary.sections])

            # add a new empty section
            # binary.add_section(new_section,
            #                 random.choice([
            #                     lief.PE.SECTION_TYPES.BSS,
            #                     lief.PE.SECTION_TYPES.DATA,
            #                     lief.PE.SECTION_TYPES.EXPORT,
            #                     lief.PE.SECTION_TYPES.IDATA,
            #                     lief.PE.SECTION_TYPES.RELOCATION,
            #                     lief.PE.SECTION_TYPES.RESOURCE,
            #                     lief.PE.SECTION_TYPES.TEXT,
            #                     lief.PE.SECTION_TYPES.TLS_,
            #                     lief.PE.SECTION_TYPES.UNKNOWN,
            #                 ]))

            # binary.add_section(new_section, lief.PE.SECTION_TYPES.TEXT)

            binary.add_section(new_section,
                               random.choice([
                                   lief.PE.SECTION_TYPES.BSS,
                                   lief.PE.SECTION_TYPES.DATA,
                                   # lief.PE.SECTION_TYPES.EXPORT,
                                   # lief.PE.SECTION_TYPES.IDATA,
                                   # lief.PE.SECTION_TYPES.RELOCATION,
                                   # lief.PE.SECTION_TYPES.RESOURCE,
                                   lief.PE.SECTION_TYPES.TEXT,
                                   # lief.PE.SECTION_TYPES.TLS_,
                                   lief.PE.SECTION_TYPES.UNKNOWN,
                               ]))

        self.bytez = self.__binary_to_bytez(binary)
        return self.bytez

    def section_append(self, seed=None):
        # append to a section (changes size and entropy)
        random.seed(seed)
        binary = lief.PE.parse(self.bytez)
        targeted_section = random.choice(binary.sections)
        L = self.__random_length()
        available_size = targeted_section.size - len(targeted_section.content)
        if L > available_size:
            L = available_size

        upper = random.randrange(256)
        targeted_section.content = targeted_section.content + \
            [random.randint(0, upper) for _ in range(L)]

        self.bytez = self.__binary_to_bytez(binary)
        return self.bytez

    # def section_reorder(self,param,seed=None):
    #   # reorder directory of sections
    #   pass

    def create_new_entry(self, seed=None):
        # create a new section with jump to old entry point, and change entry point
        # DRAFT: this may have a few technical issues with it (not accounting for relocations), but is a proof of concept for functionality
        random.seed(seed)

        binary = lief.PE.parse(self.bytez)

        # get entry point
        entry_point = binary.optional_header.addressof_entrypoint

        # get name of section
        entryname = binary.section_from_rva(entry_point).name

        # create a new section
        new_section = lief.PE.Section(entryname + "".join(chr(random.randrange(
            ord('.'), ord('z'))) for _ in range(3)))  # e.g., ".text" + 3 random characters
        # push [old_entry_point]; ret
        new_section.content = [
            0x68] + list(struct.pack("<I", entry_point + 0x10000)) + [0xc3]
        new_section.virtual_address = max(
            [s.virtual_address + s.size for s in binary.sections])
        # TO DO: account for base relocation (this is just a proof of concepts)

        # add new section
        binary.add_section(new_section, lief.PE.SECTION_TYPES.TEXT)

        # redirect entry point
        binary.optional_header.addressof_entrypoint = new_section.virtual_address

        self.bytez = self.__binary_to_bytez(binary)
        return self.bytez

    def upx_pack(self, seed=None):
        # tested with UPX 3.91
        random.seed(seed)
        tmpfilename = os.path.join(
            tempfile._get_default_tempdir(), next(tempfile._get_candidate_names()))

        # dump bytez to a temporary file
        with open(tmpfilename, 'wb') as outfile:
            outfile.write(self.bytez)

        options = ['--force', '--overlay=copy']
        compression_level = random.randint(1, 9)
        options += ['-{}'.format(compression_level)]
        # --exact
        # compression levels -1 to -9
        # --overlay=copy [default]

        # optional things:
        # --compress-exports=0/1
        # --compress-icons=0/1/2/3
        # --compress-resources=0/1
        # --strip-relocs=0/1
        options += ['--compress-exports={}'.format(random.randint(0, 1))]
        options += ['--compress-icons={}'.format(random.randint(0, 3))]
        options += ['--compress-resources={}'.format(random.randint(0, 1))]
        options += ['--strip-relocs={}'.format(random.randint(0, 1))]

        with open(os.devnull, 'w') as DEVNULL:
            retcode = subprocess.call(
                ['upx'] + options + [tmpfilename, '-o', tmpfilename + '_packed'], stdout=DEVNULL, stderr=DEVNULL)

        os.unlink(tmpfilename)

        if retcode == 0:  # successfully packed

            with open(tmpfilename + '_packed', 'rb') as infile:
                self.bytez = infile.read()

            os.unlink(tmpfilename + '_packed')

        return self.bytez

    def upx_unpack(self, seed=None):
        # dump bytez to a temporary file
        tmpfilename = os.path.join(
            tempfile._get_default_tempdir(), next(tempfile._get_candidate_names()))

        with open(tmpfilename, 'wb') as outfile:
            outfile.write(self.bytez)

        with open(os.devnull, 'w') as DEVNULL:
            retcode = subprocess.call(
                ['upx', tmpfilename, '-d', '-o', tmpfilename + '_unpacked'], stdout=DEVNULL, stderr=DEVNULL)

        os.unlink(tmpfilename)

        if retcode == 0:  # sucessfully unpacked
            with open(tmpfilename + '_unpacked', 'rb') as result:
                self.bytez = result.read()

            os.unlink(tmpfilename + '_unpacked')

        return self.bytez

    def remove_signature(self, seed=None):
        random.seed(seed)
        binary = lief.PE.parse(self.bytez)

        if binary.has_signature:
            for i, e in enumerate(binary.data_directories):
                if e.type == lief.PE.DATA_DIRECTORY.CERTIFICATE_TABLE:
                    break
            if e.type == lief.PE.DATA_DIRECTORY.CERTIFICATE_TABLE:
                # remove signature from certificate table
                e.rva = 0
                e.size = 0
                self.bytez = self.__binary_to_bytez(binary)
                return self.bytez
        # if no signature found, self.bytez is unmodified
        return self.bytez

    def remove_debug(self, seed=None):
        random.seed(seed)
        binary = lief.PE.parse(self.bytez)

        if binary.has_debug:
            for i, e in enumerate(binary.data_directories):
                if e.type == lief.PE.DATA_DIRECTORY.DEBUG:
                    break
            if e.type == lief.PE.DATA_DIRECTORY.DEBUG:
                # remove signature from certificate table
                e.rva = 0
                e.size = 0
                self.bytez = self.__binary_to_bytez(binary)
                return self.bytez
        # if no signature found, self.bytez is unmodified
        return self.bytez

    def break_optional_header_checksum(self, seed=None):
        binary = lief.PE.parse(self.bytez)
        binary.optional_header.checksum = 0
        self.bytez = self.__binary_to_bytez(binary)
        return self.bytez


##############################
def identity(bytez, seed=None):
    return bytez


######################
# explicitly list so that these may be used externally
ACTION_TABLE = {
    # 'do_nothing': identity,
    'overlay_append': 'overlay_append',
    'imports_append': 'imports_append',
    'imports_append_list': 'imports_append_list',
    'section_rename': 'section_rename',
    'section_add': 'section_add',
    'section_add_list': 'section_add_list',
    'section_append': 'section_append',
    'create_new_entry': 'create_new_entry',
    'remove_signature': 'remove_signature',
    'remove_debug': 'remove_debug',
    'upx_pack': 'upx_pack',
    'upx_unpack': 'upx_unpack',
    'break_optional_header_checksum': 'break_optional_header_checksum',
    #   'modify_exports' : modify_exports,
}


def modify_without_breaking(bytez, actions=[], seed=None):
    for action in actions:

        _action = ACTION_TABLE[action]

        # we run manipulation in a child process to shelter
        # our malware model from rare parsing errors in LIEF that
        # may segfault or timeout
        def helper(_action,shared_list):
            # TODO: LIEF is chatty. redirect stdout and stderr to /dev/null

            # for this process, change segfault of the child process
            # to a RuntimeEror
            def sig_handler(signum, frame):
                raise RuntimeError
            signal.signal(signal.SIGSEGV, sig_handler)

            bytez = array.array('B', shared_list[:]).tobytes()
            # TODO: LIEF is chatty. redirect output to /dev/null
            if type(_action) is str:
                _action = MalwareManipulator(bytez).__getattribute__(_action)
            else:
                _action = functools.partial( _action, bytez )

            # redirect standard out only in this queue
            try:
                shared_list[:] = _action(seed) 
            except (RuntimeError,UnicodeDecodeError,TypeError,lief.not_found) as e:
                # some exceptions that have yet to be handled by public release of LIEF
                print("==== exception in child process ===")
                print(e)
                # shared_bytez remains unchanged                


        # communicate with the subprocess through a shared list
        # can't use multiprocessing.Array since the subprocess may need to
        # change the size
        manager = multiprocessing.Manager()
        shared_list = manager.list() 
        shared_list[:] = bytez # copy bytez to shared array
        # define process
        p = multiprocessing.Process( target=helper, args=(_action,shared_list) ) 
        p.start() # start the process
        try:
            p.join(5) # allow this to take up to 5 seconds...
        except multiprocessing.TimeoutError: # ..then become petulant
            print('==== timeouterror ')
            p.terminate()

        bytez = array.array('B', shared_list[:]).tobytes() # copy result from child process

    import hashlib
    m = hashlib.sha256()
    m.update( bytez )
    print("new hash: {}".format(m.hexdigest()))
    return bytez

# here actions is a map object
# {}
def modify(bytez, actions={}, seed=None):
    for action, params in actions.items():

        _action = ACTION_TABLE[action]

        # we run manipulation in a child process to shelter
        # our malware model from rare parsing errors in LIEF that
        # may segfault or timeout
        def helper(_action,shared_list):
            # TODO: LIEF is chatty. redirect stdout and stderr to /dev/null

            # for this process, change segfault of the child process
            # to a RuntimeEror
            def sig_handler(signum, frame):
                raise RuntimeError
            signal.signal(signal.SIGSEGV, sig_handler)

            bytez = array.array('B', shared_list[:]).tolist()
            # print('Action: {}, param: {}'.format(_action, params))
            # TODO: LIEF is chatty. redirect output to /dev/null
            if type(_action) is str:
                _action = MalwareManipulator(bytez).__getattribute__(_action)
            else:
                _action = functools.partial( _action, bytez )

            # redirect standard out only in this queue
            try:
                # print('Before action, _action: {}'.format(_action))
                ret_value = _action(params)
                #print('After action')
                shared_list[:] = ret_value
            except (RuntimeError,UnicodeDecodeError,TypeError,lief.not_found) as e:
                # some exceptions that have yet to be handled by public release of LIEF
                print("==== exception in child process ===")
                print(e)
                # shared_bytez remains unchanged


        # communicate with the subprocess through a shared list
        # can't use multiprocessing.Array since the subprocess may need to
        # change the size
        manager = multiprocessing.Manager()
        shared_list = manager.list()
        shared_list[:] = bytez # copy bytez to shared array
        # define process
        p = multiprocessing.Process( target=helper, args=(_action,shared_list) )
        p.start() # start the process
        try:
            p.join() # allow this to take up to 5 seconds...
        except multiprocessing.TimeoutError: # ..then become petulant
            print('==== timeouterror ')
            p.terminate()

        bytez = array.array('B', shared_list[:]).tobytes() # copy result from child process

    # import hashlib
    # m = hashlib.sha256()
    # m.update( bytez )
    # print("new hash: {}".format(m.hexdigest()))
    return bytez



def test(bytez):
    binary = lief.PE.parse(bytez)

    print('overlay_append')
    manip = MalwareManipulator(bytez)        
    bytez2 = manip.overlay_append(bytez)
    binary2 = lief.PE.parse(bytez2)
    assert len(binary.overlay) != len(binary2.overlay), "modification failed"

    # SUCCEEDS, but note that lief builder also adds a new ".l1" section for each patch of the imports
    print('imports_append')
    manip = MalwareManipulator(bytez)    
    bytez2 = manip.imports_append(bytez)
    binary2 = lief.PE.parse(bytez2)
    set1 = set(binary.imported_functions)
    set2 = set(binary2.imported_functions)
    diff = set2.difference(set1)
    print(list(diff))
    assert len(binary.imported_functions) != len(binary2.imported_functions), "no new imported functions"

    # SUCCEEDS
    print('section_rename')
    manip = MalwareManipulator(bytez)    
    bytez2 = manip.section_rename(bytez)
    binary2 = lief.PE.parse(bytez2)
    oldsections = [s.name for s in binary.sections]
    newsections = [s.name for s in binary2.sections]
    print(oldsections)
    print(newsections)
    assert " ".join(newsections) != " ".join(oldsections), "no modified sections"

    print('section_add')
    manip = MalwareManipulator(bytez)    
    bytez2 = manip.section_add(bytez)
    binary2 = lief.PE.parse(bytez2)
    oldsections = [s.name for s in binary.sections]
    newsections = [s.name for s in binary2.sections]
    print(oldsections)
    print(newsections)
    assert len(newsections) != len(oldsections), "no new sections"

    # FAILS if there's insufficient room to add to the section 
    print('section_append')
    manip = MalwareManipulator(bytez)    
    bytez2 = manip.section_append(bytez)
    binary2 = lief.PE.parse(bytez2)
    oldsections = [len(s.content) for s in binary.sections]
    newsections = [len(s.content) for s in binary2.sections]
    print(oldsections)
    print(newsections)
    assert sum(newsections) != sum(oldsections), "no appended section"

    print('create_new_entry') # note: also adds a new section
    manip = MalwareManipulator(bytez)    
    bytez2 = manip.create_new_entry(bytez)
    binary2 = lief.PE.parse(bytez2)
    print(binary.entrypoint)
    print(binary2.entrypoint)
    assert binary.entrypoint != binary2.entrypoint, "no new entry point"

    print('remove_signature')
    manip = MalwareManipulator(bytez)    
    bytez2 = manip.remove_signature(bytez)
    binary2 = lief.PE.parse(bytez2)
    if binary.has_signature:
        assert binary2.has_signature == False, "failed to remove signature"

    print('remove_debug')
    manip = MalwareManipulator(bytez)    
    bytez2 = manip.remove_debug(bytez)
    binary2 = lief.PE.parse(bytez2)
    if binary.has_debug:
        assert binary2.has_debug == False, "failed to remove debug"

    print('break_optional_header_checksum')
    manip = MalwareManipulator(bytez)    
    bytez2 = manip.break_optional_header_checksum(bytez)
    binary2 = lief.PE.parse(bytez2)
    assert binary2.optional_header.checksum == 0, "checksum not zero :("


