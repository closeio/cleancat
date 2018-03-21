import unittest

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

from cleancat.sqla import object_as_dict


class ObjectAsDictTestCase(unittest.TestCase):

    def test_object_as_dict(self):
        Base = declarative_base()

        class Person(Base):
            __tablename__ = 'cleancattest'
            id = sa.Column(sa.Integer, primary_key=True)
            name = sa.Column(sa.String)
            age = sa.Column(sa.Integer)

        steve = Person(name='Steve', age=30)
        assert object_as_dict(steve) == {
            'id': None,
            'age': 30,
            'name': 'Steve'
        }


if __name__ == '__main__':
    unittest.main()
