"""
HTTP gateway: connects the web browser's world of javascript+http and Pyro.
Creates a HTTP server that essentially is a proxy for the Pyro objects behind it.
It exposes the Pyro objects through a HTTP REST interface and uses the JSON serializer,
so that you can immediately process the response data in the browser.

You can start this module as a script from the command line, to easily get a
http gateway server running:

  :command:`python -m Pyro4.utils.httpgateway`
  or simply: :command:`pyro4-httpgateway`

It is also possible to import the 'pyro_app' function and stick that into a WSGI
server of your choice, to have more control.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import print_function
import sys
import json
import re
import cgi
from wsgiref.simple_server import make_server
import Pyro4
import Pyro4.errors
import Pyro4.message
import Pyro4.util
import Pyro4.constants


__all__ = ["pyro_app", "main"]


_nameserver = None
def get_nameserver(hmac=None):
    global _nameserver
    if not _nameserver:
        _nameserver = Pyro4.locateNS(hmac_key=hmac)
    try:
        _nameserver.ping()
        return _nameserver
    except Pyro4.errors.ConnectionClosedError:
        _nameserver = None
        print("Connection with nameserver lost, reconnecting...")
        return get_nameserver(hmac)


def invalid_request(start_response):
    """Called if invalid http method."""
    start_response('405 Method Not Allowed', [('Content-Type', 'text/plain')])
    return [b'Error 405: Method Not Allowed']


def not_found(start_response):
    """Called if Url not found."""
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b'Error 404: Not Found']


def redirect(start_response, target):
    """Called to do a redirect"""
    start_response('302 Found', [('Location', target)])
    return []


index_page_template = """<!DOCTYPE html>
<html>
<head>
    <title>Pyro HTTP gateway</title>
    <style type="text/css">
    table, th, td {{border: 1px solid grey; padding: 3px;}}
    table {{border-collapse: collapse;}}
    pre {{border: 1px dotted grey; padding: 1ex; margin: 1ex; white-space: pre-wrap;}}
    </style>
</head>
<body>
    <script src="//code.jquery.com/jquery-2.1.3.min.js"></script>
    <script>
    "use strict";
    function pyro_call(name, method, params) {{
        $.ajax({{
            url: name+"/"+method,
            type: "GET",
            data: params,
            dataType: "json",
            beforeSend: function(xhr, settings) {{
                $("#pyro_call").text(settings.type+" "+settings.url);
            }},
            error: function(xhr, status, error) {{
                var errormessage = "ERROR: "+xhr.status+" "+error+" \\n"+xhr.responseText;
                $("#pyro_response").text(errormessage);
            }},
            success: function(data) {{
                $("#pyro_response").text(JSON.stringify(data, null, 4));
            }}
        }});
    }}
    </script>
