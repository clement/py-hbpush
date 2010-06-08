from brukva.client import Client, Connection

class ConnectionPool(object):
    pass

class AutoConnection(Connection):
    def __init__(self, host, port, client, io_loop=None):
        # Cyclic reference to the client,
        # allows us to automatically re-select the right DB upon reconnection
        self.client = client
        super(AutoConnection, self).__init__(host, port, io_loop=io_loop)

    def connect(self):
        if self._stream:
            return
        super(AutoConnection, self).connect()
        self.client.auto_select()

    def disconnect(self):
        if not self._stream:
            return
        super(AutoConnection, self).disconnect()

    def write(self, data):
        self.connect()
        super(AutoConnection, self).write(data)

class AutoClient(Client):
    def __init__(self, host='localhost', port=6379, database=0, io_loop=None):
        self.database = database
        super(AutoClient, self).__init__(host, port, io_loop)
        self.connection = AutoConnection(host, port, self, io_loop=self._io_loop)

    def auto_select(self):
        self.select(self.database)

    def execute_command(self, cmd, callbacks, *args, **kwargs):
        if callbacks is None:
            callbacks = []
        elif not hasattr(callbacks, '__iter__'):
            callbacks = [callbacks]
        try:
            self.connection.write(self.format(cmd, *args, **kwargs))
        except IOError:
            # Try a second time
            self.connection.disconnect()
            try:
                self.connection.write(self.format(cmd, *args, **kwargs))
            except IOError:
                self._sudden_disconnect(callbacks)
                return
        self.schedule(cmd, callbacks, *args, **kwargs)
        self.try_to_loop()
