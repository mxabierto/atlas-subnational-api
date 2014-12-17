from flask import abort
from sqlalchemy.ext.hybrid import hybrid_method
from flask.ext import restful

from colombia import ext

db = ext.db


class BaseQuery(db.Query):

    def get_or_abort(self, obj_id, http_code=404):
        """Get an object or return an error code."""
        result = self.get(obj_id)
        return result or abort(http_code)

    def first_or_abort(self, obj_id, http_code=404):
        """Get first result or return an error code."""
        result = self.first()
        return result or abort(http_code)

    def filter_by_enum(self, enum, value, possible_values=None, http_code=400):
        """
        Filters a query object by an enum, testing that it got a valid value.

        :param enum: Enum column from model, e.g. Vehicle.type
        :param value: Value to filter by
        :param possible_values: None or list of acceptable values for `value`
        """
        if value is None:
            return self

        if possible_values is None:
            possible_values = enum.property.columns[0].type.enums

        if value not in possible_values:
            msg = "Expected one of: {0}, got {1}"\
                .format(possible_values, value)
            restful.abort(http_code, message=msg)

        return self.filter(enum == value)


class BaseModel(db.Model):
    __abstract__ = True
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }
    query_class = BaseQuery


class IDMixin:
    """Adds in an autoincremented integer ID."""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self.id)


class LanguageMixin:
    """"
    Mixin to include language support in a database object, plus convenience
    functions.

    - TODO: Write a make_languages(lang_list, string_length) to have this not
    be hardcoded values.
    """
    en = db.Column(db.String(50))
    es = db.Column(db.String(50))

    @hybrid_method
    def localized_name(self, lang):
        return getattr(self, lang)


class HSProduct(BaseModel, IDMixin, LanguageMixin):
    """A product according to the HS4 (Harmonized System) classification.
    Details can be found here: http://www.wcoomd.org/en/topics/nomenclature/instrument-and-tools/hs_nomenclature_2012/hs_nomenclature_table_2012.aspx
    """
    __tablename__ = "product"

    #: Possible aggregation levels
    AGGREGATIONS = [
        "section",
        "2digit",
        "4digit"
    ]
    #: Enum that contains level of aggregation - how many "digits" of detail
    aggregation = db.Column(db.Enum(*AGGREGATIONS))

    #: Canonical name of the product - in non_colloquial english (i.e. name vs
    #: name_en)
    name = db.Column(db.String(50))

    #: HS4 code of the product, in the level of aggregation described in
    #: :py:class:`.aggregation`.
    code = db.Column(db.String(6))

    #: HS4 section of the product, this is deprecated and shouldn't be used.
    #: EVER. I had to stick this in for the alpha demo.
    section_code = db.Column(db.String(6))
    #: HS4 section name of the product, this is deprecated and shouldn't be used.
    #: EVER. I had to stick this in for the alpha demo.
    section_name = db.Column(db.String(6))

    def __repr__(self):
        return "<HSProduct: %d, %s>" % (self.id or -1, self.name or None)


class Location(BaseModel, IDMixin):
    """A geographical location."""
    __tablename__ = "location"
    type = db.Column(db.String(10))
    __mapper_args__ = {
        'polymorphic_identity': 'location',
        'polymorphic_on': type
    }

    #: Possible aggregation levels
    AGGREGATIONS = [
        "municipality",
        "department",
    ]
    #: Enum that contains level of aggregation - municipalities, cities,
    #: regions, departments
    aggregation = db.Column(db.Enum(*AGGREGATIONS))

    #: Name of the location in the most common language
    name = db.Column(db.String(50))

    #: Location code - zip code or DANE code, etc
    code = db.Column(db.String(5))


class Municipality(Location):
    """A municipality that has a 5-digit code. Cities often contain multiple
    municipalities, but there are also standalone municipalities that are not
    part of any city."""

    __tablename__ = "municipality"
    __mapper_args__ = {
        'polymorphic_identity': 'municipality',
    }

    id = db.Column(db.Integer,
                   db.ForeignKey('location.id'), primary_key=True)

    #: Possible sizes of a municipality
    SIZE = [
        "city",
        "midsize",
        "rural"
    ]
    #: Size of the municipality
    size = db.Column(db.Enum(*SIZE))

    population = db.Column(db.Integer)
    nbi = db.Column(db.Numeric)


class Department(Location):
    """A grouping of municipalities to create 32ish areas of the country.
    Departments in Colombia have 2 digit codes, which are the first 2 digits of
    the 5-digit codes of the constituent municipalities."""

    __tablename__ = "department"
    __mapper_args__ = {
        'polymorphic_identity': 'department',
    }

    id = db.Column(db.Integer,
                   db.ForeignKey('location.id'), primary_key=True)

    population = db.Column(db.Integer)
    gdp = db.Column(db.Integer)


class DepartmentProductYear(BaseModel, IDMixin):

    __tablename__ = "department_product_year"

    department_id = db.Column(db.Integer, db.ForeignKey(Department.id))
    product_id = db.Column(db.Integer, db.ForeignKey(HSProduct.id))
    year = db.Column(db.Integer)

    department = db.relationship(Department)
    product = db.relationship(HSProduct)

    import_value = db.Column(db.Integer)
    export_value = db.Column(db.Integer)
    export_rca = db.Column(db.Integer)
    distance = db.Column(db.Float)
    cog = db.Column(db.Float)
    coi = db.Column(db.Float)


class DepartmentYear(BaseModel, IDMixin):

    __tablename__ = "department_year"

    department_id = db.Column(db.Integer, db.ForeignKey(Department.id))
    year = db.Column(db.Integer)

    department = db.relationship(Department)

    eci = db.Column(db.Float)
    eci_rank = db.Column(db.Integer)
    diversity = db.Column(db.Float)


class ProductYear(BaseModel, IDMixin):

    __tablename__ = "product_year"

    product_id = db.Column(db.Integer, db.ForeignKey(HSProduct.id))
    year = db.Column(db.Integer)

    product = db.relationship(HSProduct)

    pci = db.Column(db.Float)
    pci_rank = db.Column(db.Integer)
