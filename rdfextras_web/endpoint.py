"""
This is a Flask web-app for a SPARQL Endpoint 
confirming to the SPARQL 1.0 Protocol.

The application can be started from commandline:

  python -m rdfextras_web.endpoint <RDF-file>

and the file will be served from http://localhost:5000

You can also start the server from your application by calling the :py:func:`serve` method
or get the application object yourself by called :py:func:`get` function

"""
try:
    from flask import Flask, render_template, request, make_response, Markup, g, url_for
except:
    raise Exception("Flask not found - install with 'easy_install flask'")

import rdflib

import sys
import time
import traceback

import mimeutils

from rdfextras_web import htmlresults
from rdfextras_web import __version__

endpoint = Flask(__name__)

endpoint.jinja_env.globals["rdflib_version"]=rdflib.__version__
endpoint.jinja_env.globals["rdfextras_web_version"]=__version__
endpoint.jinja_env.globals["python_version"]="%d.%d.%d"%(sys.version_info[0], sys.version_info[1], sys.version_info[2])

def content_negotiation(query_result=None):
    """Decides which format to use for serialization

    :argument:query_results: Must be set to the return value of
                             Graph.query. This is used to determine
                             the available serialization formats. If
                             None, a format Graph.serialize can
                             produce gets chosen.
    """
    # TODO: How to distungiush between query results that contain a
    # graph (DESCRIBE, CONSTRUCT) and one that contains rows?
    if query_result and query_result.graph is None:
        available = ['application/sparql-results+json', 'application/sparql-results+xml']
    else:
        available = ['application/rdf+xml', 'text/n3', 'text/turtle', 'application/n-triples']
    a = request.accept_mimetypes
    mimetype = a.best_match(available, default=available[0])
    charset = 'utf-8' if mimetype.startswith('text/') else None
    content_type = mimetype + ('; charset=' + charset if charset else '')
    return mimetype, charset, content_type

@endpoint.route("/sparql", methods=['GET', 'POST'])
def query():
    try: 
        q=request.values["query"]

        a=request.headers["Accept"]

        format="xml" # xml is default
        if mimeutils.HTML_MIME in a:
            format="html"
        if mimeutils.JSON_MIME in a: 
            format="json"

        # output parameter overrides header
        format=request.values.get("output", format) 

        mimetype=mimeutils.resultformat_to_mime(format)

        # force-accept parameter overrides mimetype
        mimetype=request.values.get("force-accept", mimetype)

        # pretty=None
        # if "force-accept" in request.values: 
        #     pretty=True

        # default-graph-uri

        results=g.graph.query(q).serialize(format=format)
        if format=='html':            
            response=make_response(render_template("results.html", results=Markup(unicode(results,"utf-8")), q=q))
        else:
            response=make_response(results)

        response.headers["Content-Type"]=mimetype
        return response
    except: 
        return "<pre>"+traceback.format_exc()+"</pre>", 400

def graph_store_do(graph_uri):
    if not graph_uri and not request.method == 'POST':
        return make_response("Missing URL query string parameter 'graph' or 'default'", 400)
    if request.method == 'PUT':
        if graph_uri in g.graph.graphs():
            existed = True
            g.graph.remove_graph(graph_uri)
        else:
            existed = False
        g.graph.parse(data=request.data, publicID=graph_uri, format=request.mimetype)
        response = make_response('', 204 if existed else 201)
    elif request.method == 'DELETE':
        if graph_uri in g.graph.graphs():
            g.graph.remove_graph(graph_uri)
            response = make_response('', 204)
        else:
            response = make_response('Graph %s not found' % graph_uri, 404)
    elif request.method == 'POST' and request.mimetype == "multipart/form-data":
        existed = graph_uri in g.graph.graphs()
        force_mimetype = request.args.get('mimetype')
        for _, data_file in request.files.items():
            data = data_file.read()
            mimetype = force_mimetype or data_file.mimetype or rdflib.guess_format(data_file.filename)
            g.graph.parse(data=data, publicID=graph_uri, format=mimetype)
        response = make_response('', 204 if existed else 201)
    elif request.method == 'POST':
        additional_headers = dict()
        if not graph_uri:
            # Coin a new identifier
            url = url_for("graph_store_direct_put", path=str(rdflib.BNode()), _external=True)
            graph_uri = rdflib.URIRef(url)
            additional_headers['location'] = url
        existed = graph_uri in g.graph.graphs()
        if request.mimetype == "multipart/form-data":
            force_mimetype = request.args.get('mimetype')
            for _, data_file in request.files.items():
                data = data_file.read()
                mimetype = force_mimetype or data_file.mimetype or rdflib.guess_format(data_file.filename)
                g.graph.parse(data=data, publicID=graph_uri, format=mimetype)
        else:
            g.graph.parse(data=request.data, publicID=graph_uri, format=request.mimetype)
        response = make_response('', 204 if existed else 201, additional_headers)
    else:
        if graph_uri in g.graph.graphs():
            format, _, content_type = content_negotiation()
            response = make_response(g.graph.graph(graph_uri).serialize(format=format))
            response.headers["Content-Type"] = content_type
        else:
            response = make_response('Graph %s not found' % graph_uri, 404)
    return response

@endpoint.route("/graph-store", methods=["GET", "PUT", "POST", "DELETE"]) # HEAD is done by flask via GET
def graph_store_indirect_get():
    
    graph_uri = request.values.get("graph", None)
    default = request.values.get("default", None)

    if 'default' in request.values:
        graph_uri = rdflib.Dataset.DEFAULT
    elif 'graph' in request.values:
        graph_uri = rdflib.URIRef(request.values['graph'])
    else:
        graph_uri = None

    return graph_store_do(graph_uri)

@endpoint.route("/graph-store/<path:path>", methods=["GET", "POST", "PUT", "DELETE"]) # HEAD is done by flask via GET
def graph_store_direct_put(path):
    graph_uri = rdflib.URIRef(request.url)

    return graph_store_do(graph_uri)


@endpoint.route("/")
def index():
    return render_template("index.html")

@endpoint.before_first_request    
def __register_namespaces(): 
    for p,ns in endpoint.config["graph"].namespaces():
        htmlresults.nm.bind(p,ns,override=True)

@endpoint.before_request
def __start(): 
    g.start=time.time()

@endpoint.after_request
def __end(response): 
    diff = time.time() - g.start
    if response.response and response.content_type.startswith("text/html") and response.status_code==200:
        response.response[0]=response.response[0].replace('__EXECUTION_TIME__', "%.3f"%diff)
        response.headers["Content-Length"]=len(response.response[0])
    return response


def serve(graph_,debug=False):
    """Serve the given graph on localhost with the LOD App"""

    a=get(graph_)
    a.run(debug=debug)
    return a

@endpoint.before_request
def _set_graph():
    """ This sets the g.graph if we are using a static graph
    set in the configuration"""
    if "graph" in endpoint.config and endpoint.config["graph"]!=None: 
        g.graph=endpoint.config["graph"]


def get(graph_):
    """
    Get the LOD Flask App setup to serve the given graph
    """

    endpoint.config["graph"]=graph_
    return endpoint


def _main(g, out, opts): 
    import rdflib    
    import sys
    if len(g)==0:
        import bookdb
        g=bookdb.bookdb
    
    serve(g, True)

def main(): 
    from rdflib.extras.cmdlineutils import main as cmdmain
    cmdmain(_main, stdin=False)

if __name__=='__main__':
    main()
