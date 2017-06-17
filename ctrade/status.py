from pymongo import MongoClient

class Mongo(object):

    def __init__(self, uri, db):

        self._client = MongoClient(uri)
        self._db = self._client[db]
        self._status = self._db.status

    def __getattr__(self, value):

        return getattr(self._client, value)

    def insert(self, element):

        self._status.insert_one(element)


def create_document():

    document = {'pair': '',
                'position_type': '',
                'price': {'open': '',
                          'close': ''},
                'date': {'open': '',
                         'close': ''}
    }
    return document


def insert(position='open', **kwargs):

    doc = create_document()
    for k,v in kwargs.items():
        if not isinstance(doc[k], dict):
            print k
            doc[k] = v
    doc['price'][position] = kwargs['price']
    doc['date'][position] = kwargs['date']
    return doc


