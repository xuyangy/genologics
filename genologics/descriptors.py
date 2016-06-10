"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""

import re

try:
    from urllib.parse import urlsplit, urlparse, parse_qs, urlunparse
except ImportError:
    from urlparse import urlsplit, urlparse, parse_qs, urlunparse

import datetime
import time
from xml.etree import ElementTree

import logging

logger = logging.getLogger(__name__)

_NSMAP = dict(
    art='http://genologics.com/ri/artifact',
    artgr='http://genologics.com/ri/artifactgroup',
    cnf='http://genologics.com/ri/configuration',
    con='http://genologics.com/ri/container',
    ctp='http://genologics.com/ri/containertype',
    exc='http://genologics.com/ri/exception',
    file='http://genologics.com/ri/file',
    inst='http://genologics.com/ri/instrument',
    lab='http://genologics.com/ri/lab',
    prc='http://genologics.com/ri/process',
    prj='http://genologics.com/ri/project',
    prop='http://genologics.com/ri/property',
    protcnf='http://genologics.com/ri/protocolconfiguration',
    protstepcnf='http://genologics.com/ri/stepconfiguration',
    prx='http://genologics.com/ri/processexecution',
    ptm='http://genologics.com/ri/processtemplate',
    ptp='http://genologics.com/ri/processtype',
    res='http://genologics.com/ri/researcher',
    ri='http://genologics.com/ri',
    rt='http://genologics.com/ri/routing',
    rtp='http://genologics.com/ri/reagenttype',
    kit='http://genologics.com/ri/reagentkit',
    lot='http://genologics.com/ri/reagentlot',
    smp='http://genologics.com/ri/sample',
    stg='http://genologics.com/ri/stage',
    stp='http://genologics.com/ri/step',
    udf='http://genologics.com/ri/userdefined',
    ver='http://genologics.com/ri/version',
    wkfcnf='http://genologics.com/ri/workflowconfiguration'
)

for prefix, uri in _NSMAP.items():
    ElementTree._namespace_map[uri] = prefix

_NSPATTERN = re.compile(r'(\{)(.+?)(\})')

def nsmap(tag):
    "Convert from normal XML-ish namespace tag to ElementTree variant."
    parts = tag.split(':')
    if len(parts) != 2:
        raise ValueError("no namespace specifier in tag")
    return "{%s}%s" % (_NSMAP[parts[0]], parts[1])


