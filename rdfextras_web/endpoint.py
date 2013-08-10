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

from rdfextras_web import htmlresults
from rdfextras_web import __version__
from rdfextras_web import generic_endpoint

endpoint = Flask(__name__)

endpoint.jinja_env.globals["rdflib_version"]=rdflib.__version__
endpoint.jinja_env.globals["rdfextras_web_version"]=__version__
endpoint.jinja_env.globals["python_version"]="%d.%d.%d"%(sys.version_info[0], sys.version_info[1], sys.version_info[2])

DEFAULT = generic_endpoint.GenericEndpoint.DEFAULT

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

def graph_store_do(graph_identifier):
    method = request.method
    mimetype = request.mimetype
    args = request.args
    if mimetype == "multipart/form-data":
        body = []
        force_mimetype = args.get('mimetype')
        for _, data_file in request.files.items():
            data = data_file.read()
            mt = force_mimetype or data_file.mimetype or rdflib.guess_format(data_file.filename)
            body.append({'data': data, 'mimetype': mt})
    else:
        body = request.data

    result = g.generic.graph_store(
        method=method, graph_identifier=graph_identifier, args=args,
        body=body, mimetype=mimetype,
        accept_header=request.headers.get("Accept")
    )
    code, headers, body = result

    response = make_response(body or '', code)
    for k, v in headers.items():
        response.headers[k] = v
    return response


@endpoint.route("/graph-store", methods=["GET", "PUT", "POST", "DELETE"]) # HEAD is done by flask via GET
def graph_store_indirect():
    return graph_store_do(None)

@endpoint.route("/graph-store/<path:path>", methods=["GET", "POST", "PUT", "DELETE"]) # HEAD is done by flask via GET
def graph_store_direct(path):
    graph_identifier = rdflib.URIRef(request.url)
    return graph_store_do(graph_identifier)


@endpoint.route("/")
def index():
    return render_template("index.html")

@endpoint.before_first_request    
def __register_namespaces(): 
    for p,ns in endpoint.config["ds"].namespaces():
        htmlresults.nm.bind(p,ns,override=True)

@endpoint.before_first_request    
def __create_generic_endpoint():
    endpoint.config["generic"]=generic_endpoint.GenericEndpoint(
        ds=endpoint.config["ds"],
        coin_url=lambda: url_for("graph_store_direct", path=str(rdflib.BNode()), _external=True)
    )

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


def serve(ds,debug=False):
    """Serve the given dataset on localhost with the LOD App"""

    a=get(ds)
    a.run(debug=debug)
    return a

@endpoint.before_request
def _set_generic():
    """ This sets the g.generic if we are using a static graph
    set in the configuration"""
    g.generic = endpoint.config["generic"]

def get(ds):
    """
    Get the LOD Flask App setup to serve the given dataset
    """

    endpoint.config["ds"]=ds
    return endpoint


def _main(g, out, opts): 
    import rdflib    
    import sys
    
    serve(g, True)

def main(): 
    from rdflib.extras.cmdlineutils import main as cmdmain
    cmdmain(_main, stdin=False)

if __name__=='__main__':
    main()
