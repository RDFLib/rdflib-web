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

from rdflib import RDF, RDFS
import rdflib.util as util
from rdflib.tools import rdfs2dot, rdf2dot


from flask import render_template, request, make_response, redirect, url_for, g, Response, session

from werkzeug.routing import BaseConverter
from werkzeug.urls import url_quote

from jinja2 import contextfilter, Markup

from .endpoint import endpoint as lod
from . import mimeutils

from rdfextras_web.caches import lfu_cache

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

@contextfilter
def termdict_link(ctx, t):
    if not t: return ""
    if isinstance(t,dict):
        cls='class="external"' if t['external'] else ''

        return Markup("<a %s href='%s'>%s</a>"%(cls, t['url'], t['label']))
    else:
        return [termdict_link(ctx,x) for x in t]


def is_rdf_node(t):
    return isinstance(t, rdflib.term.Node)

lod.url_map.converters['rdf'] = RDFUrlConverter
lod.jinja_env.filters["term"]=termdict_link
lod.jinja_env.tests["rdf_node"]=is_rdf_node

LABEL_PROPERTIES=[RDFS.label,
                  rdflib.URIRef("http://purl.org/dc/elements/1.1/title"),
                  rdflib.URIRef("http://xmlns.com/foaf/0.1/name"),
                  rdflib.URIRef("http://www.w3.org/2006/vcard/ns#fn"),
                  rdflib.URIRef("http://www.w3.org/2006/vcard/ns#org")

                  ]
@lfu_cache(200)
def resolve(r):
    """
    URL is the potentially local URL
    realurl is the one used in the data.

    return {url, realurl, label}
    """

    if r==None:
        return { 'url': None, 'realurl': None, 'label': None }
    if isinstance(r, rdflib.Literal):
        return { 'url': None, 'realurl': None, 'label': unicode(r), 'lang': r.language }

    # if str(r)=='http://www.agroxml.de/rdf/vocabulary/workProcess#WorkProcess':
    #     asldkj

    t=None
    localurl=None
    if lod.config["types"]=={None: None}:
        if lod.config["resource_types"][r] in g.graph:
            localurl=url_for("resource", label=lod.config["resources"][None][r])
    else:
        for t in lod.config["resource_types"][r]:
            if t in lod.config["types"]:
                try:
                    l=lod.config["resources"][t][r].decode("utf8")
                    localurl=url_for("resource", type_=lod.config["types"][t], label=l)
                    break
                except KeyError: pass

    types=[ resolve(t) for t in lod.config["resource_types"][r] if t!=r]

    return { 'external': not localurl,
             'url': localurl or r,
             'realurl': r,
             'label': get_label(r),
             'type': types,
             'picked': r in session["picked"]}

def localname(t):
    """standard rdflib qname computer is not quite what we want"""

    r=t[max(t.rfind("/"), t.rfind("#"))+1:]
    # pending apache 2.2.18 being available
    # work around %2F encoding bug for AllowEncodedSlashes apache option
    r=r.replace("%2F", "_")
    return r

def lookup_label(t, graph):
    if isinstance(t, rdflib.Literal): return unicode(t)
    for l in lod.config["label_properties"]:
        try:
            return graph.objects(t,l).next()
        except StopIteration:
            pass
    try:
        #return g.graph.namespace_manager.compute_qname(t)[2]
        return urllib2.unquote(localname(t))
    except:
        return t


def get_label(r):
    try:
        return lod.config["labels"][r]
    except:
        try:
            l=urllib2.unquote(localname(r))
        except:
            l=r
        lod.config["labels"][r]=l
        return l


def label_to_url(label):
    label=re.sub(re.compile('[^\w ]',re.U), '',label)
    return re.sub(" ", "_", label)

def find_types(graph):
    types={}
    resource_types=collections.defaultdict(set)
    types[RDFS.Class]=localname(RDFS.Class)
    types[RDF.Property]=localname(RDF.Property)
    for s,p,o in graph.triples((None, RDF.type, None)):
        if o not in types: types[o]=_quote(localname(o))
        resource_types[s].add(o)

    for t in types:
        resource_types[t].add(RDFS.Class)

    return types, resource_types

