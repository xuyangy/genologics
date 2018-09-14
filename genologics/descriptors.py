"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""

from genologics.constants import nsmap

try:
    from urllib.parse import urlsplit, urlparse, parse_qs, urlunparse
except ImportError:
    from urlparse import urlsplit, urlparse, parse_qs, urlunparse

import datetime
import time
from collections import MutableSet
from xml.etree import ElementTree

import logging

logger = logging.getLogger(__name__)


class BaseDescriptor(object):
    "Abstract base descriptor for an instance attribute."

    def __get__(self, instance, cls):
        raise NotImplementedError


class TagDescriptor(BaseDescriptor):
    """Abstract base descriptor for an instance attribute
    represented by an XML element.
    """

    def __init__(self, tag):
        self.tag = tag

    def get_node(self, instance):
        if self.tag:
            return instance.root.find(self.tag)
        else:
            return instance.root


class StringDescriptor(TagDescriptor):
    """An instance attribute containing a string value
    represented by an XML element.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            return None
        else:
            return node.text

    def __set__(self, instance, value):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            # create the new tag
            node = ElementTree.Element(self.tag)
            instance.root.append(node)
        node.text = str(value)


class StringAttributeDescriptor(TagDescriptor):
    """An instance attribute containing a string value
    represented by an XML attribute.
    """

    def __get__(self, instance, cls):
        instance.get()
        return instance.root.attrib[self.tag]

    def __set__(self, instance, value):
        instance.get()
        instance.root.attrib[self.tag] = value


class StringTagAttributeDescriptor(TagDescriptor):
    """A named string attribute on a child element of the entity's root."""

    def __init__(self, tag, attribute):
        super(StringTagAttributeDescriptor, self).__init__(tag)
        self.attribute = attribute

    def __get__(self, instance, cls):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            return None
        else:
            return node.attrib.get(self.attribute)

    def __set__(self, instance, value):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            # create the new tag
            node = ElementTree.Element(self.tag)
            instance.root.append(node)
        node.attrib[self.attribute] = str(value)


class StringListDescriptor(TagDescriptor):
    """An instance attribute containing a list of strings
    represented by multiple XML elements.
    """

    def __get__(self, instance, cls):
        instance.get()
        result = []
        for node in instance.root.findall(self.tag):
            result.append(node.text)
        return result


class StringDictionaryDescriptor(TagDescriptor):
    """An instance attribute containing a dictionary of string key/values
    represented by a hierarchical XML element.
    """

    def __get__(self, instance, cls):
        instance.get()
        result = dict()
        node = instance.root.find(self.tag)
        if node is not None:
            for node2 in node.getchildren():
                result[node2.tag] = node2.text
        return result


class IntegerDescriptor(StringDescriptor):
    """An instance attribute containing an integer value
    represented by an XMl element.
    """

    def __get__(self, instance, cls):
        text = super(IntegerDescriptor, self).__get__(instance, cls)
        if text is not None:
            return int(text)


class IntegerAttributeDescriptor(TagDescriptor):
    """An instance attribute containing a integer value
    represented by an XML attribute.
    """

    def __get__(self, instance, cls):
        instance.get()
        return int(instance.root.attrib[self.tag])


class BooleanDescriptor(StringDescriptor):
    """An instance attribute containing a boolean value
    represented by an XMl element.
    """

    def __get__(self, instance, cls):
        text = super(BooleanDescriptor, self).__get__(instance, cls)
        if text is not None:
            return text.lower() == 'true'

    def __set__(self, instance, value):
        super(BooleanDescriptor, self).__set__(instance, str(value).lower())


