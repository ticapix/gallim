import logging
import tornado.auth
import tornado.gen

from gallim.shared import BaseHandler

logger = logging.getLogger("tornado.application")


class GoogleLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.gen.coroutine
    def get(self):
        if self.get_argument("openid.mode", None):
            user = yield self.get_authenticated_user()
            logger.debug("received user %s" % user)
            # Save the user with e.g. set_secure_cookie()
        else:
            yield self.authenticate_redirect()
