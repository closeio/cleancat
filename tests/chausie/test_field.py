import datetime
import enum
from typing import Union, Optional, List, Set

import attr
import pytest

from cleancat.chausie.consts import omitted
from cleancat.chausie.field import (
    intfield,
    Error,
    field,
    ValidationError,
    Optional as CCOptional,
    strfield,
    listfield,
    nestedfield,
    enumfield,
    regexfield,
    urlfield,
)
from cleancat.chausie.schema import Schema


@pytest.fixture
def example_schema():
    class ExampleSchema(Schema):
        myint = field(intfield, accepts=("myint", "deprecated_int"))

        @field(parents=(intfield,))
        def mylowint(value: int) -> Union[int, Error]:
            if value < 5:
                return value
            else:
                return Error(msg="Needs to be less than 5")

    return ExampleSchema


def test_basic_happy_path(example_schema):
    test_data = {"myint": 100, "mylowint": 2}
    result = example_schema.clean(test_data)
    assert isinstance(result, example_schema)
    assert result.myint == test_data["myint"]
    assert result.mylowint == test_data["mylowint"]

    assert test_data == result.serialize()


def test_basic_validation_error(example_schema):
    test_data = {"myint": 100, "mylowint": 10}
    result = example_schema.clean(test_data)
    assert isinstance(result, ValidationError)
    assert result.errors == [
        Error(msg="Needs to be less than 5", field=("mylowint",))
    ]


def test_accepts(example_schema):
    test_data = {"deprecated_int": 100, "mylowint": 2}
    result = example_schema.clean(test_data)
    assert isinstance(result, example_schema)
    assert result.myint == test_data["deprecated_int"]

    assert result.serialize() == {
        "myint": test_data["deprecated_int"],
        "mylowint": 2,
    }


