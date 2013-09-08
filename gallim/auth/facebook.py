import json
import logging
import tornado.auth
import tornado.gen
import tornado.options
import tornado.web
import urllib.parse
import uuid

from gallim.shared import BaseHandler

#     client browser         gallim                                reverse service                      FB
#     +                      +                                     +                                    +
#     | /auth/fb             |                                     |                                    |
#     +--------------------->|                                     |                                    |
#     |                      | create session (timeout=10secs)     |                                    |
#     |                      | {referer: gallim_url}               |                                    |
#     |                      +------------------------------------>|                                    |
#     |                      |                                     |                                    |
#     |                      | ask authentification                |                                    |
#     |                      | app_id=<id>                         |                                    |
#     |                      | app_secret=<secret>                 |                                    |
#     |                      | redirect_url=<reverse_session_url>  |                                    |
#     |                      +------------------------------------------------------------------------->|
#     | ask user validation  |                                     |                                    |
#     |<------------------------------------------------------------------------------------------------+
#     | user validation      |                                     |                                    |
#     +----------------------|-------------------------------------|----------------------------------->|
#     |                      |                                     | /reverse_session_url/*?code=<code> |
#     |                      |                                     |<-----------------------------------+
#     | redirect request on gallim_url                             |                                    |
#     |<-----------------------------------------------------------+                                    |
#     |                      |                                     |                                    |
#     +--------------------->|                                     |                                    |
#     |                      |                                     |                                    |
#     |                      | ask user                            |                                    |
#     |                      | app_id=<id>                         |                                    |
#     |                      | app_secret=<secret>                 |                                    |
#     |                      | redirect_url=<reverse_session_url>  |                                    |
#     |                      | code=<code>                         |                                    |
#     |                      +------------------------------------------------------------------------->|
#     |                      |                                     |                                    |
#     |                      |<-------------------------------------------------------------------------+
#     |                      |                                     |                                    |
#     |                      | check user                          |                                    |
#     |<---------------------+                                     |                                    |
#     |                      |                                     |                                    |
#     v                      v                                     v                                    v

logger = logging.getLogger("tornado.application")



class FacebookGraphLoginHandler(BaseHandler, tornado.auth.FacebookGraphMixin):
    @tornado.gen.coroutine
    def get(self, reverse_session_id):
        if 'error_code' in self.request.arguments:
            raise tornado.web.HTTPError(410, tornado.escape.json_encode({'error_code': self.request.arguments['error_code'],
                                                                         'error_message': self.request.arguments['error_message']}))

        if 'protocol' not in self.request.headers:
            logger.warning('could not found header "protocol". Using http by default')
            protocol = 'http'
        else:
            protocol = self.request.headers['protocol']

        if len(reverse_session_id) == 0:  # starting a new session
            reverse_session_id = uuid.uuid4().hex
            sse_params = {'streaming_callback': lambda chunk: None,
                          'headers': tornado.httputil.HTTPHeaders({"referer": "%s://%s" % (protocol, self.request.headers['host'])}),
                          }
            req = tornado.httpclient.HTTPRequest(urllib.parse.urljoin(tornado.options.options['facebook_reverse_url'], 'listen/%s' % reverse_session_id), method='GET', **sse_params)
            tornado.ioloop.IOLoop.current().add_callback(self._fetch_async, req)

        redirect_uri = urllib.parse.urljoin(tornado.options.options['facebook_reverse_url'], '%s%s' % (reverse_session_id, self.reverse_url('auth.facebook', reverse_session_id)))
        if self.get_argument("code", False):
            user = yield self.get_authenticated_user(redirect_uri=redirect_uri,
                                                     client_id=tornado.options.options["facebook_api_key"],
                                                     client_secret=tornado.options.options["facebook_secret"],
                                                     code=self.get_argument("code"),
                                                     extra_fields=['email'],
                                                     )
            logger.debug("received user %s" % user)
            self.set_secure_cookie("gallim_user", json.dumps(dict([[k, user[k]] for k in ["name", "locale", "email"]])))
            self.redirect(self.get_argument("next", self.reverse_url('html', 'main')))
        else:
            yield self.authorize_redirect(redirect_uri=redirect_uri,
                                          client_id=tornado.options.options["facebook_api_key"],
                                          extra_params={"scope": "offline_access,email"},
                                          )
