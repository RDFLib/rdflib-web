#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import re

def setup_python3():
    # Taken from "distribute" setup.py
    from distutils.filelist import FileList
    from distutils import dir_util, file_util, util, log
    from os.path import join
  
    tmp_src = join("build", "src")
    log.set_verbosity(1)
    fl = FileList()
    for line in open("MANIFEST.in"):
        if not line.strip():
            continue
        fl.process_template_line(line)
    dir_util.create_tree(tmp_src, fl.files)
    outfiles_2to3 = []
    for f in fl.files:
        outf, copied = file_util.copy_file(f, join(tmp_src, f), update=1)
        if copied and outf.endswith(".py"):
            outfiles_2to3.append(outf)
  
    util.run_2to3(outfiles_2to3)
  
    # arrange setup to use the copy
    sys.path.insert(0, tmp_src)

    return tmp_src

# Find version. We have to do this because we can't import it in Python 3 until
# its been automatically converted in the setup process.
def find_version(filename):
    _version_re = re.compile(r'__version__ = "(.*)"')
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)

__version__ = find_version('rdfextras_web/__init__.py')

config = dict(
    name = 'rdfextras-web',
    version = __version__,
    description = "RDFLib Web Apps.",
    author = "Gunnar Aastrand Grimnes",
    author_email = "gromgull@gmail.com",
    url = "https://github.com/RDFLib/rdfextras-web",
    license = "BSD",
    platforms = ["any"],
    classifiers = ["Programming Language :: Python",
                   "License :: OSI Approved :: BSD License",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   "Operating System :: OS Independent",
                   ],
    packages = ['rdfextras_web'],
    package_dir = { 'rdfextras_web': 'rdfextras_web' },
    package_data = { 'rdfextras_web': ['templates/*.html','static/*',]}
)

if sys.version_info[0] >= 3:
    from setuptools import setup
    config.update({'use_2to3': True})
    config.update({'src_root': setup_python3()})
else:
    try:
        from setuptools import setup
        config.update({'test_suite' : "nose.collector"})
    except ImportError:
        from distutils.core import setup


install_requires = [
    'rdfextras',
    'flask'
]

tests_require = install_requires
                      
extras_require = { 
    "web-conneg": ["mimeparse"],

    }


config.update(
    entry_points = {
        'console_scripts': [
            'sparqlendpointapp = rdfextras_web.endpoint:main',
            'rdflodapp = rdfextras_web.lod:main',                
        ],
        'rdf.plugins.serializer': [
            'html = rdfextras_web.htmlresults:HTMLSerializer',
        ],
        'rdf.plugins.resultserializer': [
            'html = rdfextras_web.htmlresults:HTMLResultSerializer',
        ],

    },
    #namespace_packages = ['rdfextras'], # TODO: really needed?
    install_requires = install_requires,
    tests_require = tests_require,
    extras_require = extras_require 
)
    
setup(**config)

