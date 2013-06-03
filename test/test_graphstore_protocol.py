import unittest
import logging
import subprocess
import threading
import os
import re
import urllib
import httplib
import rdflib
import rdflib.compare
import rdfextras_web.endpoint

from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint

class TestcaseParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.tests = []
        self.dest = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'h2' and 'id' in attrs:
            self.tests.append({'name': attrs['id']})
            self.dest = 'title'
        elif self.tests and tag=='pre':
            if self.tests[-1].get('request'):
                self.dest = 'response'
            else:
                self.dest = 'request'
    def handle_endtag(self, tag):
        if self.dest:
            t = self.tests[-1]
            t[self.dest] = t.get(self.dest, '').strip()
            self.dest = None
    def handle_data(self, data):
        if self.dest:
            t = self.tests[-1]
            t[self.dest] = t.get(self.dest, '') + data
    def handle_entityref(self, name):
        c = unichr(name2codepoint[name])
        self.handle_data(c)
    def handle_charref(self, name):
        if name.startswith('x'):
            c = unichr(int(name[1:], 16))
        else:
            c = unichr(int(name))
        self.handle_data(c)

class TestFailure(Exception):
    pass

class TestGraphStoreProtocol(unittest.TestCase): 
    port = 57234
    host = 'localhost'
    graphstore_path = '/graph-store'.format(host, port)
    tests = []

    def setUp(self):
        self.g=rdflib.Dataset()
        app=rdfextras_web.endpoint.get(self.g)
        t=threading.Thread(target=lambda : app.run(port=self.port))
        t.daemon=True
        t.start()
        import time
        time.sleep(1)
        self.connection = httplib.HTTPConnection(self.host, self.port, timeout=5)

        self.newpath = None

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

    def compareStatus(self, expected, received):
        if not expected == received:
            raise TestFailure("Status is {}, but should be {}".format(received, expected))

    def compareHeaders(self, expected, received):
        for k, v in expected.items():
            if not k in received:
                raise TestFailure("Header {} not present in response".format(k))
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
                    raise TestFailure("Header {} has value {} instead of {}".format(k, received[k], v))

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
                raise TestFailure(msg)
        elif not expected == received:
                raise TestFailure(
                    "Body is:\n{}but should be\n{}".format(received, expected)
                )

    def runtest(self, name, title, request, response):
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
        try:
            # Compare response status
            self.compareStatus(expected_status, response_status)
            # Compare response headers
            self.compareHeaders(expected_headers, response_headers)
            # Compare response body only on success
            if response_status < 400:
                self.compareBody(expected_body, response_body, response_headers.get('content-type'))
        except TestFailure as e:
            logging.info("=== FAILURE === Test {} failed: ".format(name))
            logging.info(e)
            return False
        logging.info("Test {} passed".format(name))
        return True
        
    def test_all(self):
        testpage = open("test/graphstore_protocol/tests.html").read()

        parser = TestcaseParser()
        parser.feed(testpage)
        parser.close()
        tests = parser.tests

        failed_tests = [t['name'] for t in tests if not self.runtest(**t)]

        if failed_tests:
            self.fail("These tests failed: {}\nNOTE: Some tests may have failed because they depend on the success of preceding ones!".format(", ".join(failed_tests)))

