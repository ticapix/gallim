import tornado.web

from . import facebook
from . import google

routes = [
          tornado.web.URLSpec(r'/auth/google', google.GoogleLoginHandler, name='auth.google'),
          tornado.web.URLSpec(r'/auth/facebook/(?P<uuid>[a-z0-9]+)', facebook.FacebookGraphLoginHandler, name='auth.facebook'),
          tornado.web.URLSpec(r'/auth/fb_reverse/(?P<path>.*)', facebook.FbReverseSSEHandler, name='auth.fb_reverse'),
          ]
