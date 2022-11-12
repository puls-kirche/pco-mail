"""
Base functionalities to access pco and send mails
"""

import logging
import json
import requests
from requests.auth import HTTPBasicAuth

# example constant variable
NAME = "pco_mail"
PCO_URL = "https://api.planningcenteronline.com"


def access_pco(app_id, token):
    """
    access pco for testing
    """
    auth = HTTPBasicAuth(app_id, token)

    response = requests.get(PCO_URL + "/services/v2/", auth=auth, timeout=1000)

    # logging.info(response.status_code)
    # logging.debug(response.json())

    response = requests.get(PCO_URL + "/people/v2/people",
                            auth=auth, timeout=1000)

    name_list = []
    res = json.loads(response.text)
    for nested_array in res['data']:
        identifier = nested_array['id']
        name = nested_array['attributes']['name']

        response = requests.get(PCO_URL + "/people/v2/people/"
                                + nested_array['id'] + "/emails",
                                auth=auth, timeout=1000)

        res = json.loads(response.text)
        for nested_mail in res['data']:
            mail = nested_mail['attributes']['address']
        name_list.append({"person": [{"id": identifier},
                                     {"name": name},
                                     {"mail": mail}]})

    # Show json
    # print(name_list)

    # logging.info(response.status_code)
    # print(json.dumps(response.json()))
