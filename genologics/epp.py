import logging
import sys
import os
from shutil import copy
from html import HTML

def attach_file(src,resource):
    """Attach file at src to given resource

    Copies the file to the current directory, EPP node will upload this file
    automatically if the process output is properly set up"""
    original_name = os.path.basename(src)
    new_name = resource.id + '_' + original_name
    dir = os.getcwd()
    location = os.path.join(dir,new_name)
    print "Moving {0} to {1}".format(src,location)
    copy(src,location)

def unique_check(l,msg):
    "Check that l is of length 1, otherwise raise error, with msg appended"
    if len(l)==0:
        raise Exception("No item found for {0}".format(msg))
    elif len(l)!=1:
        raise Exception("Multiple items found for {0}".format(msg))



    
class EppLogger(object):
    """Logger class that collect stdout, stderr and info. Output is in html."""

    def __enter__(self):
        pass

    def __exit__(self,exc_type,exc_val,exc_tb):
        self.htmlify()

    def __init__(self, log_file,level=logging.INFO):
        self.log_file = log_file
        # check if file is empty:
        self.fresh = (not os.path.isfile(log_file)) or os.stat(log_file).st_size == 0
        self.level = level
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
            filename=log_file,
            filemode='a'
            )

        # This part was copied together with the StreamToLogger class below
        stdout_logger = logging.getLogger('STDOUT')
        sl = self.StreamToLogger(stdout_logger, logging.INFO)
        sys.stdout = sl

        stderr_logger = logging.getLogger('STDERR')
        sl = self.StreamToLogger(stderr_logger, logging.ERROR)
        sys.stderr = sl

    def htmlify(self):
        """Turn log file into html with colour coding"""
        pre_style = """pre {
                      white-space: pre-wrap; /* css-3 */
                      white-space: -moz-pre-wrap !important; /* Mozilla, since 1999 */
                      white-space: -pre-wrap; /* Opera 4-6 */
                      white-space: -o-pre-wrap; /* Opera 7 */
                      word-wrap: break-word; /* Internet Explorer 5.5+ */
                      border: 1px double #cccccc;
                      background-color: #f0f8ff;
                      padding: 5px;
                   }"""
        colors= {'green':'#28DD31'}

        log = open(self.log_file,'r').read()
        if self.fresh:
            doc = HTML()
            h = doc.html
            he = h.head
            he.title("EPP script Log")
            he.style(pre_style,type="text/css")
            b = h.body
            b.pre(log)
            with open(self.log_file,'w') as f:
                f.write(str(h))


    class StreamToLogger(object):
        """Fake file-like stream object that redirects writes to a logger instance.
        
        source: 
        http://www.electricmonk.nl/log/2011/08/14/
        redirect-stdout-and-stderr-to-a-logger-in-python/
        """
        def __init__(self, logger, log_level=logging.INFO):
            self.logger = logger
            self.log_level = log_level
            self.linebuf = ''
            
        def write(self, buf):
            for line in buf.rstrip().splitlines():
                self.logger.log(self.log_level, line.rstrip())
                
