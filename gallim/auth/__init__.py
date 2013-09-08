import tornado.web

from . import facebook
from . import google

routes = [
          tornado.web.URLSpec(r'/auth/google', google.GoogleLoginHandler, name='auth.google'),
          tornado.web.URLSpec(r'/auth/facebook/(?P<reverse_session_id>[a-z0-9]*)', facebook.FacebookGraphLoginHandler, name='auth.facebook'),
          ]
