from setuptools import setup
from hashmal_lib.gui_utils import hashmal_entry_points

with open('requirements.txt') as f:
    requirements = f.readlines()
requirements = [i.replace('\n', '') for i in requirements]


setup(
    name='Hashmal',
    version = '0.1.0a',
    description='Bitcoin transaction script IDE.',
    url='https://github.com/mazaclub/hashmal',
    install_requires = requirements,
    author='Tyler Willis, mazaclub',
    author_email='kefkius@maza.club',
    keywords=[
        'bitcoin',
        'transaction',
        'script',
        'ide'
    ],
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Topic :: Software Development :: Interpreters'
    ],
    scripts=['hashmal'],
    packages=[
        'hashmal_lib',
        'hashmal_lib.core',
        'hashmal_lib.plugins'
    ],
    entry_points = hashmal_entry_points
)
