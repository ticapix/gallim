import json
import logging
import tornado.auth
import tornado.gen
import urllib.parse

from gallim.shared import BaseHandler

logger = logging.getLogger("tornado.application")


class GoogleLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.gen.coroutine
    def get(self):
        if self.get_argument("openid.mode", None):
            user = yield self.get_authenticated_user()
            logger.debug("received user %s" % user)
            # Save the user with e.g. set_secure_cookie()
            self.set_secure_cookie("gallim_user", json.dumps(dict([[k, user[k]] for k in ["name", "locale", "email"]])))
            if user is not None:
                self.set_secure_cookie("gallim_user", json.dumps(dict([[k, user[k]] for k in ["name", "locale", "email"]])))
            else:
                logger.info("registration failed")
            referer = self.request.headers.get('referer', self.reverse_url('html', 'main'))
            query = urllib.parse.urlparse(referer).query
            redirect = urllib.parse.parse_qs(query).get('next', [referer])
            self.redirect(redirect[0])
        else:
            yield self.authenticate_redirect()
