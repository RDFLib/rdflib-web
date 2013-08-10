# HTTP based testcases

This directory contains HTTP based tests described in a restricted
github flavoured markdown syntax. `../test_endpoint_protocol.py`
extracts the tests from these files and runs them.

## Filename

A testcase file must have a name starting with 'test_'. The part of
the filename before '.' is used as testcase name and must be a valid
Python identifier.

## Syntax

Example:

    # Name of the testcase [rdflib.Graph()]

    The part between [ ] in the title above is evaluated in order to
    create the endpoint's dataset for this test case. It defaults to
    `rdflib.Dataset()`.

    Description of the testcase goes here.

    ## name_of_test

    The parser looks for a line starting with `##` to find the first
    test. Then it skips everything until the first `### Request` line,
    i.e. here is some space for a description.

    ### Request

    In this section the client's request has to be described inside a
    codeblock. Only a single codeblock is allowed. It must be enclosed
    two lines only containing three backticks.

    ```
    POST /foo/bar/baz HTTP/1.1
    Host: $HOST$
    Content-type: text/plain
    
    Some body
    ```

    ### Response

    Here, the codeblock must contain the expected response.

    ```
    201 Created
    Location: http://example.org/newres
    ```
        

    ## name_of_second_test

    ### Request

    Here, the variable $NEWPATH$ is replaced with the value of the
    Location header from the last response that contained such a
    header.

    ```
    GET $NEWPATH$ HTTP/1.1
    Host: $HOST$
    Accept: text/turtle
    ```
        
    ### Response

    ```
    200 Ok
    Conent-type: text/plain
    
    Some body
    ```

## Variables

The following variables are substituted:

* `$HOST$` is the host where the endpoint is listening
* `$GRAPHSTORE$` is the path of the URL of the graph store
* `$NEWPATH$` is the URL returned in the Location HTTP header

## Verification of Responses

The test runner compares codes, but it does not report differing
status messages. It verifies whether all headers given in the test are
present in the response and compares their values. It permits
additional headers in the response. If the bodies are of type
text/turtle, then it checks them for equivalence. Otherwise, they are
compared as text.

