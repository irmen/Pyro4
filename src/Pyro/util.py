import sys
import traceback
import linecache
import logging
import Pyro.constants

log=logging.getLogger("Pyro.util")

def getPyroTraceback(ex_type=None, ex_value=None, ex_tb=None):
    """return a list of strings that form the traceback information of a
    Pyro exception. Any remote Pyro exception information is included.
    Traceback information is automatically obtained via sys.exc_info() if 
    you do not supply the objects yourself."""
    def formatRemoteTraceback(remote_tb_lines) :
        result=[]
        result.append(" +--- This exception occured remotely (Pyro) - Remote traceback:")
        for line in remote_tb_lines :
            if line.endswith("\n"):
                line=line[:-1]
            lines = line.split("\n")
            for line in lines :
                result.append("\n | ")
                result.append(line)
        result.append("\n +--- End of remote traceback")
        return result
    try:
        if ex_type is None and ex_tb is None:
            ex_type, ex_value, ex_tb=sys.exc_info()
        remote_tb=getattr(ex_value,Pyro.constants.TRACEBACK_ATTRIBUTE,None)
        local_tb=formatTraceback(ex_type, ex_value, ex_tb)
        if remote_tb:
            remote_tb=formatRemoteTraceback(remote_tb)
            return local_tb + remote_tb
        else:
            # hmm. no remote tb info, return just the local tb.
            return local_tb
    finally:
        # clean up cycle to traceback, to allow proper GC
        del ex_type, ex_value, ex_tb
        


def formatTraceback(ex_type=None, ex_value=None, ex_tb=None, detailed=False):
    """format an exception traceback. If you ask for detailed formatting,
    the result will contain info on the variables in each stack frame.
    You don't have to provide the exception info objects, if you omit them,
    this function will obtain them itself using sys.exc_info()."""
    if ex_type is None and ex_tb is None:
        ex_type,ex_value,ex_tb=sys.exc_info()
    if detailed:
        get_line_number = traceback.tb_lineno
    
        res = ['-'*50+ "\n",
               " <%s> RAISED : %s\n" % (str(ex_type), str(ex_value)),
               " Extended Stacktrace follows (most recent call last)\n",
               '-'*50+'\n' ]
     
        try:
            if ex_tb != None:
                frame_stack = []
                line_number_stack = []
     
                while 1:
                    line_num = get_line_number(ex_tb)
                    line_number_stack.append(line_num)
                    if not ex_tb.tb_next:
                        break
                    ex_tb = ex_tb.tb_next
     
                f = ex_tb.tb_frame
                for _ in line_number_stack:
                    frame_stack.append(f)
                    f = f.f_back
     
                frame_stack.reverse()
     
                lines = iter(line_number_stack)
                seen_crap = 0
                for frame in frame_stack:
                    # Get items
                    flocals = frame.f_locals.items()[:]
     
                    line_num = lines.next()
                    filename = frame.f_code.co_filename
     
                    name = None
                    for key, value, in flocals:
                        if key == "self":
                            name = "%s::%s" % (value.__class__.__name__, frame.f_code.co_name)
                    if name == None:
                        name = frame.f_code.co_name
     
                    res.append('File "%s", line (%s), in %s\n' % (filename, line_num, name))
                    res.append("Source code:\n")
                    
                    code_line = linecache.getline(filename, line_num)
                    if code_line:
                        res.append('    %s\n' % code_line.strip())
      
                    if not seen_crap:
                        seen_crap = 1
                        continue
      
                    res.append("Local values:\n")
                    flocals.sort()
                    fcode=frame.f_code
                    for key, value, in flocals:
                        if key in fcode.co_names or key in fcode.co_varnames or key in fcode.co_cellvars:
                            local_res="  %20s = " % key
                            try:
                                local_res += repr(value)
                            except:
                                try:
                                    local_res += str(value)
                                except:
                                    local_res += "<ERROR>"
                                    
                            res.append(local_res+"\n")
                            
                    res.append('-'*50 + '\n')
            res.append(" <%s> RAISED : %s\n" % (str(ex_type), str(ex_value)))
            res.append('-'*50+'\n')
            return res
            
        except:
            return ["-"*50+"\nError building extended traceback!!! :\n",
                  "".join(traceback.format_exception(* sys.exc_info() ) ) + '-'*50 + '\n',
                  "Original Exception follows:\n",
                  "".join(traceback.format_exception(ex_type, ex_value, ex_tb)) ]

    else:
        # default traceback format.
        return traceback.format_exception(ex_type, ex_value, ex_tb)
