from .Helpers import *
from .JavaMethodGenerator import JavaMethodGenerator

class JavaEnumGenerator:
    def __init__(self, name, schema, attribute):
        self.enum_name = get_generated_class_name(name)
        self.enum_output = ['public enum {0} {{'.format(self.enum_name)]
        self.schema = schema
        self.privates = []
        self.attribute = attribute
        self.enum_values = {}

        self._add_enum_values(self.attribute)

    def _get_type(self, attribute):
        return get_builtin_type(attribute['size'])

    def _add_private_declaration(self, attribute):
        var_type = self._get_type(attribute)
        self.enum_output += [indent('private final {0} value;'.format(var_type))] + ['']

    def _add_enum_values(self, enum_attribute):
        enum_attribute_values = enum_attribute['values']
        for current_attribute in enum_attribute_values:
            self.add_enum_value(current_attribute['name'], current_attribute['value'])
 
    def _write_enum_values(self):
        enum_type = self._get_type(self.attribute)
        enum_length = len(self.enum_values)
        count = 1
        for name, value in self.enum_values.items():
            line = '{0}(({1}){2})'.format(name.upper(), enum_type, value)
            line += ',' if count < enum_length else ';'
            self.enum_output += [indent(line)]
            count += 1
        self.enum_output += ['']

    def _add_constructor(self, attribute):
        enum_type = self._get_type(attribute)
        constructor_method = JavaMethodGenerator('private', '', self.enum_name, [
                                                 '{0} value'.format(enum_type)])
        constructor_method.add_instructions(['this.value = value'])
        self.add_method(constructor_method)

    def _add_load_from_binary_method(self, attribute):
        load_from_binary_method = JavaMethodGenerator(
            'public', self.enum_name, 'loadFromBinary', ['DataInput stream'], 'throws Exception', True)
        load_from_binary_method.add_instructions(
            ['{0} val = stream.{1}()'.format(self._get_type(attribute), get_read_method_name(attribute['size']))])
        size = get_attribute_size(self.schema, attribute)
        reverse_byte_method = get_reverse_method_name_if_needed(size).format('val')
        load_from_binary_method.add_instructions(
            ['val = {0}'.format(reverse_byte_method)])
        load_from_binary_method.add_instructions(
            ['for ({0} current : {0}.values()) {{'.format(self.enum_name)], False)
        load_from_binary_method.add_instructions(
            [indent('if (val == current.value)')], False)
        load_from_binary_method.add_instructions(
            [indent('return current', 2)])
        load_from_binary_method.add_instructions(
            ['}'], False)
        load_from_binary_method.add_instructions(
            ['throw new RuntimeException(val + " was not a backing value for {0}.")'.format(self.enum_name)])
        self.add_method(load_from_binary_method)

    def _add_serialize_method(self, attribute):
        serialize_method = JavaMethodGenerator(
            'public', 'byte[]', 'serialize', [], 'throws Exception')
        serialize_method.add_instructions(
            ['ByteArrayOutputStream bos = new ByteArrayOutputStream()'])
        serialize_method.add_instructions(
            ['DataOutputStream stream = new DataOutputStream(bos)'])
        size = get_attribute_size(self.schema, attribute)
        reverse_byte_method = get_reverse_method_name_if_needed(size).format('this.value')
        serialize_method.add_instructions([
            'stream.{0}({1})'.format(get_write_method_name(size), reverse_byte_method)
        ])
        serialize_method.add_instructions(['stream.close()'])
        serialize_method.add_instructions(['return bos.toByteArray()'])
        self.add_method(serialize_method)

    def add_method(self, method):
        self.enum_output += [indent(line)
                             for line in method.get_method()] + ['']

    def add_enum_value(self, name, value):
        self.enum_values[name] = value

    def generate(self):
        self._write_enum_values()
        self._add_private_declaration(self.attribute)
        self._add_constructor(self.attribute)
        self._add_load_from_binary_method(self.attribute)
        self._add_serialize_method(self.attribute)
        return self.enum_output + ['}']