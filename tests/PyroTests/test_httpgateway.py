"""
Tests for the http gateway.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import json
from wsgiref.util import setup_testing_defaults
import io
import unittest
import Pyro4
import Pyro4.utils.httpgateway
import Pyro4.errors
import Pyro4.core
from Pyro4.naming import NameServer


# a bit of hackery to avoid having to launch a live name server
def get_nameserver_dummy(hmac=None):
    class NameServerDummyProxy(NameServer):
        def __init__(self):
            super(NameServerDummyProxy, self).__init__()
            self.register("http.ObjectName", "PYRO:dummy12345@localhost:59999")
        def _pyroBatch(self):
            return self
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def __call__(self, *args, **kwargs):
            return ["Name1", "Name2", "Name3"]
    return NameServerDummyProxy()


class WSGITestBase(unittest.TestCase):
    """Base class for unit-tests. Provides up a simple interface to make requests
    as though they came through a wsgi interface from a user."""

    def setUp(self):
        """Set up a fresh testing environment before each test."""
        self.cookies = []

    def request(self, application, url, query_string="", post_data=b""):
        """Hand a request to the application as if sent by a client.
        @param application: The callable wsgi application to test.
        @param url: The URL to make the request against.
        @param query_string: Url parameters.
        @param post_data: bytes to post."""
        self.response_started = False
        method = 'POST' if post_data else 'GET'
        temp = io.BytesIO(post_data)
        environ = {
            'PATH_INFO': url,
            'REQUEST_METHOD': method,
            'CONTENT_LENGTH': len(post_data),
            'QUERY_STRING': query_string,
            'wsgi.input': temp,
        }
        if method == "POST":
            environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        setup_testing_defaults(environ)
        if self.cookies:
            environ['HTTP_COOKIE'] = ';'.join(self.cookies)
        response = b''
        for ret in application(environ, self._start_response):
            assert self.response_started
            response += ret
        temp.close()
        return response

    def _start_response(self, status, headers):
        """A callback passed into the application, to simulate a wsgi
        environment.

        @param status: The response status of the application ("200", "404", etc)
        @param headers: Any headers to begin the response with.
        """
        assert not self.response_started
        self.response_started = True
        self.status = status
        self.headers = headers
        for header in headers:
            # Parse out any cookies and save them to send with later requests.
            if header[0] == 'Set-Cookie':
                var = header[1].split(';', 1)
                if len(var) > 1 and var[1][0:9] == ' Max-Age=':
                    if int(var[1][9:]) > 0:
                        # An approximation, since our cookies never expire unless
                        # explicitly deleted (by setting Max-Age=0).
                        self.cookies.append(var[0])
                    else:
                        index = self.cookies.index(var[0])
                        self.cookies.pop(index)

    def new_session(self):
        """Start a new session (or pretend to be a different user) by deleting
        all current cookies."""
        self.cookies = []


class TestHttpGateway(WSGITestBase):
    def setUp(self):
        super(TestHttpGateway, self).setUp()
        self.old_get_ns = Pyro4.utils.httpgateway.get_nameserver
        Pyro4.utils.httpgateway.get_nameserver = get_nameserver_dummy
        Pyro4.config.COMMTIMEOUT = 0.3

    def tearDown(self):
        super(TestHttpGateway, self).tearDown()
        Pyro4.utils.httpgateway.get_nameserver = self.old_get_ns
        Pyro4.config.COMMTIMEOUT = 0.0

    def testParams(self):
        multiparams = {
            "first": [1],
            "second": [1, 2, 3],
            "third": 42
        }
        checkparams = {
            "first": 1,
            "second": [1, 2, 3],
            "third": 42
        }
        params = Pyro4.utils.httpgateway.singlyfy_parameters(multiparams)
        self.assertEqual(checkparams, params)
        params = Pyro4.utils.httpgateway.singlyfy_parameters(multiparams)
        self.assertEqual(checkparams, params)

    def testRedirect(self):
        result = self.request(Pyro4.utils.httpgateway.pyro_app, "/")
        self.assertEqual("302 Found", self.status)
        self.assertEqual([('Location', '/pyro/')], self.headers)
        self.assertEqual(b"", result)

    def testWebpage(self):
        result = self.request(Pyro4.utils.httpgateway.pyro_app, "/pyro/")
        self.assertEqual("200 OK", self.status)
        self.assertTrue(result.startswith(b"<!DOCTYPE html>"))
        self.assertTrue(len(result) > 1000)

    def testMethodCallGET(self):
        result = self.request(Pyro4.utils.httpgateway.pyro_app, "/pyro/http.ObjectName/method", query_string="param=42&param2=hello")
        # the call will result in a communication error because the dummy uri points to something that is not available
        self.assertEqual("500 Internal Server Error", self.status)
        j = json.loads(result.decode("utf-8"))
        self.assertTrue(j["__exception__"])
        self.assertEqual("Pyro4.errors.CommunicationError", j["__class__"])

    def testMethodCallPOST(self):
        result = self.request(Pyro4.utils.httpgateway.pyro_app, "/pyro/http.ObjectName/method", post_data=b"param=42&param2=hello")
        # the call will result in a communication error because the dummy uri points to something that is not available
        self.assertEqual("500 Internal Server Error", self.status)
        j = json.loads(result.decode("utf-8"))
        self.assertTrue(j["__exception__"])
        self.assertEqual("Pyro4.errors.CommunicationError", j["__class__"])

    def testNameDeniedPattern(self):
        result = self.request(Pyro4.utils.httpgateway.pyro_app, "/pyro/Pyro4.NameServer/method")
        # the call will result in a access denied error because the uri points to a non-exposed name
        self.assertEqual("403 Forbidden", self.status)

    def testNameDeniedNotRegistered(self):
        result = self.request(Pyro4.utils.httpgateway.pyro_app, "/pyro/http.NotRegisteredName/method")
        # the call will result in a communication error because the dummy uri points to something that is not registered
        self.assertEqual("500 Internal Server Error", self.status)
        j = json.loads(result.decode("utf-8"))
        self.assertTrue(j["__exception__"])
        self.assertEqual("Pyro4.errors.NamingError", j["__class__"])

    def testExposedPattern(self):
        self.assertEqual(r"http\.", Pyro4.utils.httpgateway.pyro_app.ns_regex)


if __name__ == "__main__":
    unittest.main()
