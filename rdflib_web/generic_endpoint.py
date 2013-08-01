import rdflib
import mimeutils

class DefaultGraphReadOnly(Exception):
    pass

class NamedGraphsNotSupported(Exception):
    pass

class GenericEndpoint:
    """
    This is an implementation of the SPAQL 1.1 Protocol and SPARQL 1.1
    Graph Store Protocol suitable for integration into webserver
    frameworks.
    """

    def __init__(self, ds, coin_url):
        """
        :argument:ds: The dataset to be used. Must be a Dataset (recommeded),
        ConjunctiveGraph or Graph. In case of a Graph, it is served as
        the default graph.
        :argument:coin_url: A function that takes no arguments and outputs
        an URI for a fresh graph. This is used when graph_identifier is
        None and neither 'default' nor 'graph' can be found in args.
        """
        self.ds = ds
        self.coin_url = coin_url

    DEFAULT = 'DEFAULT'

    RESULT_GRAPH = 0
    RESULT_SPARQL = 1

    def negotiate(self, resulttype, accept_header):
        #TODO: Find all mimetypes supported by the serializers
        #automatically instead of hardcoded
        if resulttype == self.RESULT_GRAPH:
            available = ['application/n-triples', 'text/n3', 'text/turtle', 'application/rdf+xml']
        elif resulttype == self.RESULT_SPARQL:
            available = ["text/html", "application/sparql-results+json", "application/sparql-results+xml"]
        assert available, "Invalid resulttype"
        best = mimeutils.best_match(available, accept_header) or available[-1]
        return best, best

    def query(self, method, args, body, mimetype, accept_header):
        try: 
            if method == 'POST':
                if mimetype == "application/x-www-form-urlencoded":
                    q = body["query"]
                    default_graph_uri = body.get("default-graph-uri") # request.value would be more tolerant
                    named_graph_uri = body.get("named-graph-uri") # request.value would be more tolerant
                elif mimetype == "application/sparql-query":
                    q = body
                    default_graph_uri = args.get("default-graph-uri")
                    named_graph_uri = args.get("named-graph-uri")
                else:
                    return (415, dict(), "Media type %s not supported" % mimetype)
            elif method == 'GET' or method == 'HEAD':
                    q = args["query"]
                    default_graph_uri = args.get("default-graph-uri")
                    named_graph_uri = args.get("named-graph-uri")
            else:
                response = (405, {"Allow": "GET, HEAD, POST"}, "Method %s not supported" % method)
        except KeyError:
            return (400, dict(), 'Missing obligatory HTTP header or query parameter')
                
        default_graph_uri = default_graph_uri and rdflib.URIRef(default_graph_uri)
        named_graph_uri = named_graph_uri and rdflib.URIRef(named_graph_uri)

        try:
            # TODO: Can we distinguish between internal error and bad query?
            # TODO: implement default-graph-uri and named-graph-uri
            results=self.ds.query(q)

            if results.graph:
                result_type = self.RESULT_GRAPH
            else:
                result_type = self.RESULT_SPARQL

            format, content_type = self.negotiate(result_type, accept_header)

            return (200, {"Content-type": content_type}, results.serialize(format=format))
        except: 
            return (400, dict(), "")

    def update(self, method, args, body, mimetype, accept_header):
        try: 
            # TODO: *-graph-uri can turn up multiple times
            if mimetype == "application/x-www-form-urlencoded":
                q = body["update"]
                using_graph_uri = body.get("using-graph-uri") # request.value would be more tolerant
                using_named_graph_uri = body.get("using-named-graph-uri") # request.value would be more tolerant
            elif mimetype == "application/sparql-update":
                q = body
                using_graph_uri = args.get("using-graph-uri")
                using_named_graph_uri = args.get("using-named-graph-uri")
            else:
                return (415, dict(), "Mediatype %s is not supported" % mimetype)
                
            using_graph_uri = using_graph_uri and URIRef(using_graph_uri)
            using_named_graph_uri = using_named_graph_uri and URIRef(using_named_graph_uri)

            self.ds.update(q)
            return (204, dict(), "")
        except: 
            # Blame every error on the client, just because I don't know better.
            return (400, dict(), "")

    def graph_store(self, method, graph_identifier, args, body, mimetype, accept_header):
        """Handles a request according to the SPARQL 1.1 graph store
        protocol.

        :argument:method: 'PUT', 'POST', 'DELETE', or 'GET'
        :argument:graph_identifier: rdflib.URIRef of the graph against
        which the request is made. It must be None for indirect requests. The
        special value GenericEndpoint.DEFAULT denotes the default graph. 
        :argument:args: A dict containing all URL parameters
        :argument:body: The request body as list of dicts if the
        content-type is multipart/form-data, otherwise a string.
        :argument:mimetype: The mime type part (i.e. without charset) of
        the request body
        :argument:accept_header: The accept header value as given by
        the client. This is required for content negotiation.

        :Returns:

        A triple consisting of the HTTP status code, a dictionary of
        headers that must be included in the status, and the body of
        the status. In case of an error (i.e. the status code is
        at least 400), then the body only consists of a error message
        as string. In this case, the caller is responsible to create a
        proper status body. If the status code is 201 or 204, the body
        is None.

        This method can through exceptions. If this happens, it is always an
        internal error.
        """
        if not graph_identifier:
            if 'default' in args:
                graph_identifier = self.DEFAULT
            elif 'graph' in args:
                graph_identifier = rdflib.URIRef(args['graph'])
            elif method == 'POST':
                graph_identifier = None
            else:
                return (400, dict(), "Missing URL query string parameter 'graph' or 'default'")

        existed = False
        if graph_identifier == self.DEFAULT:
            existed = True
        elif graph_identifier and self.ds.context_aware:
            existed = graph_identifier in {g.identifier for g in self.ds.contexts()}

        def get_graph(identifier):
            # Creates the graph if it does not already exist and returns
            # it.
            if graph_identifier == self.DEFAULT:
                # A ConjunctiveGraph or Datset itself represents the
                # default graph (it might be the union of all graphs).
                # In case of a plain Graph, the default graph is the
                # graph itself too.
                return self.ds
            elif hasattr(self.ds, "graph"): # No Graph.graph_aware
                return self.ds.graph(identifier)
            elif self.ds.context_aware:
                return self.ds.get_context(identifier)
            else:
                raise NamedGraphsNotSupported()

        def clear_graph(identifier):
            if identifier == self.DEFAULT:
                if self.ds.default_union:
                    raise DefaultGraphReadOnly()
                elif self.ds.context_aware:
                    self.ds.default_context.remove((None,None,None))
                else:
                    self.ds.remove((None,None,None))
            else:
                self.ds.remove((None, None, None, get_graph(identifier)))

        def remove_graph(identifier):
            # Unfortunately, there is no Graph.graph_aware, so use
            # hasattr
            if identifier == self.DEFAULT and self.ds.default_union:
                raise DefaultGraphReadOnly()
            elif hasattr(self.ds, "remove_graph"):
                self.ds.remove_graph(get_graph(identifier))
            else:
                clear_graph(identifier)

        def parseInto(target, data, format):
            # Makes shure that the for ConjucntiveGraph and Dataset we
            # parse into the default graph instead of into a fresh
            # graph.
            if target.default_union:
                raise DefaultGraphReadOnly()
            if target.context_aware:
                target.default_context.parse(data=data, format=format)
            else:
                target.parse(data=data, format=format)

        try:

            if method == 'PUT':
                if existed:
                    clear_graph(graph_identifier)
                target = get_graph(graph_identifier)
                parseInto(target, data=body, format=mimetype)
                response = (204 if existed else 201, dict(), None)

            elif method == 'DELETE':
                if existed:
                    remove_graph(graph_identifier)
                    response = (204, dict(), None)
                else:
                    response = (404, dict(), 'Graph %s not found' % graph_identifier)

            elif method == 'POST':
                additional_headers = dict()
                if not graph_identifier:
                    # Coin a new identifier
                    existed = False
                    url = self.coin_url()
                    graph_identifier = rdflib.URIRef(url)
                    additional_headers['location'] = url
                target = get_graph(graph_identifier)
                if mimetype == "multipart/form-data":
                    for post_item in body:
                        target = get_graph(graph_identifier)
                        parseInto(target, data=post_item['data'], format=post_item['mimetype'])
                else:
                    parseInto(target, data=body, format=mimetype)
                response = (204 if existed else 201, additional_headers, None)

            elif method == 'GET' or method == 'HEAD':
                if existed:
                    format, content_type = self.negotiate(self.RESULT_GRAPH, accept_header)
                    if content_type.startswith('text/'): content_type += "; charset=utf-8"
                    headers = {"Content-type": content_type}
                    response = (200, headers, get_graph(graph_identifier).serialize(format=format))
                else:
                    response = (404, dict(), 'Graph %s not found' % graph_identifier)

            else:
                response = (405, {"Allow": "GET, HEAD, POST, PUT, DELETE"}, "Method %s not supported" % method)

        except DefaultGraphReadOnly:
            response = (400, dict(), "Default graph is read only because it is the uion")
        except NamedGraphsNotSupported:
            response = (400, dict(), "Named graphs not supported")

        return response

