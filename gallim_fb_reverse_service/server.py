#!/usr/bin/env python3

import tornado.web
import json
import logging
import os
import tornado.autoreload
import tornado.options
import tornado.httpserver
import tornado.ioloop
import traceback

logger = logging.getLogger("tornado.application")

tornado.options.define('port', default=8001, help='TCP port to listen')
tornado.options.define('conf', default=os.path.join(os.path.dirname(__file__), 'config.conf'), help='User configuration')


class BaseHandler(tornado.web.RequestHandler):
    def write_error(self, status_code, **kwargs):
        exc_type, exc_value, exc_traceback = kwargs["exc_info"]
        logger.error("status_code %s: %s" % (status_code, exc_value))
        logger.error("traceback: %s" % ''.join(traceback.format_tb(exc_traceback)))
        msg = "error %s" % exc_value
        if exc_type == tornado.web.HTTPError:
            msg = "%s" % exc_value.log_message
        if self.application.settings.get('debug', False):
            self.write(msg)  # return custom error message in the body


class SSEHandler(BaseHandler):
    def initialize(self):
        self.set_header('Content-Type', 'text/event-stream')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Connection', 'keep-alive')

    def emit(self, data, event=None):
        """ Actually emits the data to the waiting JS """
        response = ''
        encoded_data = json.dumps(data)
        if event != None:
            response += 'event: ' + event.strip() + '\n'
        response += 'data: ' + encoded_data.strip() + '\n\n'
        self.write(response)
        self.flush()


class ListennerSSEHandler(SSEHandler):
    def initialize(self, endpoints):
        super().initialize()
        self._endpoints = endpoints

    @tornado.web.asynchronous
    def get(self, endpoint_id):
        if endpoint_id in self._endpoints:
            raise tornado.web.HTTPError(400, "%s is already listenning" % endpoint_id)
        if 'referer' not in self.request.headers:
            raise tornado.web.HTTPError(400, "missing header 'Referer'")
        self._endpoint_id = endpoint_id
        self._endpoints[endpoint_id] = [self.request.headers['referer']]
        logger.debug("adding listenner %s" % self._endpoint_id)

    def on_connection_close(self):
        logger.debug("deleting listenner %s" % self._endpoint_id)
        del self._endpoints[self._endpoint_id]


class ForwardHandler(BaseHandler):
    def initialize(self, endpoints):
        super().initialize()
        self._endpoints = endpoints

    def get(self, endpoint_id):
        if endpoint_id not in self._endpoints:
            raise tornado.web.HTTPError(400, "unknown listenner %s" % endpoint_id)
        referer = self._endpoints[endpoint_id][0]
        redirect = referer + self.request.uri[len(endpoint_id)+1:]
        logger.debug("%s forwarding to %s" % (endpoint_id, referer))
        self.redirect(redirect)



def setup_application(**kwargs):
    endpoints = {}
    settings = {
                "debug": True if tornado.options.options.logging == 'debug' else False
                }
    settings.update(kwargs)
    routes = [
              tornado.web.URLSpec(r'/listen/(?P<endpoint_id>\w+)', ListennerSSEHandler, {'endpoints': endpoints}),
              tornado.web.URLSpec(r'/(?P<endpoint_id>\w+)(?:/?.*)', ForwardHandler, {'endpoints': endpoints}),
              (r"/?", tornado.web.RedirectHandler, {"url": "https://github.com/ticapix/gallim"}),
              ]
    application = tornado.web.Application(routes, **settings)
    return application


if __name__ == '__main__':
    tornado.options.parse_command_line()
    if os.path.isfile(tornado.options.options.conf):
        tornado.autoreload.watch(tornado.options.options.conf)
        tornado.options.parse_config_file(tornado.options.options.conf)
    application = setup_application()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
