# Graph Store Protocol Tests
    
This is a modified version of
http://www.w3.org/2009/sparql/docs/tests/data-sparql11/http-rdf-update/
See also: http://www.w3.org/2009/sparql/docs/tests/README.html

It is indicated where the tests differ from the original version.

## put__initial_state

PUT - Initial state

### Request

```
PUT $GRAPHSTORE$/person/1.ttl HTTP/1.1
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

## get_of_put__initial_state

GET of PUT - Initial state

### Request

```
GET $GRAPHSTORE$?graph=http://$HOST$$GRAPHSTORE$/person/1.ttl HTTP/1.1
Host: $HOST$
Accept: text/turtle
```


### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8
Content-Length: ...

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

<http://$HOST$$GRAPHSTORE$/person/1> a foaf:Person;
   foaf:businessCard [ 
        a v:VCard;
        v:fn "John Doe" 
   ].
```
    
## head_on_an_existing_graph

HEAD on an existing graph

### Request

```
HEAD $GRAPHSTORE$/person/1.ttl HTTP/1.1
Host: $HOST$
Accept: text/turtle
```


### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8
Content-Length: ...
```

## head_on_a_nonexisting_graph

HEAD on a non-existing graph

### Request

```
HEAD $GRAPHSTORE$/person/4.ttl HTTP/1.1
Host: $HOST$
```


### Response

```
404 Not Found                        
```


## put__graph_already_in_store

PUT - graph already in store

### Request

```
PUT $GRAPHSTORE$/person/1.ttl HTTP/1.1
Host: $HOST$
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

<http://$HOST$$GRAPHSTORE$/person/1> a foaf:Person;
    foaf:businessCard [ 
        a v:VCard;
        v:fn "Jane Doe" 
    ].
```

### Response

```
204 No Content
```

## get_of_put__graph_already_in_store

GET of PUT - graph already in store

### Request

```
GET $GRAPHSTORE$/person/1.ttl HTTP/1.1
Host: $HOST$
Accept: text/turtle
```


### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8
Content-Length: ...

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

<http://$HOST$$GRAPHSTORE$/person/1> a foaf:Person;
   foaf:businessCard [ 
        a v:VCard;
        v:fn "Jane Doe" 
   ] .
```

## put__default_graph

PUT - default graph

### Request

```
PUT $GRAPHSTORE$?default HTTP/1.1
Host: $HOST$
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

[]  a foaf:Person;
    foaf:businessCard [ 
        a v:VCard;
        v:given-name "Alice" 
    ] .
```

### Response
rdflib: Changed from '201 Created' to '204 No Content' because the
default graph always already exists.

```
204 No Content
```

## get_of_put__default_graph

GET of PUT - default graph

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
Content-Length: ...

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

[]  a foaf:Person;
    foaf:businessCard [ 
        a v:VCard;
        v:given-name "Alice" 
    ] .            
```

> Broken test. This request is good like this.
> ## put__mismatched_payload
> PUT - mismatched payload
> ### Request
> ```
> PUT $GRAPHSTORE$/person/1.ttl HTTP/1.1
> Host: $HOST$
> Content-Type: text/turtle; charset=utf-8
> 
> @prefix foaf: <http://xmlns.com/foaf/0.1/> .
> @prefix v: <http://www.w3.org/2006/vcard/ns#> .
> 
> <http://$HOST$$GRAPHSTORE$/person/1> a foaf:Person;
>     foaf:businessCard [ 
>         a v:VCard;
>         v:fn "Jane Doe" 
>     ].            
> ```
> ### Response
> ``` 
> 400 Bad Request            
> ```
    
## put__empty_graph

PUT - empty graph

### Request

```
PUT $GRAPHSTORE$?graph=http://$HOST$$GRAPHSTORE$/person/2.ttl HTTP/1.1
Host: $HOST$
Content-Type: text/turtle; charset=utf-8
```
   

### Response

rdflib: Changed from '200 OK' to '201 Created' because
the graph 2.ttl does not yet exist. (Although the
specification is a bit fishy in this regard.)

```
201 Created
```


## get_of_put__empty_graph

GET of PUT - empty graph

### Request

```
GET $GRAPHSTORE$/person/2.ttl HTTP/1.1
Host: $HOST$
Accept: text/turtle
```


### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8
Content-Length: ...
```


## put__replace_empty_graph
PUT - replace empty graph
### Request

```
PUT $GRAPHSTORE$?graph=http://$HOST$$GRAPHSTORE$/person/2.ttl HTTP/1.1
Host: $HOST$
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

[]  a foaf:Person;
    foaf:businessCard [ 
        a v:VCard;
        v:given-name "Alice" 
    ] .
```

### Response

rdflib: Changed from '200 OK' to '204 No Content' because the server
does not send a body.

```
204 No Content
```

## get_of_replacement_for_empty_graph
GET of replacement for empty graph
### Request

