'''
Base functionalities to access pco and send mails
'''

import logging
import requests
from requests.auth import HTTPBasicAuth

# example constant variable
NAME = "pco_mail"
PCO_URL = 'https://api.planningcenteronline.com'


def access_pco(app_id, token):
    '''
    access pco for testing
    '''
    auth = HTTPBasicAuth(app_id, token)

    response = requests.get(PCO_URL + '/services/v2/', auth=auth, timeout=1000)

    logging.info(response.status_code)
    logging.debug(response.json())