class UdfDictionary(object):
    "Dictionary-like container of UDFs, optionally within a UDT."

    def _is_string(self, value):
        try:
            return isinstance(value, basestring)
        except:
            return isinstance(value, str)

    def __init__(self, instance, *args, **kwargs):
        self.instance = instance
        self._udt = kwargs.pop('udt', False)
        self.rootkeys = args
        self._rootnode = None
        self._update_elems()
        self._prepare_lookup()
        self.location = 0

    @property
    def rootnode(self):
        if self._rootnode is None:
            self._rootnode = self.instance.root
            for rootkey in self.rootkeys:
                self._rootnode = self._rootnode.find(rootkey)
        return self._rootnode

    def get_udt(self):
        if self._udt == True:
            return None
        else:
            return self._udt

    def set_udt(self, name):
        assert isinstance(name, str)
        if not self._udt:
            raise AttributeError('cannot set name for a UDF dictionary')
        self._udt = name
        elem = self.rootnode.find(nsmap('udf:type'))
        assert elem is not None
        elem.set('name', name)

    udt = property(get_udt, set_udt)

    def _update_elems(self):
        self._elems = []
        if self._udt:
            elem = self.rootnode.find(nsmap('udf:type'))
            if elem is not None:
                self._udt = elem.attrib['name']
                self._elems = elem.findall(nsmap('udf:field'))
        else:
            tag = nsmap('udf:field')
            for elem in self.rootnode.getchildren():
                if elem.tag == tag:
                    self._elems.append(elem)

    def _prepare_lookup(self):
        self._lookup = dict()
        for elem in self._elems:
            type = elem.attrib['type'].lower()
            value = elem.text
            if not value:
                value = None
            elif type == 'numeric':
                try:
                    value = int(value)
                except ValueError:
                    value = float(value)
            elif type == 'boolean':
                value = value == 'true'
            elif type == 'date':
                value = datetime.date(*time.strptime(value, "%Y-%m-%d")[:3])
            self._lookup[elem.attrib['name']] = value

    def __contains__(self, key):
        try:
            self._lookup[key]
        except KeyError:
            return False
        return True

    def __getitem__(self, key):
        return self._lookup[key]

    def __setitem__(self, key, value):
        self._lookup[key] = value
        for node in self._elems:
            if node.attrib['name'] != key: continue
            vtype = node.attrib['type'].lower()

            if value is None:
                pass
            elif vtype == 'string':
                if not self._is_string(value):
                    raise TypeError('String UDF requires str or unicode value')
            elif vtype == 'str':
                if not self._is_string(value):
                    raise TypeError('String UDF requires str or unicode value')
            elif vtype == 'text':
                if not self._is_string(value):
                    raise TypeError('Text UDF requires str or unicode value')
            elif vtype == 'numeric':
                if not isinstance(value, (int, float)):
                    raise TypeError('Numeric UDF requires int or float value')
                value = str(value)
            elif vtype == 'boolean':
                if not isinstance(value, bool):
                    raise TypeError('Boolean UDF requires bool value')
                value = value and 'true' or 'false'
            elif vtype == 'date':
                if not isinstance(value, datetime.date):  # Too restrictive?
                    raise TypeError('Date UDF requires datetime.date value')
                value = str(value)
            elif vtype == 'uri':
                if not self._is_string(value):
                    raise TypeError('URI UDF requires str or punycode (unicode) value')
                value = str(value)
            else:
                raise NotImplemented("UDF type '%s'" % vtype)

            node.text = value
            break
        else:  # Create new entry; heuristics for type
            if self._is_string(value):
                vtype = '\n' in value and 'Text' or 'String'
            elif isinstance(value, bool):
                vtype = 'Boolean'
                value = value and 'true' or 'false'
            elif isinstance(value, (int, float)):
                vtype = 'Numeric'
                value = str(value)
            elif isinstance(value, datetime.date):
                vtype = 'Date'
                value = str(value)
            else:
                raise NotImplementedError("Cannot handle value of type '%s'"
                                          " for UDF" % type(value))
            if self._udt:
                root = self.rootnode.find(nsmap('udf:type'))
            else:
                root = self.rootnode
            elem = ElementTree.SubElement(root,
                                          nsmap('udf:field'),
                                          type=vtype,
                                          name=key)
            elem.text = value

            #update the internal elements and lookup with new values
            self._update_elems()
            self._prepare_lookup()

    def __delitem__(self, key):
        del self._lookup[key]
        for node in self._elems:
            if node.attrib['name'] == key:
                self.rootnode.remove(node)
                break

    def items(self):
        return list(self._lookup.items())

    def clear(self):
        for elem in self._elems:
            self.rootnode.remove(elem)
        self._update_elems()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            ret = list(self._lookup.keys())[self.location]
        except IndexError:
            raise StopIteration()
        self.location = self.location + 1
        return ret

    def get(self, key, default=None):
        return self._lookup.get(key, default)


