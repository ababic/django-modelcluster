import datetime


TIMEFIELD_DERIVATIVE_EXPRESSIONS = {"hour", "minute", "second"}
DATEFIELD_DERIVATIVE_EXPRESSIONS = {
    "year",
    "iso_year",
    "month",
    "day",
    "week",
    "week_day",
    "iso_week_day",
    "quarter",
}
DATETIMEFIELD_DERIVATIVE_EXPRESSIONS = (
    {"date", "time"}
    | TIMEFIELD_DERIVATIVE_EXPRESSIONS
    | DATEFIELD_DERIVATIVE_EXPRESSIONS
)
COMPARISON_VALUE_CONVERTERS = {
    "year": int,
    "iso_year": int,
    "month": int,
    "hour": int,
    "minute": int,
    "second": int,
    "day": int,
    "week": int,
    "week_day": int,
    "iso_week_day": int,
    "quarter": int,
    "date": datetime.date,
    "time": datetime.time,
}


def derive_from_value(value, expr):
    if isinstance(value, datetime.datetime):
        return derive_from_datetime(value, expr)
    if isinstance(value, datetime.date):
        return derive_from_date(value, expr)
    if isinstance(value, datetime.time):
        return derive_from_time(value, expr)
    return None


def derive_from_time(value, expr):
    """
    Mimics the behaviour of the ``hour``, ``minute`` and ``second`` lookup
    expressions that Django querysets support for ``TimeField`` and
    ``DateTimeField``, by extracting the relevant value from an in-memory
    ``time`` or ``datetime`` value.
    """
    if expr == "hour":
        return value.hour
    if expr == "minute":
        return value.minute
    if expr == "second":
        return value.second
    raise ValueError(
        "Expression '{expression}' is not supported for {value}".format(
            expression=expr, value=repr(value)
        )
    )


def derive_from_date(value, expr):
    """
    Mimics the behaviour of the ``year``, ``iso_year`` ``month``, ``day``,
    ``week``, ``week_day``, ``iso_week_day`` and ``quarter`` lookup
    expressions that Django querysets support for ``DateField`` and
    ``DateTimeField`` columns, by extracting the relevant value from an
    in-memory ``date`` or ``datetime`` value.
    """
    if expr == "year":
        return value.year
    if expr == "iso_year":
        return value.isocalendar()[0]
    if expr == "month":
        return value.month
    if expr == "day":
        return value.day
    if expr == "week":
        return value.isocalendar()[1]
    if expr == "week_day":
        v = value.isoweekday()
        return 1 if v == 7 else v + 1
    if expr == "iso_week_day":
        return value.isoweekday()
    if expr == "quarter":
        return (value.month - 1) // 3 + 1
    raise ValueError(
        "Expression '{expression}' is not supported for {value}".format(
            expression=expr, value=repr(value)
        )
    )


def derive_from_datetime(value, expr):
    """
    Mimics the behaviour of the ``date``, ``time`` and other lookup
    expressions that Django querysets support for ``DateTimeField`` columns,
    by extracting the relevant value from an in-memory ``datetime`` value.
    """
    if expr == "date":
        return value.date()
    if expr == "time":
        return value.time()
    if expr in TIMEFIELD_DERIVATIVE_EXPRESSIONS:
        return derive_from_time(value, expr)
    if expr in DATEFIELD_DERIVATIVE_EXPRESSIONS:
        return derive_from_date(value, expr)
    raise ValueError(
        "Expression '{expression}' is not supported for {value}".format(
            expression=expr, value=repr(value)
        )
    )
