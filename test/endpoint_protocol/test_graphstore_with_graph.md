# Graph Store Protocol Tests [rdflib.Graph()]

Testing the graph store protocol implementation backed by a plain
Graph. The graph is served as default graph and no other graphs can be
created.

## put__initial_state

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
204 No Content

```

## get_of_put__initial_state

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

## get__named_graph

### Request

```
GET $GRAPHSTORE$/foo HTTP/1.1
Host: $HOST$
Accept: text/turtle

```

### Response

```
404 Not Found

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
400 Named graphs not supported

```

## post__named_graph

### Request

```
POST $GRAPHSTORE$/foo HTTP/1.1
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
400 Named graphs not supported

```

## delete__default_graph

### Request

```
DELETE $GRAPHSTORE$?default HTTP/1.1
Host: $HOST$
```

### Response

```
204 No Content
```

## get_of_delete__default_graph

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

