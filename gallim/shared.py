import tornado.web
import traceback
import logging

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
        print("user_json", user_json)
        if not user_json: return None
        return tornado.escape.json_decode(user_json)

    @tornado.gen.coroutine
    def _fetch_async(self, req):
        http_client = tornado.httpclient.AsyncHTTPClient()
        logger.debug("fetching %s" % req.url)
        try:
            ans = yield http_client.fetch(req)
        except tornado.httpclient.HTTPError as e:
            if e.response is None:
                msg = "'%s'" % (req.url)
            else:
                msg = "'%s': %s" % (req.url, e.response.body.decode('utf-8'))
            raise tornado.web.HTTPError(e.code, msg)
        logger.debug("done")
        return ans

