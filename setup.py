# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['xchk_core',
 'xchk_core.migrations',
 'xchk_core.signals',
 'xchk_core.templatetags']

package_data = \
{'': ['*']}

install_requires = \
['django-enumfield>=2.0.1,<3.0.0',
 'django>=2.2,<3.0',
 'graphviz>=0.14.1,<0.15.0',
 'pinax-notifications>=6.0.0,<7.0.0',
 'iteration-utilities>=0.10.1,<0.11.0',
 'cryptography>=3.0.0,<3.1.0']

setup_kwargs = {
    'name': 'xchk-core',
    'version': '0.2.0',
    'description': 'Core functionality for the xchk teaching framework',
    'long_description': None,
    'author': 'Vincent Nys',
    'author_email': 'vincentnys@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': None,
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'python_requires': '>=3.7,<4.0',
}


setup(**setup_kwargs)
