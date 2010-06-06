from brukva.client import Client, Connection

class ConnectionPool(object):
    pass

class AutoConnection(Connection):
    def connect(self):
        if self._stream:
            return
        super(AutoConnection, self).connect()

    def disconnect(self):
        if not self._stream:
            return
        super(AutoConnection, self).disconnect()

    def write(self, data):
        self.connect()
        super(AutoConnection, self).write(data)

class AutoClient(Client):
    def __init__(self, host='localhost', port=6379, io_loop=None):
        super(AutoClient, self).__init__(host, port, io_loop)
        self.connection = AutoConnection(host, port, io_loop=self._io_loop)

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
