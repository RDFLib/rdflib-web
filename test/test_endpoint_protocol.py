import unittest
import logging
import subprocess
import threading
import os
import re
import urllib.request, urllib.parse, urllib.error
import http.client
import rdflib
import rdflib.compare
import rdflib_web.endpoint
import fileinput

class _TestSyntaxError(Exception):
    def __init__(self, filename, lineno, error):
        super(Exception, self).__init__(
                "Error in test case %s at line %s: %s" % (filename, lineno, error)
                )


class Parser():
    r_title = re.compile(r"^#(?!#)\s*(.*)")
    r_test = re.compile("^##(?!#)\s*(.*)")
    r_request = re.compile("^###\s*request", re.I)
    r_response = re.compile("^###\s*response", re.I)
    r_empty = re.compile("^\s*$")
    r_indent = re.compile("^(\s+)")

    def error(self, message):
        raise _TestSyntaxError(self.f.filename(), self.f.filelineno(), message)

    def parse(self, filename):
        self.f = fileinput.input((filename,))
        self.tests = []
        self.state = self.title

        for l in self.f:
            self.state(l)

        if not self.tests:
            self.error("No tests found")
        elif not self.tests[-1]['request']:
            self.error("Expected '### Request'")
        elif not self.tests[-1]['response']:
            self.error("Expected '### Response'")

        return self.title, self.tests

    def title(self, l):
        m = self.r_title.match(l)
        if m:
            self.title = m.group(1)
            self.state = self.test
        else:
            self.error("First line must be a title")

    def test(self, l):
        if l.startswith('#'):
            m = self.r_test.match(l)
            if not m:
                self.error("Expected '##'")
            test = {'name': m.group(1), 'request': "", 'response': ""}
            self.tests.append(test)
            self.state = self.request

    def request(self, l):
        if l.startswith('#'):
            m = self.r_request.match(l)
            if not m:
                self.error("Expected '### Request'")
            self.state = lambda l: self.block(l, 'request', self.response)

    def response(self, l):
        if l.startswith('#'):
            m = self.r_response.match(l)
            if not m:
                self.error("Expected '### Response'")
            self.state = lambda l: self.block(l, 'response', self.test)

    def block(self, l, field, next_state):
        if l.startswith('#'):
            self.error("Expected code block")
        elif l.rstrip() == '```':
            self.state = lambda l: self.consume_block(l, field, next_state)

    def consume_block(self, l, field, next_state):
        if l.rstrip().startswith('```'):
            self.state = next_state
        else:
            self.tests[-1][field] += l

def _test_function_factory(filename):
    def test_function(self):
        self.from_file(filename)
    return test_function

def _discover_tests(directory):
    # Name of this function begins with an underscore because
    # otherwise unittest thinks it is a test.
    tests = [name for name in os.listdir(directory) if name.startswith("test_")]
    def decorator(cls):
        for t in tests:
            test_function = _test_function_factory("%s/%s" % (directory, t))
            setattr(cls, t.split('.')[0], test_function)
        return cls
    return decorator

