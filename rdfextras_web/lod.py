"""
This is a Flask web-app for a simple Linked Open Data Web-app
it also includes a SPARQL 1.0 Endpoint

The application can be started from commandline:

  python -m rdfextras_web.lod <RDF-file>

and the file will be served from http://localhost:5000

You can also start the server from your application by calling the :py:func:`serve` method
or get the application object yourself by called :py:func:`get` function

The application creates local URIs based on the type of resources 
and servers content-negotiated HTML or serialised RDF from these.

"""
import re
import warnings
import urllib2
import collections
import subprocess
import codecs 
import os.path
import itertools

import rdflib

from flask import render_template, request, make_response, redirect, url_for, g, Response, abort, session

from werkzeug.routing import BaseConverter
from werkzeug.urls import url_quote


from rdfextras_web.endpoint import endpoint as lod
from rdfextras_web import mimeutils
from rdfextras.tools import rdf2dot, rdfs2dot
from rdfextras.utils import graphutils
from rdfextras_web.htmlresults import term_to_string


POSSIBLE_DOT=["/usr/bin/dot", "/usr/local/bin/dot", "/opt/local/bin/dot"]
for x in POSSIBLE_DOT: 
    if os.path.exists(x):         
        DOT=x
        break

GRAPH_TYPES={"png": "image/png", 
             "svg": "image/svg+xml", 
             "dot": "text/x-graphviz", 
             "pdf": "application/pdf" }


class RDFUrlConverter(BaseConverter):
    def __init__(self, url_map):
        BaseConverter.__init__(self,url_map)
        self.regex="[^/].*?"
    def to_url(self, value):
        return url_quote(value, self.map.charset, safe=":")

lod.url_map.converters['rdf'] = RDFUrlConverter
lod.jinja_env.filters["term_to_string"]=term_to_string

LABEL_PROPERTIES=[rdflib.RDFS.label, 
                  rdflib.URIRef("http://purl.org/dc/elements/1.1/title"), 
                  rdflib.URIRef("http://xmlns.com/foaf/0.1/name"),
                  rdflib.URIRef("http://www.w3.org/2006/vcard/ns#fn"),
                  rdflib.URIRef("http://www.w3.org/2006/vcard/ns#org")
                  
                  ]

def resolve(r):
    """
    URL is the potentially local URL
    realurl is the one used in the data. 

    return {url, realurl, label}
    """

    if r==None:
        return { 'url': None, 'realurl': None, 'label': None }
    if isinstance(r, rdflib.Literal): 
        return { 'url': None, 'realurl': None, 'label': get_label(r), 'lang': r.language }
        
    localurl=None
    if lod.config["types"]=={None: None}:
        if (r, rdflib.RDF.type, None) in g.graph:
            localurl=url_for("resource", label=lod.config["resources"][None][r])
    else:
        for t in g.graph.objects(r,rdflib.RDF.type):
            if t in lod.config["types"]: 
                l=lod.config["resources"][t][r].decode("utf8")
                localurl=url_for("resource", type_=lod.config["types"][t], label=l)                
                break
    url=r
    if localurl: url=localurl
    return { 'url': url, 'realurl': r, 'label': get_label(r) }

def localname(t): 
    """qname computer is not quite what we want"""
    
    r=t[max(t.rfind("/"), t.rfind("#"))+1:]
    # pending apache 2.2.18 being available 
    # work around %2F encoding bug for AllowEncodedSlashes apache option
    r=r.replace("%2F", "_")
    return r

def get_label(t): 
    if isinstance(t, rdflib.Literal): return unicode(t)
    for l in lod.config["label_properties"]:
        try: 
            return g.graph.objects(t,l).next()
        except: 
            pass
    try: 
        #return g.graph.namespace_manager.compute_qname(t)[2]
        return urllib2.unquote(localname(t))
    except: 
        return t

def label_to_url(label):
    label=re.sub(re.compile('[^\w ]',re.U), '',label)
    return re.sub(" ", "_", label)

