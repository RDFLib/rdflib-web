rdflib-web
==========
Two RDFLib web-apps on top of the Flask web-microframework:
 * a SPARQL endpoint app implementing the SPARQL 1.0 Protocol
 * a Linked Open Data app for publishing resources as HTML pages

Each app is available as a commandline-script, or as a Flask Blueprint
for embedding in your own application.

Documentation on ReadTheDocs: http://rdflib-web.readthedocs.org/en/latest/

Status
------
See [TODO file](TODO.txt).

Installation
------------

```bash
   pip3 install https://github.com/RDFLib/rdflib-web/archive/master.zip
```

Running
-------
Run after installing with pip:

```bash
python -m rdflib_web.lod <RDF-file>
```

or run dev server in cloned instance:

```bash
FLASK_APP=rdflib_web FLASK_ENV=development flask run
```

Requirements
------------
FIXME: rdflib, flask and python-mimeparse where not installed automatically with pip3

These are installed automatically if you install with pip

 * For the Web-apps: Flask, http://flask.pocoo.org/
  * (which in turn requires Jinja2 and Werkzeug)
  * For correct content-negotiation: python-mimeparse (fallback without conneg)
