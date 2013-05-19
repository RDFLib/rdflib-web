#from nose.exc import SkipTest
#raise SkipTest("SPARQL store server test skipped")
import unittest
import threading
import rdflib
import rdfextras_web.endpoint


class TestSPARQLStore(unittest.TestCase): 
    def testSPARQLStore(self):
        g=rdflib.Graph(identifier='http://example.org/testgraph')

        data="""<http://example.org/book/book1> <http://purl.org/dc/elements/1.1/title> "SPARQL Tutorial" .
<http://example.org/book/b\xc3\xb6\xc3\xb6k8> <http://purl.org/dc/elements/1.1/title> "Moose bite can be very n\xc3\xb6sty."@se .
 
"""

        g.parse(data=data, format='n3')

        # # create our own SPARQL endpoint

        app=rdfextras_web.endpoint.get(g)
        t=threading.Thread(target=lambda : app.run(port=57234))
        t.daemon=True
        t.start()
        import time
        time.sleep(1)
        g2=rdflib.ConjunctiveGraph('SPARQLStore')
        g2.open("http://localhost:57234/sparql")
        b=rdflib.URIRef("http://example.org/book/book1")
        b2=rdflib.URIRef("http://example.org/book/b\xc3\xb6\xc3\xb6k8")
        DCtitle=rdflib.URIRef("http://purl.org/dc/elements/1.1/title")
        self.assertEqual(len(list(g2.triples((b,None,None)))), 1)
        self.assertEqual(list(g2.objects(b,DCtitle))[0], rdflib.Literal("SPARQL Tutorial"))

        self.assertEqual(list(g2.objects(b2,DCtitle))[0], list(g.objects(b2,DCtitle))[0])
        
