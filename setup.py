from setuptools import setup, find_packages
import re

def find_version(filename):
    _version_re = re.compile(r'__version__ = "(.*)"')
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)

__version__ = find_version('rdflib_web/__init__.py')

setup(
    name = 'rdflib-web',
    version = __version__,
    description = "RDFLib Web Apps.",
    author = "Gunnar Aastrand Grimnes",
    author_email = "gromgull@gmail.com",
    url = "https://github.com/RDFLib/rdflib-web",
    license = "BSD",
    platforms = ["any"],
    classifiers = ["Programming Language :: Python",
                   "License :: OSI Approved :: BSD License",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   "Operating System :: OS Independent",
                   ],
    packages = ['rdflib_web'],
    package_dir = { 'rdflib_web': 'rdflib_web' },
    package_data = { 'rdflib_web': ['templates/*.html','static/*',]}
    #packages=find_packages(include=['exampleproject', 'exampleproject.*'])
)

install_requires = [
    'flask',
    'rdflib>=4.0',
    'python-mimeparse'
]
