from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.readlines()
requirements = [i.replace('\n', '') for i in requirements]


setup(
    name='Hashmal',
    version = '0.1.0a',
    description='Bitcoin transaction script IDE.',
    url='https://github.com/mazaclub/hashmal',
    install_requires=requirements,
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
    entry_points={
        'hashmal.plugin': [
            'Address Encoder = hashmal_lib.plugins.addr_encoder:make_plugin',
            'Blockchain = hashmal_lib.plugins.blockchain:make_plugin',
            'Script Generator = hashmal_lib.plugins.script_gen:make_plugin',
            'Stack Evaluator = hashmal_lib.plugins.stack:make_plugin',
            'Tx Builder = hashmal_lib.plugins.tx_builder:make_plugin',
            'Tx Deserializer = hashmal_lib.plugins.tx_deserializer:make_plugin',
            'Variables = hashmal_lib.plugins.variables:make_plugin'
        ]
    }
)
