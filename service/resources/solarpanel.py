"""Welcome export module"""
import os
import json
import time
import logging
import requests
import falcon
import jsend
import sentry_sdk
from .hooks import validate_access

ERROR_GENERIC = "Bad Request"
ERROR_401 = "Unauthorized"
ERROR_PDF = "Unable to generate pdf"

@falcon.before(validate_access)
class SolarPanel():
    """Export class"""
    def on_post(self, req, resp):
        #pylint: disable=no-self-use,too-many-locals
        """
        on post request
        """
        try:
            data = json.loads(req.bounded_stream.read())
            pdf = self.get_pdf(data['request']['data'], req.get_header('TEMPLATE_FILE'))
            if pdf.content:
                filename = "generated_pdf_" + str(time.time()) + ".pdf"
                # stored the generated pdf in a tmp folder, to be removed later
                temp_file= os.path.dirname(__file__) + "/tmp/" + filename
                #writes pdf to a local temp file because sending pdf bytes to a json stream is complicated
                with open(temp_file, 'wb') as fd:
                    fd.write(pdf.content)
                    fd.close()

                emails = {
                    "to": req.get_header('EMAIL_TO'),
                    "from": req.get_header('EMAIL_FROM'),
                    "reply-to": req.get_header('REPLY-TO')
                }
                # allow access to the generated pdf for email attachment
                file_url = req.url.replace("solarpanel", "static") + "/" + filename
                self.send_email(pdf.content, emails, file_url)
            else:
                raise ValueError(ERROR_PDF)

            resp.body = json.dumps(jsend.success({'message': 'success', 'responses':len(pdf.content)}))
            resp.status = falcon.HTTP_200
            sentry_sdk.capture_message('Solar Panel', 'info')

        #pylint: disable=broad-except
        except Exception as exception:
            logging.exception('Export.on_get Exception')
            resp.status = falcon.HTTP_500

            msg_error = ERROR_GENERIC
            if exception.__class__.__name__ == 'ValueError':
                msg_error = "{0}".format(exception)

            resp.body = json.dumps(jsend.error(msg_error))

    #pylint: disable=no-self-use,too-many-locals
    def send_email(self, pdf, emails, file_url):
        """
        send emails applicant and staff
        """
        subject = "Confirmation for Solar Panel Permit Application"
        file_name = "Completed-SolarWS.pdf"
        payload = {
            "attachments": [
                {
                    "content": "",
                    "path": file_url,
                    "filename": file_name,
                    "type": "application/pdf"
                }
            ],
            "to": [
                    {
                        "email": emails['to'] ,
                        "name": emails.get('to_name', 'Applicant name')
                    }
                ],
            "from": {
                "email": emails['from'],
                "name": emails.get('from_name', 'DBI Staff')
                },
            "content": [
                {
                    "type": "text/html",
                    "value": "<html><p>Hello, world! Welcome to DS</p> </html>"
                },
                {
                "type": "text/custom",
                "value": "Hello world - custom type"
                }
            ],
            "subject": subject
        }
        headers = {
            'x-apikey': os.environ.get('X_APIKEY'),
            'Content-Type': 'application/json',
            'Accept': 'text/plain'
        }
        result = None
        json_data = json.dumps(payload)

        try:
            result = requests.post(
                os.environ.get('EMAIL_SERVICE_URL'),
                headers=headers,
                data=json_data)
        except requests.exceptions.HTTPError as errh:
            logging.exception("HTTPError: %s", errh)
        except requests.exceptions.ConnectionError as errc:
            logging.exception("Error Connecting: %s", errc)
        except requests.exceptions.Timeout as errt:
            logging.exception("Timeout Error: %s", errt)
        except requests.exceptions.RequestException as err:
            logging.exception("OOps: Something Else: %s", err)

        return result

    #pylint: disable=no-self-use,too-many-locals
    def get_pdf(self, payload, template_file_url):
        """
        Generate PDF from SFDS pdf-generator
        """

        headers = {
            'ACCESS_KEY': os.environ.get('PDF_GENERATOR_ACCESS_KEY'),
            'TEMPLATE_FILE': template_file_url,
            'Content-Type': 'application/json'
        }

        result = None
        try:
            result = requests.post(
                os.environ.get('PDF_GENERATOR_URL'),
                headers=headers,
                json=payload)
        except requests.exceptions.HTTPError as errh:
            logging.exception("HTTPError: %s", errh)
        except requests.exceptions.ConnectionError as errc:
            logging.exception("Error Connecting: %s", errc)
        except requests.exceptions.Timeout as errt:
            logging.exception("Timeout Error: %s", errt)
        except requests.exceptions.RequestException as err:
            logging.exception("OOps: Something Else: %s", err)

        return result
