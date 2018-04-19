# This file is a part of the AnyBlok / Marshmallow api project
#
#    Copyright (C) 2017 Jean-Sebastien SUZANNE <jssuzanne@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from marshmallow.exceptions import ValidationError
from marshmallow.base import FieldABC
from marshmallow.validate import OneOf
from base64 import b64encode, b64decode
from marshmallow.fields import (  # noqa
    Field,
    Raw,
    Nested as FieldNested,
    Dict,
    List,
    String,
    UUID,
    Number,
    Integer,
    Decimal,
    Boolean,
    FormattedString,
    Float,
    DateTime,
    LocalDateTime,
    Time,
    Date,
    TimeDelta,
    Url,
    URL,
    Email,
    Method,
    Function,
    Str,
    Bool,
    Int,
    Constant,
)


class Nested(FieldNested):
    """Inherit marshmallow fields.Nested"""

    @property
    def schema(self):
        """Overload the super property to remove cache

        it is the only way to propagate the context at each call
        """
        self.__schema = None
        return super(Nested, self).schema


class File(Field):

    def _serialize(self, value, attr, data):
        if value:
            return b64encode(value).decode('utf-8')

        return None

    def _deserialize(self, value, attr, data):
        if value:
            return b64decode(value.encode('utf-8'))

        return None


class Text(String):
    """Simple field use to distinct by the class String and Text"""


class JsonCollection(Field):

    def __init__(self, fieldname=None, keys=None, instance='default',
                 cls_or_instance_type=String, *args, **kwargs):
        self.fieldname = fieldname
        self.keys = keys
        self.instance = instance
        if isinstance(cls_or_instance_type, type):
            if not issubclass(cls_or_instance_type, FieldABC):
                raise ValueError('The type of the list elements '
                                 'must be a subclass of '
                                 'marshmallow.base.FieldABC')
            self.container = cls_or_instance_type()
        else:
            if not isinstance(cls_or_instance_type, FieldABC):
                raise ValueError('The instances of the list '
                                 'elements must be of type '
                                 'marshmallow.base.FieldABC')
            self.container = cls_or_instance_type
        super(JsonCollection, self).__init__(*args, **kwargs)

    def _add_to_schema(self, field_name, schema):
        super(JsonCollection, self)._add_to_schema(field_name, schema)
        self.container.parent = self
        self.container.name = field_name

    def get_value_from_field(self, field, keys):
        key = keys[0]
        if len(keys) == 1:
            return field.get(key, None)

        return self.get_value_from_field(field.get(key, {}), keys[1:])

    def _serialize(self, value, attr, obj):
        return self.container._serialize(value, attr, obj)

    def _deserialize(self, value, attr, data):
        return self.container.deserialize(value, attr=attr, data=data)

    def _validate(self, value):
        errors = {}
        instance = self.context.get('instances', {}).get(self.instance, None)
        if instance is None:
            errors['instance'] = (
                "No instance found for wanted instance name %r" % self.instance
            ),

        if not hasattr(instance, self.fieldname):
            errors['fieldname'] = (
                "No fieldname %r found for wanted instance name %r" % (
                    self.fieldname, self.instance
                )
            ),

        field = getattr(instance, self.fieldname, {})
        field_value = self.get_value_from_field(field, self.keys)
        choices = []
        labels = []
        if isinstance(field_value, dict):
            choices = [x for x in field_value.keys()]
            labels = [x for x in field_value.values()]
        elif isinstance(field_value, list):
            choices = labels = field_value
        else:
            errors['instance values'] = (
                "Instance values %r is not a dict or list" % field_value
            ),

        if errors:
            raise ValidationError(
                errors,
            )

        validators = self.container.validators.copy()
        try:
            self.container.validators.append(
                OneOf(choices=choices, labels=labels)
            )
            self.container._validate(value)
        finally:
            self.container.validators = validators
