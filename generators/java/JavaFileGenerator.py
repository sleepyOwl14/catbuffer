import os
from enum import Enum
from generators.Descriptor import Descriptor
from .Helpers import *
from .JavaMethodGenerator import JavaMethodGenerator
from .JavaEnumGenerator import JavaEnumGenerator
from .JavaClassGenerator import JavaClassGenerator

class JavaFileGenerator:
    def __init__(self, schema, options):
        self.schema = schema
        self.current = None
        self.options = options
        self.code = []

    def __iter__(self):
        self.current = self.generate()
        return self

    def __next__(self):
        self.code = []
        code, name = next(self.current)
        return Descriptor(name + '.java', code)

    def prepend_copyright(self, copyright_file):
        if os.path.isfile(copyright_file):
            with open(copyright_file) as header:
                self.code = [line.strip() for line in header] + ['']

    def set_import(self):
        self.code += ['import java.lang.*;']
        self.code += ['import java.io.*;']
        self.code += ['import java.nio.*;']
        self.code += ['import catapult.builders.*;'] + ['']

    def set_package(self):
        self.code += ['package catapult.builders;'] + ['']

    def generate(self):

        for type_descriptor, value in self.schema.items():
            self.code = []
            self.prepend_copyright(self.options['copyright'])
            self.set_package()
            self.set_import()
            attribute_type = value['type']

            if attribute_type == TypeDescriptorType.Byte.value:
                # Typeless environment, values will be directly assigned
                pass
            elif attribute_type == TypeDescriptorType.Enum.value:
                new_enum = JavaEnumGenerator(type_descriptor, self.schema)
                self.code += new_enum.generate(value)
                yield self.code, type_descriptor
            elif attribute_type == TypeDescriptorType.Struct.value:
                if type_descriptor.endswith('Body'): # skip all the inline classes
                    continue
                new_class = JavaClassGenerator(type_descriptor, self.schema, value['layout'])
                self.code += new_class.generate(value)
                yield self.code, JavaClassGenerator.get_generated_class_name(type_descriptor)

        return