def reverse_types(types):
    """Generate cache of localname=>type mapping"""
    rtypes={}
    for t,l in types.iteritems():
        while l in rtypes:
            warnings.warn(u"Multiple types for label '%s': (%s) rewriting to '%s_'"%(l,rtypes[l], l))
            l+="_"
        rtypes[l]=t

    # rewrite type cache, in case we changed some labels
    types.clear()
    for l,t in rtypes.iteritems():
        types[t]=l
    return rtypes


def find_resources(graph):

    """Build up cache of type=>[resource=>localname]]"""

    resources=collections.defaultdict(dict)

    for t in lod.config["types"]:
        resources[t]={}
        for x in graph.subjects(RDF.type, t):
            resources[t][x]=_quote(localname(x))

    resources[RDFS.Class].update(lod.config["types"].copy())

    return resources

def reverse_resources(resources):
    """
    Reverse resource-cache, build up cache
    type=>[localname=>resource]

    (for finding resources when entering URL)
    """
    rresources={}
    for t,res in resources.iteritems():
        rresources[t]={}
        for r, l in res.iteritems():
            while l in rresources[t]:
                warnings.warn(u"Multiple resources for label '%s': (%s, %s) rewriting to '%s_'"%(repr(l),rresources[t][l], r, repr(l+'_')))
                l+="_"

            rresources[t][l]=r

        resources[t].clear()
        for l,r in rresources[t].iteritems():
            resources[t][r]=l

    return rresources

def find_labels(graph, resources):
    labels={}
    for t, res in resources.iteritems():
        for r in res:
            if r not in labels:
                labels[r]=lookup_label(r, graph)
    return labels

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

    graph=_resourceGraph(r)

    return graphrdf(graph, format_)

def graphrdf(graph, format_):
    return dot(lambda uw: rdf2dot.rdf2dot(graph, stream=uw), format_)

def graphrdfs(graph, format_):
    return dot(lambda uw: rdfs2dot.rdfs2dot(graph, stream=uw), format_)