class SampleHistory:
    """Class handling the history generation for a given sample/artifact
    AFAIK the only fields of the history that are read are proc.type and outart""" 

    def __init__(self, sample_name=None, output_artifact=None, input_artifact=None, lims=None, pro_per_art=None, test=False):
        self.processes_per_artifact=pro_per_art
        if lims:
            self.lims = lims
            if not (test):
                #this is now the default
                self.sample_name=sample_name
                self.alternate_history(output_artifact, input_artifact)
                self.art_map=None
            elif (sample_name) and pro_per_art:
                self.sample_name=sample_name
                self.make_sample_artifact_map()
                if output_artifact:
                    self.get_analyte_hist_sorted(output_artifact, input_artifact)
        else:
            logger.error("Tried to build History without lims")
            raise AttributeError("History cannot be computed without a valid lims object")


    def control(self):
        """this can be used to check the content of the object.
        """
        logger.info("SAMPLE NAME: {}".format(self.sample_name))
        logger.info("outart : {}".format(self.history_list[0]))
        #logger.info ("\nmap :")
        #for key, value in self.art_map.iteritems():
        #    logger.info(value[1]+"->"+value[0].id+"->"+key)
        logger.info ("\nHistory :\n\n")
        logger.info("Input\tProcess\tProcess info")
        for key, dict in self.history.items():
            logger.info (key)
            for key2, dict2 in dict.items():
                logger.info ("\t{}".format(key2))
                for key, value in dict2.items():
                    logger.info ("\t\t{0}->{1}".format(key,(value if value is not None else "None")))
        logger.info ("\nHistory List")
        for art in self.history_list:
            logger.info (art)
        
    def make_sample_artifact_map(self):
        """samp_art_map: connects each output artifact for a specific sample to its 
        corresponding process and input artifact assuming, for a given sample,
        one input -> one process -> one output
        This function starts from the output, 
        and creates an entry like this : output -> (process, input)"""
        samp_art_map ={}
        if self.sample_name:
            artifacts = self.lims.get_artifacts(sample_name = self.sample_name, type = 'Analyte', resolve=False) 
            for one_art in artifacts:
                input_arts = one_art.input_artifact_list()
                for input_art in input_arts:
                    for samp in input_art.samples:
                        if samp.name == self.sample_name:
                            samp_art_map[one_art.id] = (one_art.parent_process, input_art.id)

        self.art_map=samp_art_map
    def alternate_history(self, out_art, in_art=None):
        """This is a try at another way to generate the history.
        This one iterates over Artifact.parent_process and Process.all_inputs()
        Then, it takes all the child processes for each input (because we want
        qc processes too) and puts everything in a dictionnary. 
        """
        history = {}
        hist_list = []
       #getting the list of all expected analytes.
        artifacts = self.lims.get_artifacts(sample_name = self.sample_name, type = 'Analyte', resolve=False)
        processes=[]
        inputs=[]
        if in_art:
            #If theres an input artifact given, I need to make a loop for this one, before treating it as an output
            starting_art=in_art
            inputs.append(in_art)
            history[in_art]={}
            #If there is a loacl map, use it. else, query the lims.
            if self.processes_per_artifact and in_art in self.processes_per_artifact:
                valid_pcs=self.processes_per_artifact[in_art]
            else:
                valid_pcs=self.lims.get_processes(inputartifactlimsid=in_art)

            for tempProcess in valid_pcs:
                history[in_art][tempProcess.id] = {'date' : tempProcess.date_run,
                                                   'id' : tempProcess.id,
                                                   'outart' : (out_art if out_art in [ out.id for out in tempProcess.all_outputs()] else None ),
                                                   'inart' : in_art,
                                                   'type' : tempProcess.type.id,
                                                   'name' : tempProcess.type.name}
        else:
            starting_art=out_art
        #main iteration    
        #it is quite heavy on logger at info level
        not_done=True
        while not_done:
            logger.info ("looking for "+(starting_art))
            not_done=False 
            for o in artifacts:
                logger.info (o.id)
                if o.id == starting_art:
                    if o.parent_process is None:
                        #flow control : if there is no parent process, we can stop iterating, we're done.
                        not_done=False
                        break #breaks the for artifacts, we are done anyway.
                    else:
                        not_done=True #keep the loop running
                    logger.info ("found it")
                    processes.append(o.parent_process)
                    logger.info ("looking for inputs of "+o.parent_process.id)
                    for i in o.parent_process.all_inputs():
                        logger.info (i.id)
                        if i in artifacts:
                            history[i.id]={}
                            for tempProcess in (self.processes_per_artifact[i.id] if self.processes_per_artifact else self.lims.get_processes(inputartifactlimsid=i.id)):#If there is a loacl map, use it. else, query the lims.
                                history[i.id][tempProcess.id] = {'date' : tempProcess.date_run,
                                                               'id' : tempProcess.id,
                                                               'outart' : (o.id if tempProcess.id == o.parent_process.id else None),
                                                               'inart' : i.id,
                                                               'type' : tempProcess.type.id,
                                                               'name' : tempProcess.type.name}



                            logger.info ("found input "+i.id)
                            inputs.append(i.id) #this will be the sorted list of artifacts used to rebuild the history in order
                            # while increment
                            starting_art=i.id
                            
                            break #break the for allinputs, if we found the right one
                    break # breaks the for artifacts if we matched the current one
        self.history=history
        self.history_list=inputs 


    def get_analyte_hist_sorted(self, out_artifact, input_art = None):
         """Makes a history map of an artifac, using the samp_art_map 
         of the corresponding sample.
         The samp_art_map object is built up from analytes. This means that it will not 
         contain output-input info for processes wich have only files as output. 
         This is logical since the samp_art_map object is used for building up the ANALYTE 
         history of a sample. If you want to make the analyte history based on a 
         resultfile, that is; if you want to give a resultfile as out_artifact here, 
         and be given the historylist of analytes and processes for that file, you 
         will also have to give the input artifact for the process that generated 
         the resultfile for wich you want to get the history. In other words, if you 
         want to get the History of the folowing scenario:        
 
         History --- > Input_analyte -> Process -> Output_result_file
         
         then the arguments to this function should be:
         out_artifact = Output_result_file
         input_art = Input_analyte
 
         If you instead want the History of the folowing scenario:
         
         History --- > Input_analyte -> Process -> Output_analyte
 
         then you can skip the input_art argument and only set:
         out_artifact = Output_analyte 
         """
         history = {}
         hist_list = []
         if input_art:
            # In_art = Artifact(lims,id=input_art)
            # try:
            #     pro = In_art.parent_process.id
            # except:
            #     pro = None
             history, out_artifact = self._add_out_art_process_conection_list(input_art, 
                                                         out_artifact, history)
             hist_list.append(input_art)
         while out_artifact in self.art_map:
             pro, input_art = self.art_map[out_artifact]
             hist_list.append(input_art)
             history, out_artifact = self._add_out_art_process_conection_list(input_art, 
                                                        out_artifact, history)
         self.history=history
         self.history_list=hist_list
 
    def _add_out_art_process_conection_list(self, input_art, out_artifact, history = {}):
        """This function populates the history dict with process info per artifact.
        Maps an artifact to all the processes where its used as input and adds this 
        info to the history dict. Observe that the output artifact for the input 
        artifact in the historychain is given as input to this function. All 
        processes that the input artifact has been involved in, but that are not 
        part of the historychain get the outart set to None. This is very important."""
        # Use the local process map if we have one, else, query the lims
        from genologics import lims
        for process in self.processes_per_artifact[input_art] if self.processes_per_artifact else lims.get_processes(inputartifactlimsid = input_art):
            # outputs = map(lambda a: (a.id), process.all_outputs())
            outputs = [a.id for a in process.all_outputs()] 
            outart = out_artifact if out_artifact in outputs else None 
            step_info = {'date' : process.date_run,
                         'id' : process.id,
                         'outart' : outart,
                         'inart' : input_art,
                         'type' : process.type.id,
                         'name' : process.type.name}
            if input_art in history:
                history[input_art][process.id] = step_info
            else:
                history[input_art] = {process.id : step_info}
        return history, input_art

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
        node = self.get_node(instance)
        if node is None:
            #create the new tag
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

    def __init__(self, instance, udt=False):
        self.instance = instance
        self._udt = udt
        self._update_elems()
        self._prepare_lookup()
        self.location=0

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
        elem = self.instance.root.find(nsmap('udf:type'))
        assert elem is not None
        elem.set('name', name)

    udt = property(get_udt, set_udt)

    def _update_elems(self):
        self._elems = []
        if self._udt:
            elem = self.instance.root.find(nsmap('udf:type'))
            if elem is not None:
                self._udt = elem.attrib['name']
                self._elems = elem.findall(nsmap('udf:field'))
        else:
            tag = nsmap('udf:field')
            for elem in self.instance.root.getchildren():
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

    def __contains__(self,key):
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
                value = value and 'True' or 'False'
            elif vtype == 'date':
                if not isinstance(value, datetime.date): # Too restrictive?
                    raise TypeError('Date UDF requires datetime.date value')
                value = str(value)
            elif vtype == 'uri':
                if not isinstance(value, str):
                    raise TypeError('URI UDF requires str or punycode (unicode) value')
                value = str(value)
            else:
                raise NotImplemented("UDF type '%s'" % vtype)
            if not isinstance(value, str):
                value = str(value).encode('UTF-8')
            node.text = value
            break
        else:                           # Create new entry; heuristics for type
            if self._is_string(value):
                vtype = '\n' in value and 'Text' or 'String'
            elif isinstance(value, bool):
                vtype = 'Boolean'
                value = value and 'True' or 'False'
            elif isinstance(value, (int, float)):
                vtype = 'Numeric'
            elif isinstance(value, datetime.date):
                vtype = 'Date'
                value = str(value)
            else:
                raise NotImplementedError("Cannot handle value of type '%s'"
                                          " for UDF" % type(value))
            if self._udt:
                root = self.instance.root.find(nsmap('udf:type'))
            else:
                root = self.instance.root
            elem = ElementTree.SubElement(root,
                                          nsmap('udf:field'),
                                          type=vtype,
                                          name=key)
            if not isinstance(value, str):
                value =str(value).encode('UTF-8')
            elem.text = value

    def __delitem__(self, key):
        del self._lookup[key]
        for node in self._elems:
            if node.attrib['name'] == key:
                self.instance.root.remove(node)
                break

    def items(self):
        return list(self._lookup.items())

    def clear(self):
        for elem in self._elems:
            self.instance.root.remove(elem)
        self._update_elems()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            ret=list(self._lookup.keys())[self.location]
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

    def __get__(self, instance, cls):
        instance.get()
        self.value = UdfDictionary(instance, udt=self._UDT)
        return self.value

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
            self.value[key] = Artifact(instance.lims,uri=node.attrib['uri'])
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
        node = self.get_node(instance)
        if node is None:
            #create the new tag
            node = ElementTree.Element(self.tag)
            instance.root.append(node)
        node.attrib['uri'] = value.uri


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
        self.tag      = tag
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode=instance.root
        for rootkey in self.rootkeys:
            rootnode=rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            result.append(node.attrib)
        return result

