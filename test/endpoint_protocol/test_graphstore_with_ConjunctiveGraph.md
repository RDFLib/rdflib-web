# Graph Store Protocol Tests [rdflib.ConjunctiveGraph()]

Testing the graph store protocol implementation backed by a plain
Graph. The graph is served as default graph and no other graphs can be
created.

## put__default_graph

### Request

```
PUT $GRAPHSTORE$?default HTTP/1.1
Host: $HOST$
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

<http://$HOST$$GRAPHSTORE$/person/1> a foaf:Person;
    foaf:businessCard [ 
        a v:VCard;
        v:fn "John Doe" 
    ].            
```

### Response

```
400 Default graph is read only

```

## get_of_put__default_graph

### Request

```
GET $GRAPHSTORE$?default HTTP/1.1
Host: $HOST$
Accept: text/turtle

```

### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8

```

## put__named_graph

### Request

```
PUT $GRAPHSTORE$/foo HTTP/1.1
Host: $HOST$
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

<http://$HOST$$GRAPHSTORE$/person/1> a foaf:Person;
    foaf:businessCard [ 
        a v:VCard;
        v:fn "John Doe" 
    ].            
```

### Response

```
201 Created

```

## get_of_put__named_graph

### Request

```
GET $GRAPHSTORE$/foo HTTP/1.1
Host: $HOST$
Accept: text/turtle

```
### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

<http://$HOST$$GRAPHSTORE$/person/1> a foaf:Person;
   foaf:businessCard [ 
        a v:VCard;
        v:fn "John Doe" 
   ].
```

## get_of_put__default_graph

### Request

```
GET $GRAPHSTORE$?default HTTP/1.1
Host: $HOST$
Accept: text/turtle

```

### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

<http://$HOST$$GRAPHSTORE$/person/1> a foaf:Person;
   foaf:businessCard [ 
        a v:VCard;
        v:fn "John Doe" 
   ].
```

