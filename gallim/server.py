#!/usr/bin/env python3
import hashlib
import logging
import os
import sys
import tornado.autoreload
import tornado.httpserver
import tornado.gen
import tornado.options
import tornado.web

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import gallim.auth
import gallim.shared

tornado.options.define('conf', default=os.path.join(os.path.dirname(__file__), 'config.conf'), help='User configuration')
tornado.options.define('port', default=8000, help='TCP port to listen')
tornado.options.define('template_gallery_title', default='', help='Your Gallery name')
tornado.options.define('facebook_reverse_url', default='http://ks355126.kimsufi.com:8001', help='Facebook login reverse proxy')
tornado.options.define('facebook_api_key', default=194190347420031, help='Gallim FB app ID')
tornado.options.define('facebook_secret', default='bf737edba5ad9761d625335eca101d40', help='Gallim FB app secret')
tornado.options.define('template_path', default=os.path.join(os.path.dirname(__file__), 'templates'), help='HTML template directory')
tornado.options.define('static_path', default=os.path.join(os.path.dirname(__file__), 'static'), help='static file directory (.css, images, .js, ...)')

logger = logging.getLogger("tornado.application")


class HtmlTemplateHandler(gallim.shared.BaseHandler):
    def prepare(self):
        self.tpl_vars = {}
        for config_name, value in tornado.options.options.as_dict().items():
            if config_name.startswith('template_'):
                self.tpl_vars[config_name[len('template_'):]] = value

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self, template_name=None):
        if template_name is None:
            self.redirect(self.reverse_url('html', 'main'))
        if not os.path.isfile(os.path.join(self.application.settings['template_path'], "%s.html" % template_name)):
            raise tornado.web.HTTPError(404, '%s not found' % repr(template_name))
        self.tpl_vars.update(self.request.arguments)
        self.render("%s.html" % template_name, **self.tpl_vars)


class PublicHtmlTemplateHandler(gallim.shared.BaseHandler):
    public_pages = ['login', 'logout']

    def prepare(self):
        self.tpl_vars = {}
        for config_name, value in tornado.options.options.as_dict().items():
            if config_name.startswith('template_'):
                self.tpl_vars[config_name[len('template_'):]] = value

    @tornado.gen.coroutine
    def get(self, template_name=None):
        if template_name not in self.public_pages:
            self.redirect(self.reverse_url('public_html', 'main'))
        if not os.path.isfile(os.path.join(self.application.settings['template_path'], "%s.html" % template_name)):
            raise tornado.web.HTTPError(404, '%s not found' % repr(template_name))
        self.tpl_vars.update(self.request.arguments)
        self.render("%s.html" % template_name, **self.tpl_vars)


def setup_application( **kwargs):
    cookie_secret = hashlib.md5()
    cookie_secret.update(__file__.encode('ascii'))
    settings = {
                "cookie_secret": cookie_secret.digest(),
                "login_url": "login",
                "static_path": os.path.abspath(tornado.options.options.static_path),
                "template_path": os.path.abspath(tornado.options.options.template_path),
                "debug": True if tornado.options.options.logging == 'debug' else False
                }
    settings.update(kwargs)
    routes = [
              tornado.web.URLSpec(r'/public/html/(?P<template_name>\w+)', PublicHtmlTemplateHandler, name='public_html'),
              tornado.web.URLSpec(r'/html/(?P<template_name>\w+)', HtmlTemplateHandler, name='html'),
              tornado.web.URLSpec(r'/?', HtmlTemplateHandler),
              ]
    routes.extend(gallim.auth.routes)
    application = tornado.web.Application(routes, **settings)
    application.settings['login_url'] = application.reverse_url('public_html', application.settings['login_url'])
    return application


if __name__ == '__main__':
    tornado.options.parse_command_line()
    if os.path.isfile(tornado.options.options.conf):
        tornado.autoreload.watch(tornado.options.options.conf)
        tornado.options.parse_config_file(tornado.options.options.conf)
    logging.getLogger("tornado.application").setLevel(logging.DEBUG)
    application = setup_application()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(tornado.options.options.port)
#    tornado.ioloop.PeriodicCallback(functools.partial(look_for_new_builds, database), 20 * 60 * 1000).start()  # 20 mins
    tornado.ioloop.IOLoop.instance().start()