class UdfDictionaryDescriptor(BaseDescriptor):
    """An instance attribute containing a dictionary of UDF values
    represented by multiple XML elements.
    """
    _UDT = False

    def __init__(self, *args):
        super(BaseDescriptor, self).__init__()
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        self.value = UdfDictionary(instance, *self.rootkeys, udt=self._UDT)
        return self.value

    def __set__(self, instance, dict_value):
        instance.get()
        udf_dict = UdfDictionary(instance, *self.rootkeys, udt=self._UDT)
        udf_dict.clear()
        for k in dict_value:
            udf_dict[k] = dict_value[k]


class UdtDictionaryDescriptor(UdfDictionaryDescriptor):
    """An instance attribute containing a dictionary of UDF values
    in a UDT represented by multiple XML elements.
    """

    _UDT = True


class PlacementDictionaryDescriptor(TagDescriptor):
    """An instance attribute containing a dictionary of locations
    keys and artifact values represented by multiple XML elements.
    """

    def __get__(self, instance, cls):
        from genologics.entities import Artifact
        instance.get()
        self.value = dict()
        for node in instance.root.findall(self.tag):
            key = node.find('value').text
            self.value[key] = Artifact(instance.lims, uri=node.attrib['uri'])
        return self.value


class ExternalidListDescriptor(BaseDescriptor):
    """An instance attribute yielding a list of tuples (id, uri) for
    external identifiers represented by multiple XML elements.
    """

    def __get__(self, instance, cls):
        instance.get()
        result = []
        for node in instance.root.findall(nsmap('ri:externalid')):
            result.append((node.attrib.get('id'), node.attrib.get('uri')))
        return result


class EntityDescriptor(TagDescriptor):
    "An instance attribute referencing another entity instance."

    def __init__(self, tag, klass):
        super(EntityDescriptor, self).__init__(tag)
        self.klass = klass

    def __get__(self, instance, cls):
        instance.get()
        node = instance.root.find(self.tag)
        if node is None:
            return None
        else:
            return self.klass(instance.lims, uri=node.attrib['uri'])

    def __set__(self, instance, value):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            # create the new tag
            node = ElementTree.Element(self.tag)
            instance.root.append(node)
        node.attrib['uri'] = value.uri


class EntityAttributeDescriptor(BaseDescriptor):
    """An instance attribute referencing another entity instance, implemented
    as an attribute on the root node."""

    def __init__(self, attribute, klass):
        super(EntityAttributeDescriptor, self).__init__()
        self.attribute = attribute
        self.klass = klass

    def __get__(self, instance, cls):
        instance.get()
        attr = instance.root.attrib.get(self.attribute)
        if attr is None:
            return None
        else:
            return self.klass(instance.lims, uri=attr)


class EntityListDescriptor(EntityDescriptor):
    """An instance attribute yielding a list of entity instances
    represented by multiple XML elements.
    """

    def __get__(self, instance, cls):
        instance.get()
        result = []
        for node in instance.root.findall(self.tag):
            result.append(self.klass(instance.lims, uri=node.attrib['uri']))

        return result


class NestedAttributeListDescriptor(StringAttributeDescriptor):
    """An instance yielding a list of dictionnaries of attributes
       for a nested xml list of XML elements"""

    def __init__(self, tag, *args):
        super(StringAttributeDescriptor, self).__init__(tag)
        self.tag = tag
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            result.append(node.attrib)
        return result


class NestedStringListDescriptor(StringListDescriptor):
    """An instance yielding a list of strings
        for a nested list of xml elements"""

    def __init__(self, tag, *args):
        super(StringListDescriptor, self).__init__(tag)
        self.tag = tag
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            result.append(node.text)
        return result


class NestedEntityListDescriptor(EntityListDescriptor):
    """same as EntityListDescriptor, but works on nested elements"""

    def __init__(self, tag, klass, *args):
        super(EntityListDescriptor, self).__init__(tag, klass)
        self.klass = klass
        self.tag = tag
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            result.append(self.klass(instance.lims, uri=node.attrib['uri']))
        return result

