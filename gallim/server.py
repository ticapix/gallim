#!/usr/bin/env python3
import hashlib
import logging
import tornado.autoreload
import tornado.httpserver
import tornado.gen
import tornado.options
import tornado.web
import traceback
import os

import auth

tornado.options.define('conf', default=os.path.join(os.path.dirname(__file__), 'config.conf'), help='User configuration')
tornado.options.define('port', default=8000, help='TCP port to listen')
tornado.options.define('template_gallery_title', default='', help='Your Gallery name')
tornado.options.define('facebook_reverse_url', default='http://ks355126.kimsufi.com:8001', help='Facebook login reverse proxy')


TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates')
STATIC_PATH = os.path.join(os.path.dirname(__file__), 'static')

logger = logging.getLogger("tornado.application")


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


    def get_current_user(self):
        user_json = self.get_secure_cookie("gallim_user")
        print(user_json)
        if not user_json: return None
        return tornado.escape.json_decode(user_json)

    @tornado.gen.coroutine
    def _fetch_async(self, req):
        http_client = tornado.httpclient.AsyncHTTPClient()
        try:
            ans = yield http_client.fetch(req)
        except tornado.httpclient.HTTPError as e:
            if e.response is None:
                msg = "'%s'" % (req.url)
            else:
                msg = "'%s': %s" % (req.url, e.response.body.decode('utf-8'))
            raise tornado.web.HTTPError(e.code, msg)
        return ans


class HtmlTemplateHandler(BaseHandler):
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


class PublicHtmlTemplateHandler(BaseHandler):
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


def setup_application(template_path, static_path, **kwargs):
    cookie_secret = hashlib.md5()
    cookie_secret.update(__file__.encode('ascii'))
    settings = {
                "cookie_secret": cookie_secret.digest(),
                "login_url": "login",
                "static_path": os.path.abspath(static_path),
                "template_path": os.path.abspath(template_path),
                "debug": True,
                }
    settings.update(kwargs)
    routes = [
              tornado.web.URLSpec(r'/public/html/(?P<template_name>\w+)', PublicHtmlTemplateHandler, name='public_html'),
              tornado.web.URLSpec(r'/html/(?P<template_name>\w+)', HtmlTemplateHandler, name='html'),
              tornado.web.URLSpec(r'/?', HtmlTemplateHandler),
              ]
    routes.extend(auth.routes)
    application = tornado.web.Application(routes, **settings)
    application.settings['login_url'] = application.reverse_url('public_html', application.settings['login_url'])
    return application


if __name__ == '__main__':
    tornado.options.parse_command_line()
    if os.path.isfile(tornado.options.options.conf):
        tornado.autoreload.watch(tornado.options.options.conf)
        tornado.options.parse_config_file(tornado.options.options.conf)
    logging.getLogger("tornado.application").setLevel(logging.DEBUG)
#    database = models.BuildDB(tornado.options.options.database_file)
    application = setup_application(TEMPLATE_PATH, STATIC_PATH)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(tornado.options.options.port)
#    tornado.ioloop.PeriodicCallback(functools.partial(look_for_new_builds, database), 20 * 60 * 1000).start()  # 20 mins
    tornado.ioloop.IOLoop.instance().start()
