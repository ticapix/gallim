import json
import logging
import tornado.auth
import tornado.gen
import tornado.options
import tornado.web
import traceback
import urllib.parse

logger = logging.getLogger("tornado.application")


# GET /a4c8d8e9b23b436098b24432d73a6f21/auth/facebook/a4c8d8e9b23b436098b24432d73a6f21?error_code=901&error_message=This+app+is+in+sandbox+mode.++Edit+the+app+configuration+at+http%3A%2F%2Fdevelopers.facebook.com%2Fapps+to+make+the+app+publicly+visible. (88.196.181.151) 2.82ms
# HTTPRequest(protocol='http', host='ks355126.kimsufi.com:8001', method='GET', uri='/favicon.ico', version='HTTP/1.1', remote_ip='88.196.181.151', headers={'Host': 'ks355126.kimsufi.com:8001', 'Connection': 'keep-alive', 'Accept-Encoding': 'gzip,deflate,sdch', 'Accept-Language': 'en-US,en;q=0.8', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.95 Safari/537.36', 'Accept': '*/*'})


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


class ByteEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.decode('utf-8')
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class FacebookGraphLoginHandler(BaseHandler, tornado.auth.FacebookGraphMixin):
    @tornado.gen.coroutine
    def _fetch(self, req):
        http_client = tornado.httpclient.AsyncHTTPClient()
        logger.debug('fetching %s' % req.url)
        try:
            ans = yield http_client.fetch(req)
        except tornado.httpclient.HTTPError as e:
            if e.response is None:
                msg = "'%s'" % (req.url)
            else:
                msg = "'%s': %s" % (req.url, e.response.body.decode('utf-8'))
            raise tornado.web.HTTPError(e.code, msg)
        return ans

    @tornado.gen.coroutine
    def get(self, uuid):
        self.settings['facebook_api_key'] = 194190347420031
        self.settings['facebook_secret'] = 'bf737edba5ad9761d625335eca101d40'
        redirect_uri = urllib.parse.urljoin(tornado.options.options['facebook_reverse_url'], ''.join([uuid, self.request.uri]))
#        return
        if self.get_argument("code", False):
            user = yield self.get_authenticated_user(redirect_uri=redirect_uri,
                                                     client_id=self.settings["facebook_api_key"],
                                                     client_secret=self.settings["facebook_secret"],
                                                     code=self.get_argument("code"),
                                                     extra_fields=['email'],
                                                     )
            print(json.dumps(user, cls=ByteEncoder))
            self.set_secure_cookie("gallim_user", json.dumps(user, cls=ByteEncoder))
            self.redirect(self.request.headers['Referer'])
        else:
            yield self.authorize_redirect(redirect_uri=redirect_uri,
                                          client_id=self.settings["facebook_api_key"],
                                          extra_params={"scope": "offline_access,email"},
                                          )


class FbReverseSSEHandler(BaseHandler):
    def initialize(self):
        self.set_header('Content-Type', 'text/event-stream')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Connection', 'keep-alive')

    def _streaming_callback(self, chunck):
        self.write(chunck)
        self.flush()

    @tornado.gen.coroutine
    def get(self, path):
        sse_params = {'streaming_callback': self._streaming_callback}
        req = tornado.httpclient.HTTPRequest(urllib.parse.urljoin(tornado.options.options['facebook_reverse_url'], path), method='GET', **sse_params)
        yield self._fetch_async(req)