<img src="http://pythonhosted.org/Pyro4/_static/pyro.png" align="left">
<h1>Pyro HTTP gateway</h1>
<p>Use REST API to talk with JSON to Pyro objects.</p>
<p><em>Note: performance isn't maxed; it currently does a name lookup and uses a new Pyro proxy for each request.</em></p>
<h2>Currently exposed contents of name server (limited to 10 entries, prefix='{prefix}'):</h2>
{name_server_contents_list}
<p>Name server examples: (these examples are working if you expose the Pyro.NameServer object)</p>
<ul>
<li><a href="Pyro.NameServer/$meta" onclick="pyro_call('Pyro.NameServer','$meta'); return false;">Pyro.NameServer/$meta</a> -- gives meta info of the name server (methods)</li>
<li><a href="Pyro.NameServer/list" onclick="pyro_call('Pyro.NameServer','list'); return false;">Pyro.NameServer/list</a> -- lists the contents of the name server</li>
<li><a href="Pyro.NameServer/list?prefix=test." onclick="pyro_call('Pyro.NameServer','list', {{'prefix':'test.'}}); return false;">Pyro.NameServer/list?prefix=test.</a> -- lists the contents of the name server starting with 'test.'</li>
<li><a href="Pyro.NameServer/lookup?name=Pyro.NameServer" onclick="pyro_call('Pyro.NameServer','lookup', {{'name':'Pyro.NameServer'}}); return false;">Pyro.NameServer/lookup?name=Pyro.NameServer</a> -- perform lookup method of the name server</li>
<li><a href="Pyro.NameServer/lookup?name=test.echoserver" onclick="pyro_call('Pyro.NameServer','lookup', {{'name':'test.echoserver'}}); return false;">Pyro.NameServer/lookup?name=test.echoserver</a> -- perform lookup method of the echo server</li>
</ul>
<p>Echoserver examples: (these examples are working if you expose the test.echoserver object)</p>
<ul>
<li><a href="test.echoserver/error" onclick="pyro_call('test.echoserver','error'); return false;">test.echoserver/error</a> -- perform error call on echoserver</li>
<li><a href="test.echoserver/echo?message=Hi there, browser script!" onclick="pyro_call('test.echoserver','echo', {{'message':'Hi there, browser script!'}}); return false;">test.echoserver/echo?message=Hi there, browser script!</a> -- perform echo call on echoserver</li>
</ul>
<h2>Pyro response data (via Ajax):</h2>
Call: <pre id="pyro_call"> &nbsp; </pre>
Response: <pre id="pyro_response"> &nbsp; </pre>
<p>Pyro version: {pyro_version} &mdash; &copy; Irmen de Jong</p>
</body>
</html>
"""


def process_pyro_request(environ, path, parameters, start_response):
    nameserver = get_nameserver(hmac=pyro_app.hmac_key)
    if not path:
        start_response('200 OK', [('Content-Type', 'text/html')])
        nslist = ["<table><tr><th>Name</th><th>methods</th><th>attributes (zero-param methods)</th></tr>"]
        names = sorted(list(nameserver.list(prefix=pyro_app.ns_prefix).keys())[:10])
        with Pyro4.batch(nameserver) as nsbatch:
            for name in names:
                nsbatch.lookup(name)
            for name, uri in zip(names, nsbatch()):
                attributes = "-"
                try:
                    with Pyro4.Proxy(uri) as proxy:
                        proxy._pyroHmacKey = pyro_app.hmac_key
                        proxy._pyroBind()
                        methods = " &nbsp; ".join(proxy._pyroMethods) or "-"
                        attributes = ["<a href=\"{name}/{attribute}\" onclick=\"pyro_call('{name}','{attribute}'); return false;\">{attribute}</a>"
                                      .format(name=name, attribute=attribute) for attribute in proxy._pyroAttrs]
                        attributes = " &nbsp; ".join(attributes) or "-"
                except Pyro4.errors.PyroError as x:
                    methods = "??error:%s??" % str(x)
                nslist.append("<tr><td><a href=\"{name}/$meta\" onclick=\"pyro_call('{name}','$meta'); return false;\">{name}</a></td><td>{methods}</td><td>{attributes}</td></tr>"
                              .format(name=name, methods=methods, attributes=attributes))
        nslist.append("</table>")
        index_page = index_page_template.format(prefix=pyro_app.ns_prefix,
                                                name_server_contents_list="".join(nslist),
                                                pyro_version=Pyro4.constants.VERSION)
        return [index_page.encode("utf-8")]
    matches = re.match(r"(.+)/(.+)", path)
    if not matches:
        return not_found(start_response)
    object_name, method = matches.groups()
    if pyro_app.ns_prefix and not object_name.startswith(pyro_app.ns_prefix):
        start_response('401 Unauthorized', [('Content-Type', 'text/plain')])
        return [b"401 Unauthorized - access to the requested object has been denied"]
    try:
        uri = nameserver.lookup(object_name)
        with Pyro4.Proxy(uri) as proxy:
            proxy._pyroHmacKey = pyro_app.hmac_key
            proxy._pyroGetMetadata()
            if method == "$meta":
                result = {"methods": tuple(proxy._pyroMethods), "attributes": tuple(proxy._pyroAttrs)}
                reply = json.dumps(result).encode("utf-8")
                start_response('200 OK', [('Content-Type', 'application/json; charset=utf-8')])
                return [reply]
            else:
                proxy._pyroRawWireResponse = True   # we want to access the raw response json
                if method in proxy._pyroAttrs:
                    # retrieve the attribute
                    assert not parameters, "attribute lookup can't have query parameters"
                    msg = getattr(proxy, method)
                else:
                    # call the remote method
                    msg = getattr(proxy, method)(**parameters)
                if msg is None:
                    # was a oneway call, no response available
                    start_response('200 OK', [('Content-Type', 'application/json; charset=utf-8')])
                    return [json.dumps(None)]
                elif msg.flags & Pyro4.message.FLAGS_EXCEPTION:
                    # got an exception response so send a 500 status
                    start_response('500 Internal Server Error', [('Content-Type', 'application/json; charset=utf-8')])
                    return [msg.data]
                else:
                    # normal response
                    start_response('200 OK', [('Content-Type', 'application/json; charset=utf-8')])
                    return [msg.data]
    except Exception as x:
        import traceback
        stderr = environ["wsgi.errors"]
        print("ERROR handling {0} with params {1}:".format(path, parameters), file=stderr)
        traceback.print_exc(file=stderr)
        start_response('500 Internal Server Error', [('Content-Type', 'application/json; charset=utf-8')])
        reply = json.dumps(Pyro4.util.SerializerBase.class_to_dict(x)).encode("utf-8")
        return [reply]


def pyro_app(environ, start_response):
    """
    The WSGI app function that is used to process the requests.
    You can stick this into a wsgi server of your choice, or use the main() method
    to use the default wsgiref server.
    """
    Pyro4.config.SERIALIZER = "json"     # we only talk json through the http proxy
    method = environ.get("REQUEST_METHOD")
    path = environ.get('PATH_INFO', '').lstrip('/')
    if not path:
        return redirect(start_response, "/pyro/")
    if path.startswith("pyro/"):
        if method in ("GET", "POST"):
            parameters = singlyfy_parameters(cgi.parse(environ['wsgi.input'], environ))
            return process_pyro_request(environ, path[5:], parameters, start_response)
        else:
            return invalid_request(start_response)
    return not_found(start_response)


def singlyfy_parameters(parameters):
    """
    Makes a cgi-parsed parameter dictionary into a dict where the values that
    are just a list of a single value, are convered to just that single value.
    """
    for key, value in parameters.items():
        if isinstance(value, (list, tuple)) and len(value) == 1:
            parameters[key] = value[0]
    return parameters


pyro_app.ns_prefix = "Pyro4."
pyro_app.hmac_key = None


def main(args=None):
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-H", "--host", default="localhost", help="hostname to bind server on (default=%default)")
    parser.add_option("-p", "--port", type="int", default=8080, help="port to bind server on (default=%default)")
    parser.add_option("-f", "--prefix", default="Pyro.", help="the prefix of object names to expose (default=%default)")
    parser.add_option("-k", "--pyrokey", help="the HMAC key to use to connect with Pyro")
    # @todo could use some form of API key/hmac for the http requests...
    options, args = parser.parse_args(args)

    pyro_app.hmac_key = (options.pyrokey or "").encode("utf-8")
    pyro_app.ns_prefix = options.prefix
    if pyro_app.ns_prefix:
        print("Exposing objects with name prefix: ", pyro_app.ns_prefix)
    else:
        print("Warning: exposing all objects (no prefix set)")
    print("Connected to name server at: ", get_nameserver(hmac=pyro_app.hmac_key)._pyroUri)
    server = make_server(options.host, options.port, pyro_app)
    print("Pyro HTTP gateway running on http://{0}:{1}/pyro/".format(*server.socket.getsockname()))
    server.serve_forever()
    server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
