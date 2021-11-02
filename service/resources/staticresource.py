""" Allow static file """
import os
import falcon

class StaticResource(object):
    def on_get(self, req, resp, filename):
        filename = os.path.dirname(__file__) + "/tmp/" +  filename
        if os.path.exists(filename):
            resp.status = falcon.HTTP_200
            with open(filename, 'rb') as f:
                resp.body = f.read()
        else:
            resp.status = falcon.HTTP_500
            resp.body = "File doesn't exist!"