def dot(inputgraph, format_):

    if format_ not in GRAPH_TYPES:
        return "format '%s' not supported, try %s"%(format_, ", ".join(GRAPH_TYPES)), 415

    rankdir=request.args.get("rankdir", "BT")
    p=subprocess.Popen([DOT, "-Grankdir=%s"%rankdir, "-T%s"%format_], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    uw=codecs.getwriter("utf8")(p.stdin)
    inputgraph(uw)

    p.stdin.close()
    def readres():
        s=p.stdout.read(1000)
        while s!="":
            yield s
            s=p.stdout.read(1000)

    return Response(readres(), mimetype=GRAPH_TYPES[format_])

def _addTypesLabels(subgraph, graph):
    addMe=[]
    for o in itertools.chain(subgraph.objects(None,None),subgraph.subjects(None,None)):
        if not isinstance(o, rdflib.term.Node): continue
        addMe+=list(graph.triples((o,RDF.type, None)))
        for l in lod.config["label_properties"]:
            if (o, l, None) in graph:
                addMe+=list(graph.triples((o, l, None)))
                break
    subgraph+=addMe

def _resourceGraph(r):
    graph=rdflib.Graph()
    for p,ns in g.graph.namespaces():
        graph.bind(p,ns)

    graph+=g.graph.triples((r,None,None))
    graph+=g.graph.triples((None,None,r))

    if not "notypes" in request.args and lod.config["add_types_labels"]:
        _addTypesLabels(graph, g.graph)

    return graph


@lod.route("/data/<type_>/<rdf:label>.<format_>")
@lod.route("/data/<rdf:label>.<format_>")
def data(label, format_, type_=None):
    r=get_resource(label, type_)
    if isinstance(r,tuple): # 404
        return r

    graph=_resourceGraph(r)
    #graph=g.graph.query('DESCRIBE %s'%r.n3())
    # DESCRIBE <uri> is broken.
    # http://code.google.com/p/rdfextras/issues/detail?id=25

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

    special_props=(RDF.type, RDFS.comment, RDFS.label,
                   RDFS.domain, RDFS.range,
                   RDFS.subClassOf, RDFS.subPropertyOf)

    outprops=sorted([ (resolve(x[0]), resolve(x[1])) for x in g.graph.predicate_objects(r) if x[0] not in special_props])

    types=sorted([ resolve(x) for x in lod.config["resource_types"][r]], key=lambda x: x['label'].lower())

    comments=list(g.graph.objects(r,RDFS.comment))

    inprops=sorted([ (resolve(x[0]), resolve(x[1])) for x in g.graph.subject_predicates(r) ])

    picked=r in session["picked"]

    params={ "outprops":outprops,
             "inprops":inprops,
             "label":get_label(r),
             "urilabel":label,
             "comments":comments,
             "graph":g.graph,
             "type_":type_,
             "types":types,
             "resource":r,
             "picked":picked }
    p="lodpage.html"

    if r==RDF.Property:
        # page for all properties
        roots=util.find_roots(g.graph, RDFS.subPropertyOf, set(lod.config["resources"][r]))
        roots=sorted(roots, key=lambda x: get_label(x).lower())
        params["properties"]=[util.get_tree(g.graph, root, RDFS.subPropertyOf, resolve, lambda x: x[0]['label'].lower()) for root in roots]
        for x in inprops[:]:
            if x[1]["url"]==RDF.type:
                inprops.remove(x)


        p="properties.html"
    elif RDF.Property in lod.config["resource_types"][r]:
        # a single property

        params["properties"]=[util.get_tree(g.graph, r, RDFS.subPropertyOf, resolve)]

        superProp=[resolve(x) for x in g.graph.objects(r,RDFS.subPropertyOf) ]
        if superProp:
            params["properties"]=[(superProp, params["properties"])]

        params["domain"]=[resolve(do) for do in g.graph.objects(r,RDFS.domain)]
        params["range"]=[resolve(ra) for ra in g.graph.objects(r,RDFS.range)]

        # show subclasses/instances only once
        for x in inprops[:]:
            if x[1]["url"] in (RDFS.subPropertyOf, ):
                inprops.remove(x)

        p="property.html"
    elif r==RDFS.Class or r==rdflib.OWL.Class:
        # page for all classes
        roots=util.find_roots(g.graph, RDFS.subClassOf, set(lod.config["types"]))
        roots=sorted(roots, key=lambda x: get_label(x).lower())
        params["classes"]=[util.get_tree(g.graph, root, RDFS.subClassOf, resolve, sortkey=lambda x: x[0]['label'].lower()) for root in roots]

        p="classes.html"
        # show classes only once
        for x in inprops[:]:
            if x[1]["url"]==RDF.type:
                inprops.remove(x)

    elif RDFS.Class in lod.config["resource_types"][r] or rdflib.OWL.Class in lod.config["resource_types"][r]:
        # page for a single class

        params["classes"]=[util.get_tree(g.graph, r, RDFS.subClassOf, resolve)]

        superClass=[resolve(x) for x in g.graph.objects(r,RDFS.subClassOf) ]
        if superClass:
            params["classes"]=[(superClass, params["classes"])]

        params["classoutprops"]=[(resolve(p), [resolve(pr) for pr in g.graph.objects(p,RDFS.range)]) for p in g.graph.subjects(RDFS.domain,r)]
        params["classinprops"]=[([resolve(pr) for pr in g.graph.objects(p,RDFS.domain)],resolve(p)) for p in g.graph.subjects(RDFS.range,r)]

        params["instances"]=[]
        # show subclasses/instances only once
        for x in inprops[:]:
            if x[1]["url"]==RDF.type:
                inprops.remove(x)
                params["instances"].append(x[0])
            elif x[1]["url"] in (RDFS.subClassOf,
                                 RDFS.domain,
                                 RDFS.range):
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

    return render_template("lodindex.html")

@lod.route("/instances")
def instances():
    types=sorted([resolve(x) for x in lod.config["types"]], key=lambda x: x['label'].lower())
    resources={}
    for t in types:
        turl=t["realurl"]
        resources[turl]=sorted([resolve(x) for x in lod.config["resources"][turl]][:10],
            key=lambda x: x.get('label').lower())
        if len(lod.config["resources"][turl])>10:
            resources[turl].append({ 'url': t["url"], 'external': False, 'label': "..." })
        t["count"]=len(lod.config["resources"][turl])

    return render_template("instances.html",
                           types=types,
                           resources=resources)

@lod.route("/search")
def search():

    searchterm=request.args["searchterm"]
    offset=int(request.args["offset"]) if "offset" in request.args else 0

    results=[]
    found=set()

    for resource, label in lod.config["labels"].iteritems():
        r=re.compile("\W%s\W"%re.escape(searchterm), re.I)
        if r.search(label):
            results.append(resolve(resource))
            found.add(resource)
            if len(results)>offset+10: break

    results.sort(key=lambda x: x["label"].lower())

    for resource, label in lod.config["labels"].iteritems():
        if len(results)>offset+10: break

        r=re.compile("%s"%re.escape(searchterm), re.I)
        if resource not in found and r.search(label):
            results.append(resolve(resource))


    results=results[offset:offset+10]

    return render_template("search.html",
                           searchterm=searchterm,
                           results=results,
                           offset=offset)


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
        for p,ns in g.graph.namespaces():
            graph.bind(p,ns)

        for x in session["picked"]:
            graph+=g.graph.triples((x,None,None))
            graph+=g.graph.triples((None,None,x))

        if not "notypes" in request.args and lod.config["add_types_labels"]:
            _addTypesLabels(graph, g.graph)

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
        if action=='all':
            for t in lod.config["resources"]:
                session["picked"]|=set(lod.config["resources"][t])

        things=sorted([resolve(x) for x in session["picked"]])
        return render_template("picked.html",
                               things=things)

##################

def serve(graph_,debug=False):
    """Serve the given graph on localhost with the LOD App"""

    get(graph_).run(debug=debug)


def get(graph, types='auto',image_patterns=["\.[png|jpg|gif]$"],
        label_properties=LABEL_PROPERTIES,
        hierarchy_properties=[ RDFS.subClassOf, RDFS.subPropertyOf ],
        add_types_labels=True,dbname="RDFLib LOD App"):

    """
    Get the LOD Flask App setup to serve the given graph
    """

    lod.config["graph"]=graph
    lod.config["dbname"]=dbname

    lod.config["js"]={ "endpoint": "static", "filename":"lod.js" }
    lod.config["jssetup"]="lodsetup()"

    lod.config["label_properties"]=label_properties
    lod.config["hierarchy_properties"]=hierarchy_properties
    lod.config["add_types_labels"]=add_types_labels

    foundtypes, resource_types=find_types(graph)
    if types=='auto':
        lod.config["types"]=foundtypes
    elif types==None:
        lod.config["types"]={None:None}
    else:
        lod.config["types"]=types

    lod.config["resource_types"]=resource_types

    lod.config["rtypes"]=reverse_types(lod.config["types"])

    lod.config["resources"]=find_resources(graph)
    lod.config["rresources"]=reverse_resources(lod.config["resources"])

    lod.config["labels"]=find_labels(graph, lod.config["resources"])

    # make sure we get one session per app
    lod.config["SESSION_COOKIE_NAME"]="SESSION_"+re.sub('[^a-zA-Z0-9_]','_', str(graph.identifier))
    lod.secret_key='veryverysecret'+str(graph.identifier)

    return lod



def _main(g, out, opts):
    import rdflib
    import sys

    dbname="commandline DB"

    if len(g)==0:
        import bookdb
        g=bookdb.bookdb
        dbname='Books DB'

    opts=dict(opts)
    debug='-d' in opts
    if '-N' in opts:
        dbname=opts["-N"]
    types='auto'
    if '-t' in opts:
        types=[rdflib.URIRef(x) for x in opts['-t'].split(',')]
    if '-n' in opts:
        types=None

    get(g, types=types, dbname=dbname).run(host="0.0.0.0", debug=debug)

def main():
    from rdflib.extras.cmdlineutils import main as cmdmain
    cmdmain(_main, options='t:ndN:', stdin=False)

if __name__=='__main__':
    main()
