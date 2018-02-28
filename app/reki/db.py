#!/usr/bin/env python3

from flask_uploads import UploadSet, IMAGES

from .. import db


rekimaps = UploadSet('rekimaps', IMAGES)


class RekiData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    time = db.Column(db.BigInteger, nullable=False)
    settings = db.Column(db.PickleType, nullable=False)
    options = db.Column(db.PickleType, nullable=False)
    world_data = db.Column(db.PickleType, nullable=False)
    weather_data = db.Column(db.PickleType, nullable=True)
    map_url = db.Column(db.String(120), nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


def km2mi(km):
    return km * 1 / 1.609344


def mi2km(mi):
    return mi * 1.609344


def model_from_form(form_data, user_id):
    f = form_data

    # Days per year and days from start of year to starting date.
    dpy = sum(f['monthdays'])
    doff = sum(f['monthdays'][:f['start_month']]) + f['start_day'] - 1

    # Calculate solstices and equinoxes in absolute days from start of year.
    sum_solstice = sum(f['monthdays'][:f['solstice_month']]) + \
        f['solstice_day']
    ver_equinox = (sum_solstice - (dpy // 4) - 1) % dpy + 1
    win_solstice = (sum_solstice + (dpy // 2) - 1) % dpy + 1
    aut_equinox = (sum_solstice + (dpy // 4) - 1) % dpy + 1

    # Compile the moon data.
    moons = []
    for mi in range(f['num_moons']):
        # Moon cycle offset in days from time 0.
        lunoff = sum(f['monthdays'][:f['moon_{}_month'.format(mi)]]) + \
            f['moon_{}_day'.format(mi)] - 1 - doff
        moons.append({'name': f['moon_{}_name'.format(mi)],
                      'off': lunoff,
                      'cycle': f['moon_{}_cycle'.format(mi)]})

    # Pre-compute values necessary for date calculations.
    date = {
        'rpm': 60 / f['round_length'],
        'dpy': dpy,
        'doff': doff,
        'yoff': f['start_year'],
        'wdoff': f['start_weekday']
    }

    # Global Reki settings.
    settings = {
        'date': date,
        'months': [{'name': m, 'days': d}
                   for m, d in zip(f['months'], f['monthdays'])],
        'weekdays': f['weekdays'],
        'round': f['round_length'],
        'natural': {'veq': ver_equinox,
                    'ssol': sum_solstice,
                    'aeq': aut_equinox,
                    'wsol': win_solstice,
                    'moons': moons}
    }

    if f['use_leap_year']:
        # Days per leap cycle.
        dplc = f['leap_every'] * date['dpy'] + f['leap_by']
        # Year offset from start of leap cycle.
        lyoff = ((f['start_year'] - f['leap_basis_year'] - 1) % f['leap_by'])
        # Day offset from start of leap cycle to start of starting year.
        ldoff = lyoff * date['dpy']
        # Correct day offset from start of year.
        if lyoff == f['leap_every'] - 1 and f['start_month'] > f['leap_month']:
            date['doff'] += f['leap_by']

        settings['leap_year'] = {'every': f['leap_every'],
                                 'by': f['leap_by'],
                                 'month': f['leap_month'],
                                 'yoff': lyoff,
                                 'dplc': dplc,
                                 'doff': ldoff}
    else:
        settings['leap_year'] = None

    if f['use_map']:
        settings['map'] = {'world_width': f['map_width']
                           if f['map_units'] == 'mi'
                           else km2mi(f['map_width'])}
        map_filename = rekimaps.save(f['map_file'])
        map_url = rekimaps.url(map_filename)
    else:
        settings['map'] = None
        map_url = None

    # Initialize empty world data dict.
    world_data = {'events': [], 'history': [], 'inProgress': [],
                  'holidays': [], 'recurring': [], 'locations': {},
                  'routes': [],
                  'eras': [{'name': f['era_name'], 'start': 1}]}

    # Initialize empty options.
    options = {}

    return RekiData(name=f['name'], time=0, settings=settings, options=options,
                    world_data=world_data, map_url=map_url,
                    user_id=user_id)