def detect_types(graph): 
    types={}
    types[rdflib.RDFS.Class]=localname(rdflib.RDFS.Class)
    types[rdflib.RDF.Property]=localname(rdflib.RDF.Property)
    for t in set(graph.objects(None, rdflib.RDF.type)):
        types[t]=localname(t)

    # make sure type triples are in graph
    for t in types: 
        graph.add((t, rdflib.RDF.type, rdflib.RDFS.Class))

    return types

def reverse_types(types): 
    rtypes={}
    for t,l in types.iteritems(): 
        while l in rtypes: 
            warnings.warn(u"Multiple types for label '%s': (%s) rewriting to '%s_'"%(l,rtypes[l], l))           
            l+="_"
        rtypes[l]=t
    types.clear()
    for l,t in rtypes.iteritems():
        types[t]=l
    return rtypes

            
def find_resources(graph): 
    resources=collections.defaultdict(dict)
    
    for t in lod.config["types"]: 
        resources[t]={}
        for x in graph.subjects(rdflib.RDF.type, t): 
            resources[t][x]=_quote(localname(x))

    #resources[rdflib.RDFS.Class]=lod.config["types"].copy()

    return resources

def reverse_resources(resources): 
    rresources={}
    for t,res in resources.iteritems(): 
        rresources[t]={}
        for r, l in res.iteritems():
            while l in rresources[t]: 
                warnings.warn(u"Multiple resources for label '%s': (%s) rewriting to '%s_'"%(repr(l),rresources[t][l], repr(l+'_')))           
                l+="_"
                
            rresources[t][l]=r

        resources[t].clear()
        for l,r in rresources[t].iteritems():
            resources[t][r]=l

    return rresources


def _quote(l): 
    if isinstance(l,unicode): 
        l=l.encode("utf-8")
    return l
    #return urllib2.quote(l, safe="")
        

def get_resource(label, type_): 
    label=_quote(label)
    if type_ and type_ not in lod.config["rtypes"]:
        return "No such type_ %s"%type_, 404
    try: 
        t=lod.config["rtypes"][type_]
        return lod.config["rresources"][t][label]

    except: 
        return "No such resource %s"%label, 404

@lod.route("/download/<format_>")
def download(format_):
    return serialize(g.graph, format_)

@lod.route("/rdfgraph/<type_>/<rdf:label>.<format_>")
@lod.route("/rdfgraph/<rdf:label>.<format_>")
def rdfgraph(label, format_,type_=None): 
    r=get_resource(label, type_)
    if isinstance(r,tuple): # 404
        return r

    graph=rdflib.Graph()
    graph+=g.graph.triples((r,None,None))
    graph+=g.graph.triples((None,None,r))

    if lod.config["add_types_labels"]:
        addTypesLabels(graph, g.graph)

    return graphrdf(graph, format_)

def graphrdf(graph, format_):
    return dot(lambda uw: rdf2dot.rdf2dot(graph, stream=uw), format_)

def graphrdfs(graph, format_):
    return dot(lambda uw: rdfs2dot.rdfs2dot(graph, stream=uw), format_)

