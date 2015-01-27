"""
HTTP gateway: connects the web browser's world of javascript+http and Pyro.
Creates a HTTP server that essentially is a proxy for the Pyro objects behind it.
It exposes the Pyro objects through a HTTP REST interface and uses the JSON serializer,
so that you can immediately process the response data in the browser.

You can start this module as a script from the command line, to easily get a
http gateway server running:

  :command:`python -m Pyro4.utils.httpgateway`
  or simply: :command:`pyro4-httpgateway`

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import print_function
import sys
import json
import re
from wsgiref.simple_server import make_server
try:
    from urlparse import parse_qsl
except ImportError:
    from urllib.parse import parse_qsl
import Pyro4
import Pyro4.errors
import Pyro4.message
import Pyro4.util
import Pyro4.constants


__all__ = ["pyro_app", "make_server"]

_nameserver = None
def get_nameserver():
    global _nameserver
    if not _nameserver:
        _nameserver = Pyro4.locateNS()
    try:
        _nameserver.ping()
        return _nameserver
    except Pyro4.errors.ConnectionClosedError:
        _nameserver = None
        print("Connection with nameserver lost, reconnecting...")
        return get_nameserver()


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


index_page_template = """<html>
<head>
    <title>Pyro HTTP gateway</title>
    <script>
    "use strict";
    function pyro_call(name, method, params) {{
        console.debug("Pyro call: name="+name+" method="+method+" params="+params);
        var url = buildUrl(name+"/"+method, params);
        var x = new XMLHttpRequest();
        x.onload = function () {{
                var baseuri = document.baseURI;
                if(!baseuri) {{
                    baseuri = document.location.href;        // IE fallback
                }}
                document.getElementById("pyro_call").innerHTML = baseuri+url;
                if(this.readyState==4 && this.status==200) {{
                    var json = JSON.parse(this.response);
                    console.debug(json);
                    document.getElementById("pyro_response").innerHTML = JSON.stringify(json, null, 4);
                }} else {{
                    var errormessage = "ERROR: "+this.status+" "+this.statusText+" \\n "+this.responseText;
                    console.error(errormessage);
                    document.getElementById("pyro_response").innerHTML = errormessage;
                }}
            }}  ;
        x.open("get", url, true);
        x.send();
    }}

    function buildUrl(url, parameters) {{
      var qs = "";
      for(var key in parameters) {{
        var value = parameters[key];
        qs += encodeURIComponent(key) + "=" + encodeURIComponent(value) + "&";
      }}
      if (qs.length > 0) {{
        qs = qs.substring(0, qs.length-1); //chop off last "&"
        url = url + "?" + qs;
      }}
      return url;
    }}
    </script>
</head>
<body>
<img src="http://pythonhosted.org/Pyro4/_static/pyro.png" align="left">
<h1>Pyro HTTP gateway</h1>
<p>Use REST API to talk with JSON to Pyro objects.</p>
<p><em>Note: performance isn't very high; it currently uses a new Pyro proxy for each request.</em></p>
<p>Examples: (these examples are working if you expose the Pyro.NameServer object)</p>
<ul>
<li><a href="Pyro.NameServer/$meta" onclick="pyro_call('Pyro.NameServer','$meta'); return false;">Pyro.NameServer/$meta</a> -- gives meta info of the name server (methods)</li>
<li><a href="Pyro.NameServer/list" onclick="pyro_call('Pyro.NameServer','list'); return false;">Pyro.NameServer/list</a> -- lists the contents of the name server</li>
<li><a href="Pyro.NameServer/list?prefix=test." onclick="pyro_call('Pyro.NameServer','list', {{'prefix':'test.'}}); return false;">Pyro.NameServer/list?prefix=test.</a> -- lists the contents of the name server starting with 'test.'</li>
<li><a href="Pyro.NameServer/lookup?name=Pyro.NameServer" onclick="pyro_call('Pyro.NameServer','lookup', {{'name':'Pyro.NameServer'}}); return false;">Pyro.NameServer/lookup?name=Pyro.NameServer</a> -- perform lookup method of the name server</li>
</ul>
<h2>Currently exposed contents of name server (limited to 10 entries, prefix='{prefix}'):</h2>
{name_server_contents_list}
<h2>Pyro response data (via Ajax):</h2>
Call: <pre id="pyro_call" style="border: dotted 1px; padding: 1ex; margin: 1ex;"> &nbsp; </pre>
Response: <pre id="pyro_response" style="border: dotted 1px; padding: 1ex; margin: 1ex;"> &nbsp; </pre>
<p>Pyro version: {pyro_version}</p>
</body>
</html>
"""


def process_pyro_request(environ, path, queryparams, start_response):
    nameserver = get_nameserver()
    if not path:
        start_response('200 OK', [('Content-Type', 'text/html')])
        nslist = ["<table border=\"1\"><tr><th>Name</th><th>methods</th><th>attributes (zero-param methods)</th></tr>"]
        names = sorted(list(nameserver.list(prefix=pyro_app.ns_prefix).keys())[:10])
        with Pyro4.batch(nameserver) as nsbatch:
            for name in names:
                nsbatch.lookup(name)
            for name, uri in zip(names, nsbatch()):
                attributes = "-"
                try:
                    with Pyro4.Proxy(uri) as proxy:
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
                    assert not queryparams, "attribute lookup can't have query parameters"
                    msg = getattr(proxy, method)
                else:
                    # call the remote method
                    msg = getattr(proxy, method)(**queryparams)
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
        print("ERROR handling {0} with params {1}:".format(path, queryparams), file=stderr)
        traceback.print_exc(file=stderr)
        start_response('500 Internal Server Error', [('Content-Type', 'application/json; charset=utf-8')])
        reply = json.dumps(Pyro4.util.SerializerBase.class_to_dict(x)).encode("utf-8")
        return [reply]


def pyro_app(environ, start_response):
    Pyro4.config.SERIALIZER = "json"     # we only talk json through the http proxy
    method = environ.get("REQUEST_METHOD")
    if method != "GET":
        return invalid_request(start_response)
    path = environ.get('PATH_INFO', '').lstrip('/')
    if not path:
        return redirect(start_response, "/pyro/")
    if path.startswith("pyro/"):
        qs = dict(parse_qsl(environ["QUERY_STRING"]))
        return process_pyro_request(environ, path[5:], qs, start_response)
    return not_found(start_response)


pyro_app.ns_prefix = "Pyro4."
pyro_app.hmac_key = None        # XXX use this!


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
    print("Connected to name server at: ", get_nameserver()._pyroUri)
    server = make_server(options.host, options.port, pyro_app)
    print("Pyro HTTP gateway running on {0}:{1}".format(*server.socket.getsockname()))
    server.serve_forever()
    server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