class InlineEntityListDescriptor(EntityListDescriptor):
    """EntityListDescriptor which saves the XML tags in the parent entity as the
    root elements of the referenced entities. Useful when the full body of the
    referenced entity is enclosed in the parent."""

    def __init__(self, tag, klass, *args):
        super(EntityListDescriptor, self).__init__(tag, klass)
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode=instance.root
        for rootkey in self.rootkeys:
            rootnode=rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            entity = self.klass(instance.lims, uri=node.attrib['uri'])
            entity.root = node
            result.append(entity)
        return result

class ObjectListDescriptor(EntityListDescriptor):
    """Represents a list of objects, which in general is not a list of
    Entities."""

    def __init__(self, tag, klass, *args):
        super(BaseDescriptor, self).__init__()
        self.tag = tag
        self.klass = klass
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode=instance.root
        for rootkey in self.rootkeys:
            rootnode=rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            result.append(self.klass(instance.lims, node))
        return result

class DimensionDescriptor(TagDescriptor):
    """An instance attribute containing a dictionary specifying
    the properties of a dimension of a container type.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = instance.root.find(self.tag)
        return dict(is_alpha=node.find('is-alpha').text.lower() == 'true',
                    offset=int(node.find('offset').text),
                    size=int(node.find('size').text))


class LocationDescriptor(TagDescriptor):
    """An instance attribute containing a tuple (container, value)
    specifying the location of an analyte in a container.
    """

    def __get__(self, instance, cls):
        from genologics.entities import Container
        instance.get()
        node = instance.root.find(self.tag)
        uri = node.find('container').attrib['uri']
        return Container(instance.lims, uri=uri), node.find('value').text


class ReagentLabelSet(MutableSet):
    """Holds infomation about reagent labels. Acts like a set, but
    also updates the underlying XML. It thus supports adding and deleting
    reagent labels."""

    def __init__(self, root):
        self.root = root
        self.value = set()
        for node in self.root.findall('reagent-label'):
            try:
                self.value.add(node.attrib['name'])
            except KeyError:
                pass

    def __contains__(self, i): return i in self.value

    def __iter__(self): return self.value.__iter__()

    def __len__(self): return len(self.value)

    def discard(self, name):
        self.value.remove(name) # Or fail if it's not there
        for node in self.root.findall('reagent-label'):
            try:
                if node.attrib['name'] == name:
                   break
            except (AttributeError, KeyError):
                pass
        else:
            raise RuntimeError("Internal state is not consistent")
        self.root.remove(node)

    def add(self, name):
        if not name in self.value:
            self.value.add(name)
            ElementTree.SubElement(self.root, 'reagent-label', {'name': name})

    def __str__(self):
        return str(self.value)

    def __getitem__(self, index):
        """Emulate list-like indexing to support code written when this was
        a list."""
        return list(self.value)[index]


class ReagentLabelSetDescriptor(BaseDescriptor):
    """An instance attribute yielding a list of reagent labels.

    Allows read-write access."""
    def __get__(self, instance, cls):
        instance.get()
        return ReagentLabelSet(instance.root)


class InputOutputMapList(BaseDescriptor):
    """An instance attribute yielding a list of tuples (input, output)
    where each item is a dictionary, representing the input/output
    maps of a Process instance.
    """

    def __init__(self, *args):
        super(BaseDescriptor, self).__init__()
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        self.value = []
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        for node in rootnode.findall('input-output-map'):
            input = self.get_dict(instance.lims, node.find('input'))
            output = self.get_dict(instance.lims, node.find('output'))
            self.value.append((input, output))
        return self.value

    def get_dict(self, lims, node):
        from genologics.entities import Artifact, Process
        if node is None: return None
        result = dict()
        for key in ['limsid', 'output-type', 'output-generation-type']:
            try:
                result[key] = node.attrib[key]
            except KeyError:
                pass
            for uri in ['uri', 'post-process-uri']:
                try:
                    result[uri] = Artifact(lims, uri=node.attrib[uri])
                except KeyError:
                    pass
        node = node.find('parent-process')
        if node is not None:
            result['parent-process'] = Process(lims, node.attrib['uri'])
        return result
