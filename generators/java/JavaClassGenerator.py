import os
from enum import Enum
from .Helpers import *
from .JavaMethodGenerator import JavaMethodGenerator

class JavaClassGenerator:
    @staticmethod
    def get_generated_class_name(name):
        return '{}'.format(name)

    def _get_generated_getter_name(self, attribute):
        return 'get{}'.format(attribute.capitalize())

    def _get_generated_setter_name(self, attribute_name):
        return 'set{}'.format(attribute_name.capitalize())

    def __init__(self, name, schema, class_schema):
        self.class_name = JavaClassGenerator.get_generated_class_name(name)
        self.class_output = ['public class {0} {{'.format(self.class_name)]
        self.load_from_binary_method = None
        self.serialize_method = None
        self.schema = schema
        self.class_schema = class_schema
        self.privates = []

    def _set_declarations(self):
        self.class_output += [indent(line) for line in self.privates] + ['']

    def _add_private_declaration(self, attribute):
        attribute_name = attribute['name']
        var_type = get_generated_type(self.schema, attribute)
        self.privates += ['private {0} {1};'.format(var_type, attribute_name)]

    def _add_simple_getter(self, attribute, new_getter):
        new_getter.add_instructions(
            ['return this.{0}'.format(attribute['name'])])

    def _add_buffer_getter(self, attribute, new_getter):
        new_getter.add_instructions(
            ['return this.{0}'.format(attribute['name'])])

    def _add_array_getter(self, attribute, new_getter):
        return_type = get_generated_type(self.schema, attribute)
        new_getter.add_instructions(
            ['return ({0})this.{1}'.format(return_type, attribute['name'])])

    def _add_method_condition(self, attribute, method_writer):
        if 'condition' in attribute:
            condition_type_attribute = get_attribute_where_property_equal(self.schema, self.class_schema, 'name', attribute['condition'])
            condition_type_prefix = ''
            if condition_type_attribute is not None:
                condition_type_prefix = '{0}.'.format(condition_type_attribute['type'])

            method_writer.add_instructions(['if ({0} != {1}{2})'.format(
                attribute['condition'], condition_type_prefix, attribute['condition_value'].upper())], False)
            method_writer.add_instructions(
                [indent('throw new java.lang.IllegalStateException()')])
            method_writer.add_instructions([''], False)

    def _add_getter(self, attribute):
        attribute_name = attribute['name']
        return_type = get_generated_type(self.schema, attribute)
        new_getter = JavaMethodGenerator(
            'public', return_type, self._get_generated_getter_name(attribute_name), [])
        self._add_method_condition(attribute, new_getter)

        getters = {
            AttributeKind.SIMPLE: self._add_simple_getter,
            AttributeKind.BUFFER: self._add_buffer_getter,
            AttributeKind.ARRAY: self._add_array_getter,
            AttributeKind.CUSTOM: self._add_simple_getter
        }
        attribute_kind = get_attribute_kind(self.schema, attribute)
        getters[attribute_kind](attribute, new_getter)
        self._add_method(new_getter)

    def _add_simple_setter(self, attribute, new_setter):
        new_setter.add_instructions(
            ['this.{0} = {0}'.format(attribute['name'])])

    def _add_buffer_setter(self, attribute, new_setter):
        attribute_size = get_attribute_size(self.schema, attribute)
        attribute_name = attribute['name']
        new_setter.add_instructions(
            ['if ({0} == null)'.format(attribute_name)], False)
        new_setter.add_instructions(
            [indent('throw new NullPointerException("{0}")'.format(attribute_name))])
        new_setter.add_instructions([''], False)
        if not isinstance(attribute_size, str):
            new_setter.add_instructions(
                ['if ({0}.array().length != {1})'.format(attribute_name, attribute_size)], False)
            new_setter.add_instructions(
                [indent('throw new IllegalArgumentException("{0} should be {1} bytes")'.format(attribute_name, attribute_size))])
        new_setter.add_instructions([''], False)
        new_setter.add_instructions(
            ['this.{0} = {0}'.format(attribute_name)])

    def _add_array_setter(self, attribute, new_setter):
        new_setter.add_instructions(
            ['this.{0} = {0}'.format(attribute['name'])])

    def _add_setter(self, attribute):
        attribute_name = attribute['name']
        return_type = get_generated_type(self.schema, attribute)
        new_setter = JavaMethodGenerator('public', 'void', self._get_generated_setter_name(
            attribute_name), [return_type + ' ' + attribute_name])
        self._add_method_condition(attribute, new_setter)

        setters = {
            AttributeKind.SIMPLE: self._add_simple_setter,
            AttributeKind.BUFFER: self._add_buffer_setter,
            AttributeKind.ARRAY: self._add_array_setter,
            AttributeKind.CUSTOM: self._add_simple_setter
        }

        attribute_kind = get_attribute_kind(self.schema, attribute)
        setters[attribute_kind](attribute, new_setter)
        self._add_method(new_setter)

    def _add_getter_setter(self, attribute):
        self._add_getter(attribute)
        self._add_setter(attribute)
        self._add_private_declaration(attribute)

    def _add_method(self, method):
        self.class_output += [indent(line)
                              for line in method.get_method()] + ['']
    
    def _recurse_inlines(self, generate_attribute_method, attributes):
        for attribute in attributes:
            if 'disposition' in attribute:
                if attribute['disposition'] == TypeDescriptorDisposition.Inline.value:
                    self._recurse_inlines(
                        generate_attribute_method, self.schema[attribute['type']]['layout'])
                elif attribute['disposition'] == TypeDescriptorDisposition.Const.value:
                    pass
            else:
                generate_attribute_method(
                    attribute, get_attribute_if_size(attribute['name'], attributes), attributes)

    def _add_attribute_condition_if_needed(self, attribute, class_schema, method_writer, obj_prefix):
        if 'condition' in attribute:
            condition_type_attribute = get_attribute_where_property_equal(self.schema, class_schema, 'name', attribute['condition'])
            condition_type_prefix = ''
            if condition_type_attribute is not None:
                condition_type_prefix = '{0}.'.format(condition_type_attribute['type'])

            method_writer.add_instructions(['if ({0}{1}() == {2}{3})'.format(
                obj_prefix, self._get_generated_getter_name(attribute['condition']), condition_type_prefix, attribute['condition_value'].upper())], False)
            return True
        return False

    def _load_from_binary_simple(self, attribute, class_attributes):
        indent_required = self._add_attribute_condition_if_needed(attribute, class_attributes, self.load_from_binary_method, 'obj.')
        line = 'obj.{0}(stream.{1}())'.format(self._get_generated_setter_name(
                attribute['name']), get_read_method_name(get_attribute_size(self.schema, attribute)))
        self.load_from_binary_method.add_instructions([indent(line) if indent_required else line])

    def _load_from_binary_buffer(self, attribute, clas_attributes):
        attribute_name = attribute['name']
        attribute_size = get_attribute_size(self.schema, attribute)
        self.load_from_binary_method.add_instructions(
            ['obj.{0} = ByteBuffer.allocate({1})'.format(attribute_name, attribute_size)])
        self.load_from_binary_method.add_instructions([
            'stream.{0}(obj.{1}.array())'.format(
                get_read_method_name(attribute_size), attribute_name)
        ])

    def _load_from_binary_array(self, attribute, class_attributes):
        attribute_typename = attribute['type']
        attribute_sizename = attribute['size']
        attribute_name = attribute['name']
        self.load_from_binary_method.add_instructions(['java.util.ArrayList<{1}> {0} = new java.util.ArrayList<{1}>({2})'.format(
            attribute_name, attribute_typename, attribute_sizename)])
        self.load_from_binary_method.add_instructions([
            'for (int i = 0; i < {0}; i++) {{'.format(attribute_sizename)], False)

        if attribute_typename == TypeDescriptorType.Byte.value:
            self.load_from_binary_method.add_instructions([indent(
                '{0}.add(stream.{1}())'.format(attribute_name, get_read_method_name(1)))])
        else:
            self.load_from_binary_method.add_instructions([indent(
                '{0}.add({1}.loadFromBinary(stream))'.format(attribute_name, attribute_typename))])
        self.load_from_binary_method.add_instructions(['}'], False)
        self.load_from_binary_method.add_instructions(['obj.{0}({1})'.format(
            self._get_generated_setter_name(attribute['name']), attribute_name)])

    def _load_from_binary_custom(self, attribute, class_attributes):
        self.load_from_binary_method.add_instructions([
            'obj.{0}({1}.loadFromBinary(stream))'.format(
                self._get_generated_setter_name(attribute['name']), attribute['type'])
        ])

    def _generate_load_from_binary_attributes(self, attribute, sizeof_attribute_name, class_attributes):
        attribute_name = attribute['name']
        if sizeof_attribute_name is not None:
            self.load_from_binary_method.add_instructions([
                '{0} {1} = stream.{2}()'.format(get_generated_type(self.schema, attribute),
                                                attribute['name'], get_read_method_name(attribute['size']))
            ])
        else:
            load_attribute = {
                AttributeKind.SIMPLE: self._load_from_binary_simple,
                AttributeKind.BUFFER: self._load_from_binary_buffer,
                AttributeKind.ARRAY: self._load_from_binary_array,
                AttributeKind.CUSTOM: self._load_from_binary_custom
            }

            attribute_kind = get_attribute_kind(self.schema, attribute)
            load_attribute[attribute_kind](attribute, class_attributes)

    def _generate_load_from_binary_method(self, attributes):
        self.load_from_binary_method = JavaMethodGenerator(
            'public', self.class_name, 'loadFromBinary', ['DataInput stream'], 'throws Exception', True)
        self.load_from_binary_method.add_instructions(
            ['{0} obj = new {0}()'.format(self.class_name)])
        self._recurse_inlines(
            self._generate_load_from_binary_attributes, attributes)
        self.load_from_binary_method.add_instructions(['return obj'])
        self._add_method(self.load_from_binary_method)

    def _serialize_attribute_simple(self, attribute, class_attributes):
        indent_required = self._add_attribute_condition_if_needed(attribute, class_attributes, self.serialize_method, 'this.')
        line = 'stream.{0}(this.{1}())'.format(get_write_method_name(get_attribute_size(self.schema, attribute)),
                                           self._get_generated_getter_name(attribute['name']))
        self.serialize_method.add_instructions([indent(line) if indent_required else line])

    def _serialize_attribute_buffer(self, attribute, clas_attributes):
        attribute_name = attribute['name']
        attribute_size = get_attribute_size(self.schema, attribute)
        self.serialize_method.add_instructions([
            'stream.{0}(this.{1}.array(), 0, this.{1}.array().length)'.format(
                get_write_method_name(attribute_size), attribute_name)
        ])

    def _serialize_attribute_array(self, attribute, class_attributes):
        attribute_typename = attribute['type']
        attribute_size = attribute['size']
        attribute_name = attribute['name']
        self.serialize_method.add_instructions([
            'for (int i = 0; i < this.{0}.size(); i++) {{'.format(attribute_name)
        ], False)

        if attribute_typename == TypeDescriptorType.Byte.value:
            self.serialize_method.add_instructions([indent(
                'stream.{0}(this.{1}.get(i))'.format(get_write_method_name(1), attribute_name))])
        else:
            self.serialize_method.add_instructions([indent(
                'byte[] ser = this.{0}.get(i).serialize()'.format(attribute_name))])
            self.serialize_method.add_instructions([indent(
                'stream.{0}(ser, 0, ser.length)'.format(get_write_method_name(attribute_size)))])
        self.serialize_method.add_instructions(['}'], False)

    def _serialize_attribute_custom(self, attribute, class_attributes):
        self.serialize_method.add_instructions([
            'byte[] {0} = this.{1}().serialize()'.format(attribute['name'],
                                                         self._get_generated_getter_name(attribute['name']))
        ])
        self.serialize_method.add_instructions([
            'stream.write({0}, 0, {0}.length)'.format(attribute['name'])
        ])

    def _generate_serialize_attributes(self, attribute, sizeof_attribute_name, class_attributes):
        attribute_name = attribute['name']
        if sizeof_attribute_name is not None:
            line = 'stream.{0}(this.{1}'.format(
                    get_write_method_name(get_attribute_size(self.schema, attribute)), sizeof_attribute_name)
            if attribute_name.endswith('Count'):
                line += '.size())'
            else:
                line += '.array().length)'
            self.serialize_method.add_instructions([line])
        else:
            serialize_attribute = {
                AttributeKind.SIMPLE: self._serialize_attribute_simple,
                AttributeKind.BUFFER: self._serialize_attribute_buffer,
                AttributeKind.ARRAY: self._serialize_attribute_array,
                AttributeKind.CUSTOM: self._serialize_attribute_custom
            }

            attribute_kind = get_attribute_kind(self.schema, attribute)
            serialize_attribute[attribute_kind](attribute, class_attributes)

    def _generate_serialize_method(self, attributes):
        self.serialize_method = JavaMethodGenerator(
            'public', 'byte[]', 'serialize', [], 'throws Exception')
        self.serialize_method.add_instructions(
            ['ByteArrayOutputStream bos = new ByteArrayOutputStream()'])
        self.serialize_method.add_instructions(
            ['DataOutputStream stream = new DataOutputStream(bos)'])
        self._recurse_inlines(self._generate_serialize_attributes, attributes)
        self.serialize_method.add_instructions(['stream.close()'])
        self.serialize_method.add_instructions(['return bos.toByteArray()'])
        self._add_method(self.serialize_method)

    def _generate_attributes(self, attribute, sizeof_attribute_name, class_attributes):
        if sizeof_attribute_name is None:
            self._add_getter_setter(attribute)
    
    def _generate_getter_setter(self, class_layout):
        self._recurse_inlines(self._generate_attributes, class_layout)

    def generate(self, class_schema):
        class_layout = class_schema['layout']
        self._generate_getter_setter(class_layout)
        self._generate_load_from_binary_method(class_layout)
        self._generate_serialize_method(class_layout)
        self._set_declarations()
        return self.class_output + ['}']
