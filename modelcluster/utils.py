import datetime
from functools import lru_cache
from django.core.exceptions import FieldDoesNotExist
from django.db.models import (
    DateField,
    DateTimeField,
    ManyToManyField,
    ManyToManyRel,
    TimeField,
)

from modelcluster import datetime_utils as dt_utils

REL_DELIMETER = "__"


class ManyToManyTraversalError(ValueError):
    pass


class TraversedRelationship:
    __slots__ = ["from_model", "field"]

    def __init__(self, from_model, field):
        self.from_model = from_model
        self.field = field

    @property
    def field_name(self) -> str:
        return self.field.name

    @property
    def to_model(self):
        return self.field.target_model


@lru_cache(maxsize=None)
def get_model_field(model, name):
    """
    Returns a model field matching the supplied ``name``, which can include
    double-underscores (`'__'`) to indicate relationship traversal - in which
    case, the model field will be lookuped up from the related model.

    Multiple traversals for the same field are supported, but at this moment
    in time, only traversal of many-to-one and one-to-one relationships is
    supported.

    Details of any relationships traversed in order to reach the returned
    field are made available as ``field.traversals``. The value is a tuple of
    ``TraversedRelationship`` instances.

    If ``name`` happens to end with ``'__date'``, ``'__time'``, ``'_hour'``, or
    any of the other derivative expressions that Django supports for date,
    time and datetime fields, a ``_convert_raw``  attribute will be added to
    the return value, referencing a callable that should be used to convert
    comparison values to the correct type instead of the field's
    ``to_python()`` method.

    Raises ``FieldDoesNotExist`` if the name cannot be mapped to a model field.

    Raises ``ManyToManyTraversalError`` if a many-to-many relationship is
    encountered.
    """
    subject_model = model
    traversals = []
    field = None
    segments = name.split(REL_DELIMETER)
    for i, field_name in enumerate(segments):

        if field is not None:
            if isinstance(field, (ManyToManyField, ManyToManyRel)):
                raise ManyToManyTraversalError(
                    "The lookup '{name}' from {model} cannot be replicated by "
                    "modelcluster, because the '{field_name}' relationship "
                    "from {subject_model} is a many-to-many, and traversal is "
                    "only supported for one-to-one or many-to-one "
                    "relationships.".format(
                        name=name,
                        model=model,
                        field_name=field_name,
                        subject_model=subject_model,
                    )
                )

            if (
                i == len(segments)
                and field_name in dt_utils.DATETIMEFIELD_DERIVATIVE_EXPRESSIONS
            ):
                if isinstance(field, DateTimeField):
                    field._convert_raw = (
                        dt_utils.COMPARISON_VALUE_CONVERTERS[field_name]
                    )
                    break
                if (
                    isinstance(field, DateField)
                    and field_name in dt_utils.DATEFIELD_DERIVATIVE_EXPRESSIONS
                ):
                    field._convert_raw = (
                        dt_utils.COMPARISON_VALUE_CONVERTERS[field_name]
                    )
                    break
                if (
                    isinstance(field, TimeField)
                    and field_name in dt_utils.TIMEFIELD_DERIVATIVE_EXPRESSIONS
                ):
                    field._convert_raw = (
                        dt_utils.COMPARISON_VALUE_CONVERTERS[field_name]
                    )
                    break

            if getattr(field, "related_model", None):
                traversals.append(TraversedRelationship(subject_model, field))
                subject_model = field.related_model

        try:
            field = subject_model._meta.get_field(field_name)
        except FieldDoesNotExist as e:
            if field_name.endswith("_id"):
                field = subject_model._meta.get_field(field_name[:-3]).target_field
            raise e

    field.traversals = tuple(traversals)
    return field


def extract_field_value(obj, key, pk_only=False, suppress_fielddoesnotexist=False):
    """
    Attempts to extract a field value from ``obj`` matching the ``key`` - which,
    can contain double-underscores (`'__'`) to indicate traversal of relationships
    to related objects, and may also include `'__day'`, `'__hour'` and other
    derivative expressions that Django supports for date, time and datetime fields.

    For keys that specify ``ForeignKey`` or ``OneToOneField`` field values, full
    related objects are returned by default. If only the primary key values are
    required ((.g. when ordering, or using ``values()`` or ``values_list()``)),
    call the function with ``pk_only=True``.

    By default, ``FieldDoesNotExist`` is raised if the key cannot be mapped to
    a model field. Call the function with ``suppress_fielddoesnotexist=True``
    to get ``None`` values instead.
    """
    source = obj
    segments = key.split(REL_DELIMETER)
    value = None
    for i, attr in enumerate(segments, start=1):
        if (
            i > 1
            and i == len(segments)
            and isinstance(
                value, (None, datetime.datetime, datetime.date, datetime.time)
            )
        ):
            # Support derivative expressions for the last segment
            return dt_utils.derive_from_value(value, attr)
        elif hasattr(source, attr):
            value = getattr(source, attr)
            source = value
            continue
        elif suppress_fielddoesnotexist:
            return None
        else:
            raise FieldDoesNotExist(
                "'{name}' is not a valid field name for {model}".format(
                    name=attr, model=type(source)
                )
            )
    if pk_only and hasattr(value, "pk"):
        return value.pk
    return value


def convert_raw_value(field, value):
    # convert value to the correct python type
    if hasattr(field, '_convert_raw'):
        # get_model_field() sets this when a derivative of date, time, or datetime
        # has been requested
        return field._convert_raw(value)
    # use the built-in method for the field
    return field.to_python(value)


def sort_by_fields(items, fields):
    """
    Sort a list of objects on the given fields. The field list works analogously to
    queryset.order_by(*fields): each field is either a property of the object,
    or is prefixed by '-' (e.g. '-name') to indicate reverse ordering.
    """
    # To get the desired behaviour, we need to order by keys in reverse order
    # See: https://docs.python.org/2/howto/sorting.html#sort-stability-and-complex-sorts
    for key in reversed(fields):
        # Check if this key has been reversed
        reverse = False
        if key[0] == "-":
            reverse = True
            key = key[1:]

        def get_sort_value(item):
            # Use a tuple of (v is not None, v) as the key, to ensure that None sorts before other values,
            # as comparing directly with None breaks on python3
            value = extract_field_value(
                item, key, pk_only=True, suppress_fielddoesnotexist=True
            )
            return (value is not None, value)

        # Sort items
        items.sort(key=get_sort_value, reverse=reverse)