class NestedStringListDescriptor(StringListDescriptor):
    """An instance yielding a list of strings
        for a nested list of xml elements"""
    def __init__(self, tag, *args):
        super(StringListDescriptor, self).__init__(tag)
        self.tag      = tag
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode=instance.root
        for rootkey in self.rootkeys:
            rootnode=rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            result.append(node.text)
        return result

class NestedEntityListDescriptor(EntityListDescriptor):
    """same as EntityListDescriptor, but works on nested elements"""

    def __init__(self, tag, klass, *args):
        super(EntityListDescriptor, self).__init__(tag, klass)
        self.klass    = klass
        self.tag      = tag
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode=instance.root
        for rootkey in self.rootkeys:
            rootnode=rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            result.append(self.klass(instance.lims, uri=node.attrib['uri']))
        return result

class DimensionDescriptor(TagDescriptor):
    """An instance attribute containing a dictionary specifying
    the properties of a dimension of a container type.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = instance.root.find(self.tag)
        return dict(is_alpha = node.find('is-alpha').text.lower() == 'true',
                    offset = int(node.find('offset').text),
                    size = int(node.find('size').text))

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

class ReagentLabelList(BaseDescriptor):
    """An instance attribute yielding a list of reagent labels"""
    def __get__(self, instance, cls):
        instance.get()
        self.value = []
        for node in instance.root.findall('reagent-label'):
            try:
                self.value.append(node.attrib['name'])
            except:
                pass
        return self.value

class InputOutputMapList(BaseDescriptor):
    """An instance attribute yielding a list of tuples (input, output)
    where each item is a dictionary, representing the input/output
    maps of a Process instance.
    """

    def __get__(self, instance, cls):
        instance.get()
        self.value = []
        for node in instance.root.findall('input-output-map'):
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

