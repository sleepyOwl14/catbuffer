import os
from .Helpers import indent

class JavaMethodGenerator:
    def __init__(self, scope, return_type, name, params, exception_list = '', static = False):
        self.name = name
        if static:
            self.method_output = ['{0} static {1} {2}({3}) {4} {{'.format(
                scope, return_type, self.name, ', '.join(params), exception_list)]
        else:
            self.method_output = ['{0} {1} {2}({3}) {4} {{'.format(
                scope, return_type, self.name, ', '.join(params), exception_list)]

    def add_instructions(self, instructions, add_semicolon=True):
        for instruction in instructions:
            if add_semicolon:
                instruction += ';'
            self.method_output.append(indent(instruction))

    def get_method(self):
        return self.method_output + ['}']