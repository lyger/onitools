#!/usr/bin/env python3

from flask_uploads import IMAGES
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from werkzeug.datastructures import FileStorage
from wtforms import BooleanField, IntegerField, SelectField, StringField
from wtforms.compat import string_types
from wtforms.validators import InputRequired, Length, NumberRange, \
    StopValidation, ValidationError
from os import SEEK_END


def human_filesize(size):
    size = float(size)
    for pref in ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']:
        if abs(size) < 1000.0:
            return '{:.1f} {}B'.format(size, pref).replace('.0', '')
        size /= 1000.0
    return '{:.1f} YB'.format(size).replace('.0', '')


class FileSize:

    def __init__(self, max_bytes):
        self.max_bits = max_bytes * 1000
        self.msg = \
            'File too large '

    def __call__(self, form, field):
        file_data = field.data
        if not isinstance(file_data, FileStorage):
            print(type(file_data))
            raise ValidationError('Input was not a file.')
        file_data.seek(0, SEEK_END)
        file_size = file_data.tell()
        # Reset file cursor.
        file_data.seek(0)

        if file_size > self.max_bits:
            raise ValidationError(
                self.msg + '(received {})'.format(human_filesize(file_size)))


class RequiredIfMixin:

    def __init__(self, other_field_name, strip_whitespace=True,
                 *args, **kwargs):
        self.other = other_field_name
        if strip_whitespace:
            self.string_check = lambda s: s.strip()
        else:
            self.string_check = lambda s: s
        super().__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other, None)
        if other_field is None:
            raise ValidationError('The form is broken.')

        if bool(other_field.data):
            super().__call__(form, field)

        if not field.raw_data or isinstance(field.raw_data[0], string_types) \
                and not self.string_check(field.raw_data[0]):
            field.errors[:] = []
            raise StopValidation()


class InputRequiredIf(RequiredIfMixin, InputRequired):
    pass


class FileRequiredIf(RequiredIfMixin, FileRequired):
    pass


class CreateRekiForm1(FlaskForm):
    name = StringField('Calendar name',
                       validators=[InputRequired(), Length(min=1, max=60)])
    era_name = StringField('Current era suffix', default='AD',
                           validators=[InputRequired(), Length(min=1, max=10)])
    num_months = \
        IntegerField('Months per year', default=12,
                     validators=[InputRequired(), NumberRange(min=3, max=50)])
    num_weekdays = \
        IntegerField('Days per week', default=7,
                     validators=[InputRequired(), NumberRange(min=3, max=20)])
    round_length = \
        IntegerField('Seconds in a game round', default=6,
                     validators=[InputRequired(), NumberRange(min=1)])
    num_moons = \
        IntegerField('Number of moons in world', default=1,
                     validators=[InputRequired(), NumberRange(min=0, max=5)])


class CreateRekiForm2(FlaskForm):
    pass


class CreateRekiForm3(FlaskForm):
    start_year = \
        IntegerField(default=1,
                     validators=[InputRequired(), NumberRange(min=1)])
    use_leap_year = BooleanField('Use leap year', default=False)
    leap_every = \
        IntegerField(default=4,
                     validators=[InputRequiredIf('use_leap_year'),
                                 NumberRange(min=1)])
    leap_by = \
        IntegerField(default=1,
                     validators=[InputRequiredIf('use_leap_year'),
                                 NumberRange(min=1, max=5)])
    leap_basis_year = \
        IntegerField(default=1,
                     validators=[InputRequiredIf('use_leap_year'),
                                 NumberRange(min=1)])
    use_map = BooleanField('Use map', default=True)
    map_width = \
        IntegerField('Map width', default=1000,
                     validators=[InputRequiredIf('use_map'),
                                 NumberRange(min=1, max=50000)])
    map_units = SelectField(choices=[('mi', 'miles'), ('km', 'kilometers')],
                            default='mi')

    map_file = \
        FileField('Map file (max 3 MB)',
                  validators=[FileRequiredIf('use_map'),
                              FileSize(3000),
                              FileAllowed(IMAGES,
                                          'Please choose an image file')])
