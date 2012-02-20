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
    from flask import Flask, render_template, request, make_response, Markup, g
except:
    raise Exception("Flask not found - install with 'easy_install flask'")

import rdflib
import rdfextras
import sys
import traceback

import mimeutils

endpoint = Flask(__name__)

endpoint.jinja_env.globals["rdflib_version"]=rdflib.__version__
endpoint.jinja_env.globals["rdfextras_version"]=rdfextras.__version__
endpoint.jinja_env.globals["python_version"]="%d.%d.%d"%(sys.version_info[0], sys.version_info[1], sys.version_info[2])


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


@endpoint.route("/")
def index():
    return render_template("index.html")

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
    from rdfextras.utils.cmdlineutils import main as cmdmain
    cmdmain(_main)

if __name__=='__main__':
    main()
