"""Welcome export module"""
import os
import json
import time
import logging
import pathlib
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
            if data['request']:
                self.prepare_data(data['request'])
                print(data['request'])
                pdf = self.get_pdf(data['request']['data'], req.get_header('TEMPLATE_FILE'))
                if pdf.content:
                    filename = "generated_pdf_" + str(time.time()) + ".pdf"
                    # stored the generated pdf in a tmp folder, to be removed later
                    temp_file= os.path.dirname(__file__) + "/tmp/" + filename
                    #writes pdf to a local temp file because sending pdf bytes to a json stream(encoding) is complicated
                    with open(temp_file, 'wb') as fd:
                        fd.write(pdf.content)
                        fd.close()
                    emails = self.get_emails(data['request']['emails'])
                    if emails:
                        # allow access to the generated pdf for email attachment
                        file_url = req.url.replace("solar-panel", "static") + "/" + filename
                        self.send_email(data['request'], emails, file_url, 'staffs')
                        #self.send_email(data['request'], emails, file_url, 'applicants')
                else:
                    raise ValueError(ERROR_PDF)

            resp.body = json.dumps(jsend.success({'message': 'success', 'responses':len(pdf.content)}))
            resp.status = falcon.HTTP_200
            sentry_sdk.capture_message('Solar Panel', 'info')

        #pylint: disable=broad-except
        except Exception as exception:
            logging.exception('SolarPanel.on_post Exception')
            resp.status = falcon.HTTP_500

            msg_error = ERROR_GENERIC
            if exception.__class__.__name__ == 'ValueError':
                msg_error = "{0}".format(exception)

            resp.body = json.dumps(jsend.error(msg_error))

    #pylint: disable=no-self-use,too-many-locals
    def send_email(self, request, emails, file_url, type):
        """
        send emails applicant and staff
        """
        template = {
            "url": request["staff_email_template"],
            "replacements": {
                "data": request
            }
        }
        subject = request['data']["ContractorApplicantName"] + " applied for a solar permit at " + request['data']["projectAddress"]
        email_to = emails["staffs"]
        #applicant email
        if type == "applicants":
            subject = "You applied for a solar permit at " + request['data']["projectAddress"]
            email_to = emails["applicants"]
            template = {
                "url": request["applicant_email_template"],
                "replacements": {
                    "data": request['data']
                }
            }

        file_name = "Completed-SolarWS.pdf"
        payload = {
            "subject": subject,
            "attachments": [
                {
                    "content": "",
                    "path": file_url,
                    "filename": file_name,
                    "type": "application/pdf"
                }
            ],
            "to": email_to,
            "from": emails["from"],
            "template": template
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
    def prepare_data(self, request):
        """
        Prepare form data for pdf geeneration and email
        """
        # update file upload names
        project_address = request['data']["projectAddress"]
        fe = pathlib.Path(request['data']["planDrawings"][0]["originalName"]).suffix
        request['data']["planDrawings"][0]["originalName"] = project_address + "-plans" + fe
        fe = pathlib.Path(request['data']["dataSheets"][0]["originalName"]).suffix
        request['data']["dataSheets"][0]["originalName"] = project_address + "-cut" + fe
        if request['data']['structuralReview']:
            fe = pathlib.Path(request['data']["structuralReview"][0]["originalName"]).suffix
            request['data']["structuralReview"][0]["originalName"] = project_address + "-str" + fe

        # flatten lists into string
        request['data']['occupancyClass'] = ", ".join(str(x) for x in request['data']['occupancyClass'])

        # flatten multiple checkboxes
        cb = []
        for k,v in request['data']['LicenseClass'].items():
            if v:
                if k == "Other":
                    cb.append(request['data']['OtherLicenseClass'])
                else:
                    cb.append(k)
        request['data']['LicenseClass'] = ", ".join(cb)

        # logic for applicant name/email
        if request['data']['whatIsYourRoleInThisProject'] == 'propertyOwner':
            email = request['data']['ownersEmailAddress']
            name = request['data']['OwnerName']
        elif request['data']['whatIsYourRoleInThisProject'] == 'contractor':
            email = request['data']['ApplicantEmailAddress']
            name = request['data']['ContractorApplicantName']
        else:
            email = request['data']['yourEmail']
            name = request['data']['yourName']

        request['emails']['applicants'][0]['email'] = email
        request['emails']['applicants'][0]['name'] = name

    #pylint: disable=no-self-use,too-many-locals
    def get_emails(self, emails):
        """
        get email information from payload
        """
        email_info = {}
        if emails["from"]:
            email_info["from"] = {
                "email": emails["from"]["email"],
                "name": emails["from"]["name"]
            }
        if emails["applicants"]:
            email_info["applicants"] = []
            for email in emails["applicants"]:
                email_info["applicants"].append({
                    "email": email["email"],
                    "name": email["name"]
                })
        if emails["staffs"]:
            email_info["staffs"] = []
            for email in emails["staffs"]:
                email_info["staffs"].append({
                    "email": email["email"],
                    "name": email["name"]
                })
        return email_info

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

