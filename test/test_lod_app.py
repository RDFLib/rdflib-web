import threading
import time
from http.client import HTTPConnection

import rdflib
import rdflib_web.lod as lod
from rdflib_web.bookdb import bookdb



def test_lod_app():

    def req(u, ok=200):
        h.request('GET', u)
        r = h.getresponse()
        assert r.status == ok, 'Request for %s did not succeed, status code: %d'%(u,r.status)

    app = lod.get(bookdb)
    t=threading.Thread(target=lambda : app.run(port=57234))
    t.daemon=True
    t.start()

    time.sleep(2) # give the web-app time to start

    h = HTTPConnection('localhost', 57234)

    req('/')
    req('/instances')
    # req('/resource/Book/book1') # httplib does not follow redirects
    req('/page/Book/book1')
    req('/data/Book/book1.nt')
    req('/rdfgraph/Book/book1.png')
    req('/page/Class/Class')
    req('/page/Class/Property')
    req('/picked/')
    req('/download/nt')

    req('/pick?uri=http%3A%2F%2Fexample.org%2Fbook%2Fbook1', 302)
    req('/picked/download/nt')
    req('/picked/rdfgraph/png')