@_discover_tests("test/endpoint_protocol")
class TestEndpointProtocol(unittest.TestCase): 
    port = 57234
    host = 'localhost'
    graphstore_path = '/graph-store'.format(host, port)
    tests = []
    connection = None
    app = None

    # Blarg! Using shared fixture, because I don't know how to stop a
    # running flask app in a thread. Running the app in a
    # subprocess or using app.test_client() should be considered.
    @classmethod
    def setUpClass(cls):
        ds=rdflib.Dataset()
        cls.app=rdflib_web.endpoint.get(ds)
        t=threading.Thread(target=lambda : cls.app.run(port=cls.port))
        t.daemon=True
        t.start()
        import time
        time.sleep(1)
        cls.connection = http.client.HTTPConnection(cls.host, cls.port, timeout=5)

    def replace_constants(self, s):
        s = s.replace('$GRAPHSTORE$', self.graphstore_path)
        return s.replace('$HOST$', self.host+':'+str(self.port))

    def replace_variables(self, s):
        if self.newpath:
            # The host part must be removed, because it should not
            # turn up in the first request line (flask chokes at it,
            # although HTTP explicitely allows it).
            newpath = re.sub(r"^http://[^:]+:[^/]+", '', self.newpath)
            s = s.replace('$NEWPATH$', newpath)
        else:
            s = s.replace('$NEWPATH$', 'NEW_PATH_MISSING')
        return s

    def readProtocol(self, data):
        lines = iter(data.split('\n'))
        firstline = next(lines)
        headers = dict()
        for l in lines:
            if l.isspace() or not l: break
            k, v = l.split(': ', 1)
            if k.lower() not in ['content-length','host']:
                headers[k.lower()] = v
        body = '\n'.join(lines)
        return firstline, headers, body

    # The compare functions return a list of strings, each describing
    # a difference. If the list is empty, no difference has been
    # found.
    def compareStatus(self, expected, received):
        if not expected == received:
            return ["Status is {}, but should be {}".format(received, expected)]
        else:
            return []

    def compareHeaders(self, expected, received):
        result = []
        for k, v in list(expected.items()):
            if not k in received:
                result.append("Header {} not present in response".format(k))
            else:
                # Create a regular expression matching the header and
                # reading out $NEWPATH$
                v_re = re.sub(r'([^\w\s])', r'\\\1', v)
                v_re = re.sub(r'\\\$NEWPATH\\\$', r'(.*)', v_re) # $NEWPATH$ escaped by previous line
                v_re = '^' + v_re + '$'
                m = re.match(v_re, received[k])
                if m and m.groups() and m.group(1):
                    self.newpath = m.group(1)
                elif not m:
                    result.append("Header {} has value {} instead of {}".format(k, received[k], v))
        return result

    def compareBody(self, expected, received, content_type):
        mimetype = content_type.split(';', 1)[0]
        if mimetype == 'text/turtle':
            g_expected = rdflib.compare.IsomorphicGraph()
            g_expected.parse(data=expected, format=mimetype)
            g_received = rdflib.compare.IsomorphicGraph()
            g_received.parse(data=received, format=mimetype)
            _, in_expected, in_received = rdflib.compare.graph_diff(g_expected, g_received)
            if in_expected or in_received:
                msg = "Triples expected but not returned:\n"
                for t in sorted(in_expected):
                    msg += "    " + " ".join([n.n3() for n in t]) + " .\n"
                msg += "Triples returned but not expected:\n"
                for t in sorted(in_received):
                    msg+="    " + " ".join([n.n3() for n in t]) + " .\n"
                return [msg]
        elif not expected == received:
            return ["Body is:\n{}but should be\n{}".format(received, expected)]
        return []

    def runtest(self, name, request, response):
        logging.info("Prepairing test {}".format(name))
        request = self.replace_constants(request)
        request = self.replace_variables(request)
        response = self.replace_constants(response)
        # Read request into data structure
        firstline, request_headers, request_body = self.readProtocol(request)
        match = re.match("^(\w+) ([^ ]+)", firstline)
        request_method = match.group(1)
        request_url = match.group(2)
        # Read response into data structure
        firstline, expected_headers, expected_body = self.readProtocol(response)
        expected_status = int(firstline.split(' ', 1)[0])

        logging.info("Running test {}".format(name))
        self.connection.request(request_method, request_url, request_body, request_headers)
        # Get response
        response = self.connection.getresponse();
        response_status = response.status;
        response_headers = {k.lower(): v for k, v in response.getheaders()}
        response_body = response.read()
        # Collect errors
        errors = []
        # Compare response status
        errors += self.compareStatus(expected_status, response_status)
        # Compare response headers
        errors += self.compareHeaders(expected_headers, response_headers)
        # Compare response body only on success
        if response_status < 400:
            errors += self.compareBody(expected_body, response_body, response_headers.get('content-type'))
        # Report
        if errors:
            logging.info("=== FAILURE === Test {} failed: ".format(name))
            logging.info("\n".join(errors))
            return False
        else:
            logging.info("Test {} passed".format(name))
            return True

    def from_file(self, filename):
        parser = Parser()
        title, tests = parser.parse(filename)

        # Because of the shared fixture, mess with the endpoint's
        # internal in order to reset the dataset
        m = re.search(r"\[(.*)\]", title)
        initExpression = m.group(1) if m else "rdflib.Dataset()"
        logging.info("Initializing endpoint with `%s`" % initExpression)
        self.app.config["ds"] = eval(initExpression)
        if "generic" in self.app.config:
            self.app.config["generic"].ds = self.app.config["ds"]
        self.newpath = None

        failed_tests = [t['name'] for t in tests if not self.runtest(**t)]

        if failed_tests:
            self.fail("These tests failed: {}\nNOTE: Some tests may have failed because they depend on the success of preceding ones!".format(", ".join(failed_tests)))

