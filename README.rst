Python HTTP Basic Push Server
=============================

hbpush is a python/tornado_ implementation of Leo Ponomarev's `Basic HTTP Push Relay Protocol <http://pushmodule.slact.net/>`_.

Yes, it is yet another comet server, but simpler, and speaking plain old HTTP.

Features
--------

- long polling / interval polling for subscriber
- pluggable message storage (included: memory or redis)

Install
-------

::

  $ pip install py-hbpush

or

::

  $ easy_install py-hbpush

Running it
----------

::

  $ hbpushd

to run it with the default configuration, or

::

  $ hbpushd --config=path/to/configuration/file

Playing with it
---------------

Well, well, the best is probably to read protocol_ itself.
For lazies out there, here is a small example using cURL_::

  // Run the server with the default configuration
  $ sudo hbpushd &
  
  // Post a message to channel `test`
  $ curl -i -d 'Hello world!' -H 'Content-Type: text/plain' http://localhost:80/publisher/test

  // Retrieve that message (and print response headers)
  $ curl -i http://localhost:80/subscriber/test
  HTTP/1.1 200 OK
  Content-Length: 12
  Vary: If-Modified-Since, If-None-Match
  Server: TornadoServer/0.1
  Last-Modified: Mon, 07 Jun 2010 16:21:50 GMT
  Etag: 0
  Content-Type: text/plain

  Hello world!

  // Retrieve the next message (there's none so far, so the client
  // will wait)
  $ curl -i -H 'If-Modified-Since: Mon, 07 Jun 2010 16:21:50 GMT' -H 'If-None-Match: 0' http://localhost:90/test

  // Open up another terminal, and send a new message
  $ curl -i -d '{"msg":"Hello world!"}' -H 'Content-Type: application/json' http://localhost:90/test

  // Back to the first terminal, you'll see the message has arrived
  HTTP/1.1 200 OK
  Content-Length: 22
  Vary: If-Modified-Since, If-None-Match
  Server: TornadoServer/0.1
  Last-Modified: Mon, 07 Jun 2010 16:25:21 GMT
  Etag: 0
  Content-Type: application/json

  {"msg":"Hello world!"}

Configuration
-------------

hbpushd configuration files are either YAML or JSON files.

Server
^^^^^^

You can use the following options:

- ``port``: the numeric port number to use (default to ``80``)
- ``address``: the IP-address to bind to (default to ``''``)

Example configuration (in YAML)::

  port: 9090
  address: 127.0.0.1

Stores
^^^^^^

Stores are modules responsible for storing/retrieving messages. hbpush comes bundled with two types
of stores, ``memory`` and ``redis``. Each of these stores has specific options. For redis:

- ``host``: the hostname for redis server, default to ``'localhost'``
- ``port``: the port for redis server, default to ``6379``
- ``key_prefix``: a string prepended to a channel identifier to make a redis key. Use this to avoid key
  collision when you're using your redis server for other stuff.

Memory stores haven't any specific options (yet).

Here is an example of how to specify the store (YAML)::

  port: 9090
  store:
    type: redis
    key_prefix: hbpush_

In more complex configurations, you might need multiple stores on the same server. Here is how it looks
like::

  port: 9090
  store:
    mystore:
      type: redis
      host: 127.0.0.1
      port: 6380
    myotherstore:
      type: memory
    default:
      type: redis
      port: 6379

Note that ``default`` is a special name (see the `Locations`_ part). Also, if you just specify an unnamed
store, it will have a name of ``default``. That means that the two following configuration snippets are
equivalent::

  port: 9090
  store:
    type: redis
    key_prefix: hbpush_

  # is exactly the same as

  port: 9090
  store:
    default:
      type: redis
      key_prefix: hbpush_

Locations
^^^^^^^^^

Locations are URLs pattern on which the server listen for publishing/subscribing request. hbpush provides
a flexible way to configure those, or you can stick with the default configuration, which should be enough
for a vast majority of use-cases.

A location has a ``type`` of either ``publisher`` or ``subscriber``. It supports also setting some options:

- ``store``: the store name to use (default to ``default``)
- ``prefix``: an URL prefix for this location. For example ``/publisher/``. Everything coming after the prefix will be used as channel id (not set by default)
- ``url``: the complete URL pattern to use for this location, eg: ``/channel/(\d+)/publish/``. Not you should have only one capture group, that must represent the channel id. This settings has precedence over ``prefix`` (not set by default)
- ``polling`` (subscriber only): ``interval`` or ``long``, see the protocol_ for more information (default to ``long``)
- ``create_on_post`` (publisher only): if set to ``false``, you will need to create a channel with a PUT request first before POSTing any data to it (default to ``true``)

For info, the default configuration looks like this::

  port: 80
  store:
    type: memory
  locations:
    -
      type: subscriber
      prefix: /subscriber/
    -
      type: publisher
      prefix: /publisher/


Now, here's a complex configuration example, with multiple stores, and multiple pub/sub locations::

  port: 9090
  store:
    default:
      type: memory
    redis1:
      type: redis
      key_prefix: redis1_
    redis2:
      type: redis
      key_prefix: redis2_
  locations:
    -
      type: subscriber
      prefix: /sub/
    -
      type: publisher
      prefix: /pub/
    -
      type: subscriber
      polling: interval
      url: /redis/(.+)/1/sub/
      store: redis1
    -
      type: publisher
      url: /redis/(.+)/1/pub/
      store: redis1
    -
      type: subscriber
      url: /redis/(.+)/2/sub/
      store: redis2
    -
      type: publisher
      url: /redis/(.+)/2/pub/
      store: redis2

Caveats
~~~~~~~

- The server will try each location pattern in order of definition.
- It also won't detect if you messed up your URL scheme, so be careful designing it. A typical example::

    locations:
      -
        type: subscriber
        url: /(.+)
      -
        type: publisher
        url: /pub/(.+)

  with this configuration, your publisher location will be unreachable, as the server will always match the
  request to the subscriber location.

Known Issues
------------

- the current implementation of the redis message store uses zset (ordered sets) to store channels
  messages. It allows for blazingly fast search of a given message in a channel. But due to the way
  scoring is implemented in zsets (as a double-precision number), you can't have more than 10K messages
  per second (peek) for a given channel. If you ever reach that kind of volume, it is recommended to
  partition your traffic so you can stay below the threshold.
- hbpushd depends on the development version of facebook's tornado. `setup.py` will install a
  compatible version, but if you have already installed tornado through `easy_install` or `pip`,
  you might have some problems with Etag, or when launching hbpushd. In that case, reinstall
  the latest version of tornado_.

Change log
----------

- 0.1.0
  - redis and memory message store
  - interval and long polling
  - subscriber and publisher locations
  - partial implementation of the protocol

.. _tornado: http://github.com/facebook/tornado
.. _cURL: http://curl.haxx.se/
.. _protocol: http://pushmodule.slact.net/protocol.html
