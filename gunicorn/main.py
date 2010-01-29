# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.


import logging
import optparse as op
import os
import resource
import sys

from gunicorn.arbiter import Arbiter

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG
}

UMASK = 0
MAXFD = 1024
if (hasattr(os, "devnull")):
   REDIRECT_TO = os.devnull
else:
   REDIRECT_TO = "/dev/null"


def options():
    return [
        op.make_option('--host', dest='host',
            help='Host to listen on. [%default]'),
        op.make_option('--port', dest='port', type='int',
            help='Port to listen on. [%default]'),
        op.make_option('--workers', dest='workers', type='int',
            help='Number of workers to spawn. [%default]'),
        op.make_option('-p','--pid', dest='pidfile',
            help='set the background PID FILE'),
        op.make_option('-D', '--daemon', dest='daemon',
            help='Run daemonized in the background.'),
        op.make_option('--log-level', dest='loglevel', default='info',
            help='Log level below which to silence messages. [%default]'),
        op.make_option('--log-file', dest='logfile', default='-',
            help='Log to a file. - is stdout. [%default]'),
        op.make_option('-d', '--debug', dest='debug', action="store_true",
            default=False, help='Debug mode. only 1 worker.')
    ]

def configure_logging(opts):
    handlers = []
    if opts.logfile != "-":
        handlers.append(logging.FileHandler(opts.logfile))
    else:
        handlers.append(logging.StreamHandler())

    loglevel = LOG_LEVELS.get(opts.loglevel.lower(), logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(loglevel)
    for h in handlers:
        h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(h)
    return logger
        
def daemonize(logger):
    if not 'GUNICORN_FD' in os.environ:
        if os.fork() == 0: 
            os.setsid()
            if os.fork() == 0:
                os.umask(UMASK)
            else:
                os._exit(0)
        else:
            os._exit(0)

        import resource		# Resource usage information.
        
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if (maxfd == resource.RLIM_INFINITY):
            maxfd = 1024
            
        # Iterate through and close all file descriptors.
        for fd in range(0, maxfd):
            try:
                os.close(fd)
            except OSError:	# ERROR, fd wasn't open to begin with (ignored)
                pass
        
        
        os.open(REDIRECT_TO, os.O_RDWR)
        os.dup2(0, 1)
        os.dup2(0, 2)
        
def main(usage, get_app):
    parser = op.OptionParser(usage=usage, option_list=options())
    opts, args = parser.parse_args()
    logger = configure_logging(opts)

    app = get_app(parser, opts, args)
    workers = opts.workers or 1
    if opts.debug:
        workers = 1
        
    host = opts.host or '127.0.0.1'
    port = opts.port
    if port is None:
        if ':' in host:
            host, port = host.split(':', 1)
            port = int(port)
        else:
            port = 8000
            
    kwargs = dict(
        debug=opts.debug,
        pidfile=opts.pidfile
    )
    

    arbiter = Arbiter((host,port), workers, app, 
                    **kwargs)
    if opts.daemon:
        daemonize(logger)
    arbiter.run()
    
def paste_server(app, global_conf=None, host="127.0.0.1", port=None, 
            *args, **kwargs):
    logger = configure_logging(opts)
    if not port:
        if ':' in host:
            host, port = host.split(':', 1)
        else:
            port = 8000
    bind_addr = (host, int(port))
    
    workers = kwargs.get("workers", 1)
    if global_conf:
        workers = int(global_conf.get('workers', workers))
        
    debug = global_conf.get('debug') == "true"
    if debug:
        # we force to one worker in debug mode.
        workers = 1
        
    pid = kwargs.get("pid")
    if global_conf:
        pid = global_conf.get('pid', pid)
        
    daemon = kwargs.get("daemon")
    if global_conf:
        daemon = global_conf.get('daemon', daemonize)
   
    kwargs = dict(
        debug=debug,
        pidfile=pid
    )

    arbiter = Arbiter(bind_addr, workers, app, **kwargs)
    if daemon == "true":
           daemonize(logger)
    arbiter.run()