def test_serialize_to():
    class MySchema(Schema):
        myint = field(intfield, serialize_to="my_new_int")

    result = MySchema.clean({"myint": 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert result.serialize() == {"my_new_int": 100}


def test_serialize_func():
    def double(value):
        return value * 2

    class MySchema(Schema):
        myint = field(intfield, serialize_func=double)

    result = MySchema.clean({"myint": 100})
    assert isinstance(result, MySchema)
    assert result.myint == 100
    assert result.serialize() == {"myint": 200}


def test_intfield():
    class MySchema(Schema):
        val: int = field(intfield)

    result = MySchema.clean({"val": 5})
    assert isinstance(result, MySchema)
    assert result.val == 5


def test_strfield():
    class UserSchema(Schema):
        name: str

    result = UserSchema.clean({"name": "John"})
    assert isinstance(result, UserSchema)
    assert result.name == "John"


def test_boolfield():
    class UserSchema(Schema):
        active: bool

    result = UserSchema.clean({"active": True})
    assert isinstance(result, UserSchema)
    assert result.active is True


class TestListField:
    def test_listfield_basic(self):
        class UserSchema(Schema):
            aliases = field(listfield(field(strfield)))

        result = UserSchema.clean({"aliases": ["John", "Johnny"]})
        assert isinstance(result, UserSchema)
        assert result.aliases == ["John", "Johnny"]

    def test_listfield_empty(self):
        class UserSchema(Schema):
            aliases = field(listfield(field(strfield)))

        result = UserSchema.clean({"aliases": ["John", "Johnny"]})
        assert isinstance(result, UserSchema)
        assert result.aliases == ["John", "Johnny"]

    def test_listfield_inner_optional(self):
        class UserSchema(Schema):
            aliases = field(
                listfield(field(strfield, nullability=CCOptional()))
            )

        result = UserSchema.clean({"aliases": ["John", None]})
        assert isinstance(result, UserSchema)
        assert result.aliases == ["John", None]

    def test_listfield_chained(self):
        @attr.frozen
        class Alias:
            value: str

        class UserSchema(Schema):
            @field(parents=(listfield(field(strfield)),))
            def aliases(value: List[str]) -> List[Alias]:
                return [Alias(v) for v in value]

        result = UserSchema.clean({"aliases": ["John", "Johnny"]})
        assert isinstance(result, UserSchema)
        assert result.aliases == [Alias(value="John"), Alias(value="Johnny")]

    def test_listfield_parent_context(self):
        @attr.frozen
        class Context:
            valid_suffixes: Set[str]

        def validate_suffix(value: str, context: Context):
            if value not in context.valid_suffixes:
                return Error(msg="Suffix is invalid")
            return value

        class UserSchema(Schema):
            suffixes = field(
                listfield(field(validate_suffix, parents=(strfield,)))
            )

        context_ = Context(valid_suffixes={"Sr", "Jr", "2nd"})
        result = UserSchema.clean({"suffixes": ["Sr", "Jr"]}, context=context_)
        assert isinstance(result, UserSchema)
        assert result.suffixes == ["Sr", "Jr"]

    def test_listfield_context(self):
        @attr.frozen
        class Context:
            valid_suffixes: Set[str]

        class UserSchema(Schema):
            @field(parents=(listfield(field(strfield)),))
            def suffixes(
                value: List[str], context: Context
            ) -> Union[List[str], Error]:
                for suffix in value:
                    if suffix not in context.valid_suffixes:
                        return Error(msg="Suffix is invalid")
                return value

        context_ = Context(valid_suffixes={"Sr", "Jr", "2nd"})
        result = UserSchema.clean({"suffixes": ["Sr", "Jr"]}, context=context_)
        assert isinstance(result, UserSchema)
        assert result.suffixes == ["Sr", "Jr"]


class TestRegexField:
    def test_basic(self):
        class UserSchema(Schema):
            initials: str = regexfield(r"[A-Z]{2}")

        result = UserSchema.clean({"initials": "AA"})
        assert isinstance(result, UserSchema)
        assert result.initials == "AA"

    def test_no_match(self):
        class UserSchema(Schema):
            initials: str = regexfield(r"[A-Z]{2}")

        result = UserSchema.clean({"initials": "A"})
        assert isinstance(result, ValidationError)
        assert result.errors == [
            Error(msg="Invalid input.", field=("initials",))
        ]


class TestDatetimeField:
    def test_basic(self):
        class UserSchema(Schema):
            birthday: datetime.datetime

        result = UserSchema.clean({"birthday": "2000-01-01T4:00:00Z"})
        assert isinstance(result, UserSchema)
        assert result.birthday == datetime.datetime(
            2000, 1, 1, 4, tzinfo=datetime.timezone.utc
        )

    def test_no_match(self):
        class UserSchema(Schema):
            birthday: datetime.datetime

        result = UserSchema.clean({"birthday": "nonsense"})
        assert isinstance(result, ValidationError)
        assert result.errors == [
            Error(msg="Could not parse datetime.", field=("birthday",))
        ]


class TestNullability:
    def test_required_omitted(self):
        class MySchema(Schema):
            myint: int

        result = MySchema.clean({})
        assert isinstance(result, ValidationError)
        assert result.errors == [
            Error(msg="Value is required.", field=("myint",))
        ]

    def test_required_none(self):
        class MySchema(Schema):
            myint: int

        result = MySchema.clean({"myint": None})
        assert isinstance(result, ValidationError)
        assert result.errors == [
            Error(
                msg="Value is required, and must not be None.",
                field=("myint",),
            )
        ]

    def test_optional_omitted(self):
        class MySchema(Schema):
            myint: Optional[int]

        result = MySchema.clean({})
        assert isinstance(result, MySchema)
        assert result.myint is omitted

    def test_optional_none(self):
        class MySchema(Schema):
            myint: Optional[int]

        result = MySchema.clean({"myint": None})
        assert isinstance(result, MySchema)
        assert result.myint is None


class TestNestedField:
    def test_nestedfield_basic(self):
        class InnerSchema(Schema):
            a: str

        class OuterSchema(Schema):
            inner = field(nestedfield(InnerSchema))

        result = OuterSchema.clean({"inner": {"a": "John"}})
        assert isinstance(result, OuterSchema)
        assert isinstance(result.inner, InnerSchema)
        assert result.inner.a == "John"

    def test_nestedfield_with_context(self):
        @attr.frozen
        class Context:
            curr_user_id: str

        class InnerSchema(Schema):
            @field(parents=(strfield,))
            def a(value: str, context: Context) -> str:
                return f"{value}:{context.curr_user_id}"

        class OuterSchema(Schema):
            inner = field(nestedfield(InnerSchema))

        result = OuterSchema.clean(
            {"inner": {"a": "John"}}, context=Context(curr_user_id="user_abc")
        )
        assert isinstance(result, OuterSchema)
        assert isinstance(result.inner, InnerSchema)
        assert result.inner.a == "John:user_abc"


class TestEnumField:
    def test_enumfield_basic(self):
        class Color(enum.Enum):
            BLUE = "blue"
            RED = "red"
            GREEN = "green"

        class MySchema(Schema):
            color = field(enumfield(Color))

        result = MySchema.clean({"color": "blue"})
        assert isinstance(result, MySchema)
        assert isinstance(result.color, Color)
        assert result.color is Color.BLUE

    @pytest.mark.parametrize("bad_value", ["black", 5, object()])
    def test_enumfield_error(self, bad_value):
        class Color(enum.Enum):
            BLUE = "blue"
            RED = "red"
            GREEN = "green"

        class MySchema(Schema):
            color = field(enumfield(Color))

        result = MySchema.clean({"color": bad_value})
        assert isinstance(result, ValidationError)
        assert result.errors == [
            Error(msg="Invalid value for enum.", field=("color",))
        ]


def test_field_self():
    class AliasSchema(Schema):
        @field(parents=(strfield,))
        def value(self, value: str):
            return f"Value:{value}"

    result = AliasSchema.clean({"value": "John"})
    assert isinstance(result, AliasSchema)
    assert result.value == "Value:John"


def test_extendable_fields():
    # we should be able to define reusable/composable fields with their own parents
    # TODO should this be a different function that makes it clearer this only applies parents as validators?
    @field(parents=(strfield,))
    def valuefield(value: str):
        return f"Value:{value}"

    class MySchema(Schema):
        @field(parents=(valuefield,))
        def a(self, value: str):
            return f"a:{value}"

    result = MySchema.clean({"a": "John"})
    assert isinstance(result, MySchema)
    assert result.a == "a:Value:John"


class TestURLField:
    @pytest.mark.parametrize(
        "value",
        [
            "http://x.com",
            "http://♡.com",
            "http://example.com/a?b=c",
            "ftp://ftp.example.com",
            "http://example.com?params=without&path",
            # Russian unicode URL (IDN, unicode path and query params)
            "http://пример.com",
            "http://пример.рф",
            "http://пример.рф/путь/?параметр=значение",
            # Punicode stuff
            "http://test.XN--11B4C3D",
            # http://stackoverflow.com/questions/9238640/how-long-can-a-tld-possibly-be
            # Longest to date (Feb 2017) TLD in punicode format is 24 chars long
            "http://test.xn--vermgensberatung-pwb",
        ],
    )
    def test_in_accepts_valid_urls(self, value):
        class MyUrlSchema(Schema):
            url = field(urlfield())

        result = MyUrlSchema.clean({"url": value})
        assert isinstance(result, MyUrlSchema)
        assert result.url == value

    @pytest.mark.parametrize(
        "value",
        [
            "www.example.com",
            "http:// invalid.com",
            "http://!nvalid.com",
            "http://.com",
            "http://",
            "http://.",
            "invalid",
            "http://ＧＯＯＧＬＥ.com",  # full-width chars are disallowed
            "javascript:alert()",  # TODO "javascript" is a valid scheme. "//" is not a part of some URIs.
        ],
    )
    def test_it_rejects_invalid_urls(self, value):
        class MyUrlSchema(Schema):
            url = field(urlfield())

        result = MyUrlSchema.clean({"url": value})
        assert isinstance(result, ValidationError)
        assert result.errors == [Error(msg="Invalid input.", field=("url",))]

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("http://example.com/a?b=c", "http://example.com/a?b=c"),
            ("ftp://ftp.example.com", "ftp://ftp.example.com"),
            ("www.example.com", "http://www.example.com"),
            ("invalid", None),
        ],
    )
    def test_it_supports_a_default_scheme(self, value, expected):
        class MyUrlSchema(Schema):
            url = field(urlfield(default_scheme="http://"))

        result = MyUrlSchema.clean({"url": value})
        if expected:
            assert isinstance(result, MyUrlSchema)
            assert result.url == expected
        else:
            assert isinstance(result, ValidationError)
            assert result.errors == [
                Error(msg="Invalid input.", field=("url",))
            ]

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("https://example.com/", "https://example.com/"),
            ("example.com/", "https://example.com/"),
            ("http://example.com", None),
        ],
    )
    def test_it_enforces_allowed_schemes(self, value, expected):
        class MyUrlSchema(Schema):
            url = field(
                urlfield(
                    default_scheme="https://", allowed_schemes=["https://"]
                )
            )

        result = MyUrlSchema.clean({"url": value})
        if expected:
            assert isinstance(result, MyUrlSchema)
            assert result.url == expected
        else:
            expected_err_msg = (
                "This URL uses a scheme that's not allowed. You can only "
                "use https://."
            )
            assert isinstance(result, ValidationError)
            assert result.errors == [
                Error(msg=expected_err_msg, field=("url",))
            ]

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("https://example.com/", "https://example.com/"),
            ("ftp://ftp.example.com", "ftp://ftp.example.com"),
            ("example.com/", "https://example.com/"),
            ("javascript://www.example.com/#%0aalert(document.cookie)", None),
        ],
    )
    def test_it_enforces_disallowed_schemes(self, value, expected):
        class MyUrlSchema(Schema):
            url = field(
                urlfield(
                    default_scheme="https://",
                    disallowed_schemes=["javascript:"],
                )
            )

        result = MyUrlSchema.clean({"url": value})
        if expected:
            assert isinstance(result, MyUrlSchema)
            assert result.url == expected
        else:
            assert isinstance(result, ValidationError)
            assert result.errors == [
                Error(
                    msg="This URL uses a scheme that's not allowed.",
                    field=("url",),
                )
            ]

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("https://example.com/", "https://example.com/"),
            ("example.com/", "https://example.com/"),
            ("ftps://storage.example.com", "ftps://storage.example.com"),
        ],
    )
    def test_it_supports_simpler_allowed_scheme_values(self, value, expected):
        class MyUrlSchema(Schema):
            url = field(
                urlfield(
                    default_scheme="https", allowed_schemes=["https", "ftps"]
                )
            )

        result = MyUrlSchema.clean({"url": value})
        assert isinstance(result, MyUrlSchema)
        assert result.url == expected

    @pytest.mark.parametrize("value", [23.0, True])
    def test_it_enforces_valid_data_type(self, value):
        class MyUrlSchema(Schema):
            url = field(
                urlfield(
                    default_scheme="https", allowed_schemes=["https", "ftps"]
                )
            )

        result = MyUrlSchema.clean({"url": value})
        assert isinstance(result, ValidationError)
        assert result.errors == [Error(msg="Unhandled type", field=("url",))]
