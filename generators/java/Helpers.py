import os
from enum import Enum

class TypeDescriptorType(Enum):
    Byte = 'byte'
    Struct = 'struct'
    Enum = 'enum'


def is_builtin_type(typename, size):
    # byte up to long are passed as 'byte' with size set to proper value
    return not isinstance(size, str) and TypeDescriptorType.Byte.value == typename and size <= 8


class AttributeKind(Enum):
    SIMPLE = 1
    BUFFER = 2
    ARRAY = 3
    CUSTOM = 4
    UNKNOWN = 100


def get_attribute_size(schema, attribute):
    if 'size' not in attribute and attribute['type'] != TypeDescriptorType.Byte.value and attribute['type'] != TypeDescriptorType.Enum.value:
        attr = schema[attribute['type']]
        if 'size' in attr:
            return attr['size']
        else:
            return 1
    return attribute['size']


def get_attribute_kind(schema, attribute):
    attribute_type = attribute['type']
    if attribute_type == TypeDescriptorType.Struct.value or attribute_type == TypeDescriptorType.Enum.value:
        return AttributeKind.CUSTOM
    if 'size' not in attribute:
        type_descriptor = schema[attribute_type]
        return get_attribute_kind(schema, type_descriptor)

    attribute_size = attribute['size']

    if isinstance(attribute_size, str):
        if attribute_size.endswith('Size'):
            return AttributeKind.BUFFER
        
        if attribute_size.endswith('Count'):
            return AttributeKind.ARRAY

    if is_builtin_type(attribute_type, attribute_size):
        return AttributeKind.SIMPLE

    return AttributeKind.BUFFER


class TypeDescriptorDisposition(Enum):
    Inline = 'inline'
    Const = 'const'


def indent(code, n_indents=1):
    return ' ' * 4 * n_indents + code


def get_attribute_if_size(attribute_name, attributes):
    for attribute in attributes:
        if 'size' in attribute and attribute['size'] == attribute_name:
            return attribute['name']

    return None


def get_attribute_where_property_equal(schema, attributes, attribute_name, attribute_value):
    for attribute in attributes:
        if attribute_name in attribute and attribute[attribute_name] == attribute_value:
            return attribute
        if 'disposition' in attribute and attribute['disposition'] == TypeDescriptorDisposition.Inline.value:
            value = get_attribute_where_property_equal(schema, schema[attribute['type']]['layout'], attribute_name, attribute_value)
            if value is not None:
                return value

    return None

def get_builtin_type(size):
    builtin_types = {1: 'byte', 2: 'short', 4: 'int', 8: 'long'}
    builtin_type = builtin_types[size]
    return builtin_type


def get_read_method_name(size):
    if isinstance(size, str) or size > 8:
        method_name = 'readFully'
    else:
        typesize_methodname = {1: 'readByte',
                               2: 'readShort', 4: 'readInt', 8: 'readLong'}
        method_name = typesize_methodname[size]
    return method_name


def get_write_method_name(size):
    if isinstance(size, str) or size > 8:
        method_name = 'write'
    else:
        typesize_methodname = {1: 'writeByte',
                               2: 'writeShort', 4: 'writeInt', 8: 'writeLong'}
        method_name = typesize_methodname[size]
    return method_name


def get_generated_type(schema, attribute):
    typename = attribute['type']
    attribute_kind = get_attribute_kind(schema, attribute)
    if attribute_kind == AttributeKind.SIMPLE:
        return get_builtin_type(get_attribute_size(schema, attribute))
    elif attribute_kind == AttributeKind.BUFFER:
        return 'ByteBuffer'
    elif attribute_kind == AttributeKind.ARRAY:
        return 'java.util.ArrayList<{0}>'.format(typename)

    return typename