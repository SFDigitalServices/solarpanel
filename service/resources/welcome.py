"""Welcome example module"""
#pylint: disable=too-few-public-methods
import json
import falcon
import jsend
from .hooks import validate_access

@falcon.before(validate_access)
class Welcome():
    """Welcome class"""
    def on_get(self, _req, resp):
        #pylint: disable=no-self-use
        """on get request
        return Welcome message
        """
        msg = {'message': 'Welcome'}
<<<<<<< HEAD
        resp.text = json.dumps(jsend.success(msg))
=======
        resp.body = json.dumps(jsend.success(msg))
>>>>>>> 06dbc10 (First commit)
        resp.status = falcon.HTTP_200