def dot(inputgraph, format_): 

    if format_ not in GRAPH_TYPES: 
        return "format '%s' not supported, try %s"%(format_, ", ".join(GRAPH_TYPES)), 415

    p=subprocess.Popen([DOT, "-T%s"%format_], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    uw=codecs.getwriter("utf8")(p.stdin)
    inputgraph(uw)

    p.stdin.close()
    def readres(): 
        s=p.stdout.read(1000)
        while s!="": 
            yield s
            s=p.stdout.read(1000)
        
    return Response(readres(), mimetype=GRAPH_TYPES[format_])
    

def addTypesLabels(subgraph, graph): 
    addMe=[]
    for o in itertools.chain(subgraph.objects(None,None),subgraph.subjects(None,None)):
        if not isinstance(o, rdflib.term.Node): continue
        addMe+=list(graph.triples((o,rdflib.RDF.type, None)))
        for l in lod.config["label_properties"]:
            if (o, l, None) in graph:
                addMe+=list(graph.triples((o, l, None)))
                break
    subgraph+=addMe


@lod.route("/data/<type_>/<rdf:label>.<format_>")
@lod.route("/data/<rdf:label>.<format_>")
def data(label, format_, type_=None):
    r=get_resource(label, type_)
    if isinstance(r,tuple): # 404
        return r

    
    #graph=g.graph.query('DESCRIBE %s'%r.n3())
    # DESCRIBE <uri> is broken. 
    # http://code.google.com/p/rdfextras/issues/detail?id=25
    graph=rdflib.Graph()
    graph+=g.graph.triples((r,None,None))
    graph+=g.graph.triples((None,None,r))

    if lod.config["add_types_labels"]:
        addTypesLabels(graph, g.graph)

    return serialize(graph, format_)

def serialize(graph, format_):    

    format_,mimetype_=mimeutils.format_to_mime(format_)

    response=make_response(graph.serialize(format=format_))

    response.headers["Content-Type"]=mimetype_

    return response


@lod.route("/page/<type_>/<rdf:label>")
@lod.route("/page/<rdf:label>")
def page(label, type_=None):
    r=get_resource(label, type_)
    if isinstance(r,tuple): # 404
        return r

    outprops=sorted([ (resolve(x[0]), resolve(x[1])) for x in g.graph.predicate_objects(r) if x[0]!=rdflib.RDF.type])
    
    types=sorted([ resolve(x) for x in g.graph.objects(r,rdflib.RDF.type)])
    
    inprops=sorted([ (resolve(x[0]), resolve(x[1])) for x in g.graph.subject_predicates(r) ])

    picked=r in session["picked"]

    params={ "outprops":outprops, 
        "inprops":inprops, 
        "label":get_label(r),
        "urilabel":label,
        "graph":g.graph,
        "type_":type_, 
        "types":types,
        "resource":r, 
        "picked":picked }
    p="lodpage.html"
        
    if r==rdflib.RDFS.Class or r==rdflib.OWL.Class: 
        # page for all classes
        roots=graphutils.find_roots(g.graph, rdflib.RDFS.subClassOf, set(lod.config["types"]))
        params["classes"]=[graphutils.get_tree(g.graph, x, rdflib.RDFS.subClassOf, resolve) for x in roots]
        
        p="classes.html"
        # show classes only once
        for x in inprops[:]: 
            if x[1]["url"]==rdflib.RDF.type:
                inprops.remove(x)

    elif (r, rdflib.RDF.type, rdflib.RDFS.Class) in g.graph or (r, rdflib.RDF.type, rdflib.OWL.Class) in g.graph:
        # page for a single class
        
        params["classes"]=[graphutils.get_tree(g.graph, r, rdflib.RDFS.subClassOf, resolve)]
        superClass=g.graph.value(r,rdflib.RDFS.subClassOf)
        if superClass: 
            params["classes"]=[(resolve(superClass), params["classes"])]
            
        params["instances"]=[]
        # show subclasses/instances only once
        for x in inprops[:]: 
            if x[1]["url"]==rdflib.RDF.type:
                inprops.remove(x)
                params["instances"].append(x[0])
            elif x[1]["url"]==rdflib.RDFS.subClassOf: 
                inprops.remove(x)
        p="class.html"

    return render_template(p, **params)
          
@lod.route("/resource/<type_>/<rdf:label>")
@lod.route("/resource/<rdf:label>")
def resource(label, type_=None): 
    """
    Do ContentNegotiation for some resource and 
    redirect to the appropriate place
    """
    
    mimetype=mimeutils.best_match([mimeutils.RDFXML_MIME, mimeutils.N3_MIME, 
        mimeutils.NTRIPLES_MIME, mimeutils.HTML_MIME], request.headers.get("Accept"))
        
    if mimetype and mimetype!=mimeutils.HTML_MIME:
        path="data"
        ext="."+mimeutils.mime_to_format(mimetype)
    else:
        path="page"
        ext=""
    
    if type_:
        if ext!='' :
            url=url_for(path, type_=type_, label=label, format_=ext)
        else:
            url=url_for(path, type_=type_, label=label)
    else:
        if ext!='':
            url=url_for(path, label=label, format_=ext)
        else: 
            url=url_for(path, label=label)

    return redirect(url, 303)
        
        

@lod.route("/")
def index(): 
    types=sorted([resolve(x) for x in lod.config["types"]], key=lambda x: x['label'])
    resources={}
    for t in types:
        turl=t["realurl"]
        resources[turl]=sorted([resolve(x) for x in lod.config["resources"][turl]][:10], 
            key=lambda x: x.get('label'))
        if len(lod.config["resources"][turl])>10:
            resources[turl].append({ 'url': t["url"], 'label': "..." })
        t["count"]=len(lod.config["resources"][turl])
    
    return render_template("lodindex.html", 
                           types=types, 
                           resources=resources,
                           graph=g.graph)

@lod.before_request
def setupSession():
    if "picked" not in session:         
        session["picked"]=set()

@lod.route("/pick")
def pick(): 
    session["picked"]^=set((rdflib.URIRef(request.args["uri"]),)) # xor
    return redirect(request.referrer)

@lod.route("/picked/<action>/<format_>")
@lod.route("/picked/<action>/")
@lod.route("/picked/")
def picked(action=None, format_=None): 

    def pickedgraph(): 
        graph=rdflib.Graph()
        for x in session["picked"]:
            graph+=g.graph.triples((x,None,None))
            graph+=g.graph.triples((None,None,x))    

        if lod.config["add_types_labels"]:
            addTypesLabels(graph, g.graph)

        return graph



    if action=='download': 
        return serialize(pickedgraph(), format_)
    elif action=='rdfgraph': 
        return graphrdf(pickedgraph(), format_)
    elif action=='rdfsgraph':
        return graphrdfs(pickedgraph(), format_)
    elif action=='clear':
        session["picked"]=set()
        return render_template("picked.html",
                               things=[])
    else:
        things=[resolve(x) for x in session["picked"]]
        return render_template("picked.html",
                               things=things)

    

        

    
##################

def serve(graph_,debug=False):
    """Serve the given graph on localhost with the LOD App"""

    get(graph_).run(debug=debug)


def get(graph, types='auto',image_patterns=["\.[png|jpg|gif]$"], 
        label_properties=LABEL_PROPERTIES, 
        hierarchy_properties=[ rdflib.RDFS.subClassOf, rdflib.RDFS.subPropertyOf ],
        add_types_labels=True):

    """
    Get the LOD Flask App setup to serve the given graph
    """

    lod.config["graph"]=graph
    lod.config["label_properties"]=label_properties
    lod.config["hierarchy_properties"]=hierarchy_properties
    lod.config["add_types_labels"]=add_types_labels
    
    if types=='auto':
        lod.config["types"]=detect_types(graph)
    elif types==None: 
        lod.config["types"]={None:None}
    else: 
        lod.config["types"]=types

    lod.config["rtypes"]=reverse_types(lod.config["types"])

    lod.config["resources"]=find_resources(graph)
    lod.config["rresources"]=reverse_resources(lod.config["resources"])

    lod.secret_key='veryverysecret'


    
    return lod    
    
    
    

def _main(g, out, opts): 
    import rdflib    
    import sys
    if len(g)==0:
        import bookdb
        g=bookdb.bookdb

    opts=dict(opts)
    debug='-d' in opts
    types='auto'
    if '-t' in opts: 
        types=[rdflib.URIRef(x) for x in opts['-t'].split(',')]
    if '-n' in opts:
        types=None
 
    get(g, types=types).run(debug=debug)

def main(): 
    from rdfextras.utils.cmdlineutils import main as cmdmain
    cmdmain(_main, options='t:nd')

if __name__=='__main__':
    main()
