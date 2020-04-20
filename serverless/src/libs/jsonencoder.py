import decimal
import json

from datetime import datetime
from sys import byteorder


# This is a workaround for: http://bugs.python.org/issue16535.
class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        """Default conversion method if object is not natively JSON-able."""

        if isinstance(obj, decimal.Decimal):
            return int(obj)

        if isinstance(obj, bytes):
            return int.from_bytes(obj, byteorder)

        if isinstance(obj, datetime):
            return obj.isoformat()

        if self.is_jsonable(obj):
            return obj
        else:
            raise TypeError("Type %s not serializable" % type(obj))

        return super(JsonEncoder, self).default(obj)


    def is_jsonable(self, obj):
        """Helper method to check if object is JSON-able."""

        try:
            json.dumps(obj)
            return True
        except (TypeError, OverflowError):
            return False
