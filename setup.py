# coding=utf-8
# Bundle setuptools
import ez_setup
ez_setup.use_setuptools()


from setuptools import setup

setup(name='py-hbpush',
      version=__import__('hbpush').__version__,
      description='HTTP Basic Push Server',
      long_description=open('README.rst').read(),

      author='Clément Nodet',
      author_email='clement.nodet@gmail.com',
      url='http://github.com/clement/py-hbpush/',
      download_url='http://github.com/clement/py-hbpush/downloads',

      classifiers=('Development Status :: 3 - Alpha',
                   'Environment :: No Input/Output (Daemon)',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 2.6',
                   'Topic :: Internet :: WWW/HTTP :: HTTP Servers', ),

      packages=('hbpush', 'hbpush.channel', 'hbpush.store', 'hbpush.utils', 'hbpush.pubsub'),
      scripts=('bin/hbpushd',),
      dependency_links= ('http://github.com/facebook/tornado/tarball/b8271f94434208646eeec9cf33da703d97c5364e#egg=tornado-0.2',
                         'http://github.com/clement/brukva/tarball/bff451511a3cc09cd52bebcf6372a59d36567827#egg=brukva-0.0.1',),
      install_requires=('PyYAML', 'brukva==0.0.1', 'tornado==0.2'),
      requires=('PyYAML', 'brukva(==0.0.1)', 'tonardo(==0.2)'),
)
