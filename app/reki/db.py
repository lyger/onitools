#!/usr/bin/env python3

from .. import db


class RekiData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    time = db.Column(db.BigInteger, nullable=False)
    settings = db.Column(db.PickleType, nullable=False)
    world_data = db.Column(db.PickleType, nullable=False)
    weather_data = db.Column(db.PickleType, nullable=True)
    map_image = db.Column(db.LargeBinary, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


def km2mi(km):
    return km * 1 / 1.609344


def mi2km(mi):
    return mi * 1.609344


def model_from_form(form_data, user_id):
    f = form_data

    # Calculate solstices in absolute days from start of year.
    year_days = sum(f['monthdays'])
    sum_solstice = sum(f['monthdays'][:f['solstice_month']]) + \
        f['solstice_day']
    win_solstice = (sum_solstice + (year_days // 2) - 1) % year_days + 1

    # Global Reki settings.
    settings = {
        'start_date': {'year': f['start_year'],
                       'month': f['start_month'],
                       'day': f['start_day'],
                       'weekday': f['start_weekday']},
        'months': [{'name': m, 'days': d}
                   for m, d in zip(f['months'], f['monthdays'])],
        'weekdays': f['weekdays'],
        'round': f['round_length'],
        'eras': [{'name': f['era_name'], 'start': f['start_year']}],
        'solstice': {'summer': sum_solstice,
                     'winter': win_solstice}
    }

    if f['use_leap_year']:
        settings['leap_year'] = {'every': f['leap_every'],
                                 'by': f['leap_by'],
                                 'month': f['leap_month'],
                                 'offset': ((f['start_year'] -
                                             f['leap_basis_year']) %
                                            f['leap_by'])}
    else:
        settings['leap_year'] = None

    if f['use_map']:
        settings['map'] = {'world_width': f['map_width']
                           if f['map_units'] == 'mi'
                           else km2mi(f['map_width'])}
        map_image = f['map_file'].read()
    else:
        settings['map'] = None
        map_image = None

    # Initialize empty world data dict.
    world_data = {'events': [], 'history': [], 'locations': [], 'paths': []}

    return RekiData(name=f['name'], time=0, settings=settings,
                    world_data=world_data, map_image=map_image,
                    user_id=user_id)
