# SFDS microservice.py [![CircleCI](https://badgen.net/circleci/github/SFDigitalServices/solarpanel/main)](https://circleci.com/gh/SFDigitalServices/solarpanel) [![Coverage Status](https://coveralls.io/repos/github/SFDigitalServices/solarpanel/badge.svg?branch=main)](https://coveralls.io/github/SFDigitalServices/solarpanel?branch=main)

SFDS Solar Panel Permit Application

## Starter guide
Please see
([SFDS microservice boiler template](https://github.com/SFDigitalServices/microservice-py)

## Get started
Solar Panel expects 2 parameters:
* Form data in ([JSON])(https://www.json.org/json-en.html) format
* A PDF template which form fields that matches the keys in the form
and passes these to the ([SFDS PDF Generator])(https://github.com/SFDigitalServices/pdf-generator)

It then calls the ([SFDS Email Microservice])(https://github.com/SFDigitalServices/email-microservice-py) to send emails to Applicant and DBI Staff with the generated PDF as an attachment

### Usage
Make a HTTP POST to the deployed URL with
    HTTP header of ACCESS_KEY and TEMPLATE_FILE(see sample.pdf)
    Form data, see sample-data.json


