import rdflib

DEFAULT = 'DEFAULT'

class GenericEndpoint:
    """
    This is an implementation of the SPAQL 1.1 Protocol and SPARQL 1.1
    Graph Store Protocol suitable for integration into webserver
    frameworks.
    """

    def __init__(self, ds, coin_url):
        """
        :argument:ds: The dataset to be used. Must be a Dataset.
        :argument:coin_url: A function that takes no arguments and outputs
        an URI for a fresh graph. This is used when graph_identifier is
        None and neither 'default' nor 'graph' can be found in args.
        """
        self.ds = ds
        self.coin_url = coin_url

    RESULT_GRAPH = 0

    def negotiate(self, resulttype, accept_header):
        #TODO: Find all mimetypes supported by the serializers
        #automatically instead of hardcoded
        import logging
        if resulttype == self.RESULT_GRAPH:
            available = ['application/n-triples', 'text/n3', 'text/turtle', 'application/rdf+xml']
        assert available, "Invalid resulttype"
        import mimeutils
        best = mimeutils.best_match(available, accept_header) or available[-1]
        return best, best

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
        """
        if not graph_identifier:
            if 'default' in args:
                graph_identifier = DEFAULT
            elif 'graph' in args:
                graph_identifier = rdflib.URIRef(args['graph'])
            elif method == 'POST':
                graph_identifier = None
            else:
                return (400, dict(), "Missing URL query string parameter 'graph' or 'default'")

        if graph_identifier == DEFAULT:
            existed = True
        elif graph_identifier:
            existed = graph_identifier in {g.identifier for g in self.ds.contexts()}

        def get_graph(identifier):
            if graph_identifier == DEFAULT:
                return self.ds.default_context
            else:
                return self.ds.get_context(identifier)

        if method == 'PUT':
            if existed:
                self.ds.remove_graph(get_graph(graph_identifier))
            target = get_graph(graph_identifier)
            target.parse(data=body, format=mimetype)
            response = (204 if existed else 201, dict(), None)

        elif method == 'DELETE':
            if existed:
                self.ds.remove_graph(get_graph(graph_identifier))
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
                    target.parse(data=post_item['data'], format=post_item['mimetype'])
            else:
                target.parse(data=body, format=mimetype)
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

        return response