```
GET $GRAPHSTORE$/person/2.ttl HTTP/1.1
Host: $HOST$
Accept: text/turtle
```

### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8
Content-Length: ...

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

[]  a foaf:Person;
    foaf:businessCard [ 
        a v:VCard;
        v:given-name "Alice" 
    ] .
```



## delete__existing_graph
DELETE - existing graph
### Request

```
DELETE $GRAPHSTORE$/person/2.ttl HTTP/1.1
Host: $HOST$            
```

### Response

rdflib: Changed from '200 OK' to '204 No Content' for
obvious reasons.

```
204 No Content
```

## get_of_delete__existing_graph
GET of DELETE - existing graph
### Request

```
GET $GRAPHSTORE$/person/2.ttl HTTP/1.1
Host: $HOST$            
Accept: text/turtle
```

### Response

```
404 Not Found            
```

## delete__nonexistent_graph
DELETE - non-existent graph
### Request

```
DELETE $GRAPHSTORE$/person/2.ttl HTTP/1.1
Host: $HOST$            
```

### Response

```
404 Not Found            
```

## post__existing_graph
POST - existing graph
### Request

```
POST $GRAPHSTORE$/person/1.ttl HTTP/1.1
Host: $HOST$
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .

<http://$HOST$$GRAPHSTORE$/person/1> foaf:name "Jane Doe" .
```

### Response

rdflib: Changed from '200 OK' to '204 No Content'.

```
204 No Content
```

## get_of_post__existing_graph

GET of POST - existing graph

### Request

```
GET $GRAPHSTORE$/person/1.ttl HTTP/1.1
Host: $HOST$
Accept: text/turtle
```


### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8
Content-Length: ...

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

<http://$HOST$$GRAPHSTORE$/person/1> a foaf:Person;
    foaf:name "Jane Doe";
    foaf:businessCard [ 
        a v:VCard;
        v:fn "Jane Doe" 
    ] .            
```

## post__multipart_formdata

POST - multipart/form-data

### Request

```
POST $GRAPHSTORE$/person/1.ttl HTTP/1.1
Host: $HOST$
Content-Type: multipart/form-data; boundary=a6fe4cd636164618814be9f8d3d1a0de

--a6fe4cd636164618814be9f8d3d1a0de
Content-Disposition: form-data; name="lastName.ttl"; filename="lastName.ttl"
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
<http://$HOST$$GRAPHSTORE$/person/1> foaf:familyName "Doe" .

--a6fe4cd636164618814be9f8d3d1a0de
Content-Disposition: form-data; name="firstName.ttl"; filename="firstName.ttl"
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
<http://$HOST$$GRAPHSTORE$/person/1> foaf:givenName "Jane" .

--a6fe4cd636164618814be9f8d3d1a0de--
```

### Response
rdflib: Changed from '200 OK' to '204 No Content'.

```
204 No Content
```

## get_of_post__multipart_formdata

GET of POST - multipart/form-data

### Request

```
GET $GRAPHSTORE$/person/1.ttl HTTP/1.1
Host: $HOST$         
Accept: text/turtle
```


### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8
Content-Length: ...

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

<http://$HOST$$GRAPHSTORE$/person/1> a foaf:Person;
    foaf:name           "Jane Doe";
    foaf:givenName      "Jane";
    foaf:familyName     "Doe";
    foaf:businessCard [ 
        a               v:VCard;
        v:fn            "Jane Doe" 
    ] .
```

## post__create__new_graph

POST - create  new graph

### Request

```
POST $GRAPHSTORE$ HTTP/1.1
Host: $HOST$
Content-Type: text/turtle; charset=utf-8

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

[]  a foaf:Person;
    foaf:businessCard [ 
        a v:VCard;
        v:given-name "Alice" 
    ] .            
```

### Response

```
201 Created
Location: $NEWPATH$
```


## get_of_post__create__new_graph

GET of POST - create  new graph

### Request

```
GET $NEWPATH$ HTTP/1.1
Host: $HOST$
Accept: text/turtle
```


### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8
Content-Length: ...

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

[]  a foaf:Person;
    foaf:businessCard [ 
        a v:VCard;
        v:given-name "Alice" 
    ] .         
```

## post__empty_graph_to_existing_graph

POST - empty graph to existing graph

### Request

```
POST $NEWPATH$ HTTP/1.1
Host: $HOST$
Content-Type: text/turtle; charset=utf-8
```


### Response

```
204 No Content            
```

## get_of_post__after_noop

GET of POST - after noop

### Request

```
GET $NEWPATH$ HTTP/1.1
Host: $HOST$
Accept: text/turtle
```


### Response

```
200 OK
Content-Type: text/turtle; charset=utf-8
Content-Length: ...

@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix v: <http://www.w3.org/2006/vcard/ns#> .

[]  a foaf:Person;
    foaf:businessCard [ 
        a v:VCard;
        v:given-name "Alice" 
    ] .            
```

