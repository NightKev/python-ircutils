"""Manages I/O for a single IRC server and client. This includes reading 
from the server and pushing a command to the server. It supports SSL 
connections.

"""
import asyncore, asynchat
import socket
try:
    import ssl
except ImportError:
    ssl_available = False
else:
    ssl_available = True
    import errno

from . import protocol
from . import responses


class Connection(asynchat.async_chat):
    """ This class represents an asynchronous connection with an IRC server. It
    handles all of the dirty work such as maintaining input and output with
    the server as well as automatically handling PING requests.
   
    """
    
    def __init__(self, ipv6=False):
        asynchat.async_chat.__init__(self)
        self.ping_auto_respond = True
        self.set_terminator(b"\r\n")
        self.collect_incoming_data = self._collect_incoming_data
        if ipv6:
            self.create_socket(socket.AF_INET6, socket.SOCK_STREAM)
        else:
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    
    
    def connect(self, hostname, port=None, use_ssl=False, password=None, ssl_options=None):
        """ Create a connection to the specified host. If a port is given, it'll
        attempt to connect with that. A password may be specified and it'll
        be sent if the IRC server requires one.
        
        """
        self.ssl_options = ssl_options
        self.hostname = hostname
        self.port = port
        self.use_ssl = use_ssl
        if use_ssl and not ssl_available:
            raise ImportError("Python's SSL module is unavailable.")
        elif use_ssl:
            port = port or 7000
            self.send = self._ssl_send
            self.recv = self._ssl_recv
        else:
            port = port or 6667
        asynchat.async_chat.connect(self, (hostname, port))
        if password is not None:
            self.execute("PASS", password)
    
    
    def found_terminator(self):
        """ Activated when ``\\r\\n`` is encountered. Do not call directly. """
        data = "".join([i.decode("utf_8", "replace") for i in self.incoming])
        self.incoming = []
        prefix, command, params = protocol.parse_line(data)
        if command == "PING" and self.ping_auto_respond:
            self.execute("PONG", *params)
        if command.isdigit():
            command = responses.from_digit(command)
        self.handle_line(prefix, command, params)
    
    
    def handle_error(self):
        raise # Causes the error to propagate. I hate the compact traceback
              # that asyncore uses.
    
    
    def handle_connect(self):
        """ Initializes SSL support after the connection has been made. """
        if self.use_ssl:
            if 'keyfile' in self.ssl_options:
                keyfile = self.ssl_options['key_file']
            else:
                keyfile = None
            if 'certfile' in self.ssl_options:
                certfile = self.ssl_options['certfile']
            else:
                certfile = None
            if 'ssl_version' in self.ssl_options:
                ssl_version = self.ssl_options['ssl_version']
            else:
                ssl_version = 2
            if 'server_side' in self.ssl_options:
                server_side = self.ssl_options['server_side']
            else:
                server_side = False
            if 'cert_reqs' in self.ssl_options:
                if self.ssl_options['cert_reqs'].upper() == 'NONE':
                    cert_reqs = ssl.CERT_NONE
                if self.ssl_options['cert_reqs'].upper() == 'REQUIRED':
                    cert_reqs = ssl.CERT_REQUIRED
                if self.ssl_options['cert_reqs'].upper() == 'OPTIONAL':
                    cert_reqs = ssl.CERT_OPTIONAL
            else:
                cert_reqs = ssl.CERT_OPTIONAL
            if 'ca_certs' in self.ssl_options:
                ca_certs = self.ssl_options['ca_certs']
            else:
                ca_certs = None
            if 'do_handshake_on_connect' in self.ssl_options:
                do_handshake_on_connect = self.ssl_options['do_handshake_on_connect']
            else:
                do_handshake_on_connect = True
            #pdb.set_trace()
            if 'suppress_ragged_eofs' in self.ssl_options:
                suppress_ragged_eofs = self.ssl_options['suppress_ragged_eofs']
            else:
                suppress_ragged_eofs = True


            self.ssl = ssl.wrap_socket(self.socket,
                       keyfile=keyfile,
                       certfile=certfile,
                       server_side=server_side,
                       cert_reqs=cert_reqs,
                       ssl_version=ssl_version,
                       ca_certs=ca_certs,
                       do_handshake_on_connect=do_handshake_on_connect,
                       suppress_ragged_eofs=True,
                       ) 
            self.set_socket(self.ssl)
    
    
    def execute(self, command, *params, **kwargs):
        """ This places an IRC command on the output queue. If you wish to use
        a trailing perameter, set it as a keyword argument, like so:
        
            >>> self.execute("PRIVMSG", "#channel", trailing="Hello!")
        
        """
        params = [x for x in params if x is not None]
        if "trailing" in kwargs:
            params = list(params)
<<<<<<< HEAD
            params.append(":%s" % kwargs["trailing"])
        self.push("%s %s\r\n" % (command.upper(), " ".join(params)))
=======
            if kwargs["trailing"] is not None:
                params.append(":%s" % kwargs["trailing"])
        self.push(("%s %s\r\n" % (command.upper(), " ".join(params)))
            .encode("utf_8", "replace"))
>>>>>>> remotes/origin/pipeep-patch-set
    
    
    def handle_line(self, prefix, command, params):
        """ This gets called when one single line is ready to get handled. It
        is provided the three main parts of an IRC message. This method is 
        meant to be over-ridden or replaced.
        
        """
        raise NotImplementedError("handle_line() must be overridden.")
    
    
    def start(self):
        """ This causes the connection to begin sending and receiving data. It
        starts a private asyncore loop so if you want to run multiple bots
        on the same loop DO NOT call ``start()`` and instead call 
        ``ircutils.start_all()`` after they have been instantiated.
        
        """
        asyncore.loop(map=self._map)
    
    
    def _ssl_send(self, data):
        """ Replacement for self.send() during SSL connections. """
        try:
            result = self.socket.send(data)
            return result
        except ssl.SSLError as why:
            if why[0] == asyncore.EWOULDBLOCK:
                return 0
            else:
                raise ssl.SSLError(why)
            return 0
        
        
    def _ssl_recv(self, buffer_size):
        """ Replacement for self.recv() during SSL connections. """
        try:
            data = self.socket.recv(buffer_size)
            if not data:
                self.handle_close()
                return ''
            return data
        except ssl.SSLError as why:
            if why[0] in [asyncore.ECONNRESET, asyncore.ENOTCONN, 
                          asyncore.ESHUTDOWN]:
                self.handle_close()
                return ''
            elif why[0] == errno.ENOENT:
                # Required in order to keep it non-blocking
                return ''
            else:
                raise
