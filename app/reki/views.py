#!/usr/bin/env python3

from flask import jsonify, redirect, render_template, request, session, url_for
from flask_security import current_user, login_required
from sqlalchemy.orm import load_only, defer
from wtforms import IntegerField, SelectField, StringField
from wtforms.validators import InputRequired, NumberRange, Length, \
    ValidationError
from itertools import zip_longest
from os import remove as remove_file

from . import Reki
from .db import db, model_from_form, RekiData, rekimaps
from .forms import CreateRekiForm1, CreateRekiForm2, CreateRekiForm3
from .. import csrf

DEFAULT_MONTHS = ['January', 'February', 'March', 'April',
                  'May', 'June', 'July', 'August',
                  'September', 'October', 'November', 'December']
DEFAULT_MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
DEFAULT_WEEKDAYS = ['Sunday', 'Monday', 'Tuesday',
                    'Wednesday', 'Thursday', 'Friday', 'Saturday']

# Global storage.
active_rekis = {}


@Reki.context_processor
def inject_globals():
    return {
        'active_page': 'Reki'
    }


@Reki.route('/', methods=['GET'])
def main():
    return render_template('reki_index.html')


@Reki.route('/create/1', methods=['GET', 'POST'])
@login_required
def create_new1():
    form_data = session.get('reki_form_data', None)

    form = CreateRekiForm1()

    if form.validate_on_submit():
        session['reki_form_data'] = {'step1': form.data}
        return redirect(url_for('.create_new2'))

    return render_template('reki_create1.html', form=form)


@Reki.route('/create/2', methods=['GET', 'POST'])
@login_required
def create_new2():
    form_data = session.get('reki_form_data', None)

    if not form_data or 'step1' not in form_data:
        return redirect(url_for('.create_new1'))

    # Define form dynamically.
    class F(CreateRekiForm2):
        pass

    num_months = form_data['step1']['num_months']
    num_weekdays = form_data['step1']['num_weekdays']

    for i, mn, numdays in zip_longest(range(num_months),
                                      DEFAULT_MONTHS[:num_months],
                                      DEFAULT_MONTH_DAYS[:num_months]):
        if not mn:
            mn = 'Month {}'.format(i + 1)
        if not numdays:
            numdays = 30
        setattr(F, 'month_{}_name'.format(i),
                StringField('Month {} name'.format(i + 1), default=mn,
                            validators=[InputRequired()]))
        setattr(F, 'month_{}_days'.format(i),
                IntegerField('Number of days', default=numdays,
                             validators=[InputRequired(),
                                         NumberRange(min=1, max=100)]))

    for i, day in zip_longest(range(num_weekdays),
                              DEFAULT_WEEKDAYS[:num_weekdays]):
        if not day:
            day = 'Day {}'.format(i + 1)
        setattr(F, 'weekday_{}_name'.format(i),
                StringField('Day {} name'.format(i + 1), default=day,
                            validators=[InputRequired()]))

    form = F()

    if form.validate_on_submit():
        # Clean up form data to lists of months and weekdays.
        num_months = form_data['step1']['num_months']
        num_weekdays = form_data['step1']['num_weekdays']
        step2_data = form.data
        step2_data['months'] = [step2_data['month_{}_name'.format(i)]
                                for i in range(num_months)]
        step2_data['monthdays'] = [step2_data['month_{}_days'.format(i)]
                                   for i in range(num_months)]
        step2_data['weekdays'] = [step2_data['weekday_{}_name'.format(i)]
                                  for i in range(num_weekdays)]
        form_data['step2'] = step2_data
        session['reki_form_data'] = form_data
        return redirect(url_for('.create_new3'))

    return render_template('reki_create2.html', form=form,
                           num_months=form_data['step1']['num_months'],
                           num_weekdays=form_data['step1']['num_weekdays'])


@Reki.route('/create/3', methods=['GET', 'POST'])
@login_required
def create_new3():
    form_data = session.get('reki_form_data', None)

    if not form_data or 'step1' not in form_data:
        return redirect(url_for('.create_new1'))
    elif 'step2' not in form_data:
        return redirect(url_for('.create_new2'))

    # Define form dynamically.
    monthsel = [(i, m) for i, m in enumerate(form_data['step2']['months'])]
    monthdays = form_data['step2']['monthdays']
    weekdaysel = [(i, w) for i, w in enumerate(form_data['step2']['weekdays'])]

    def dayInMonth(month_field_name, msg=None):
        if not msg:
            msg = 'Day must be within month.'

        def _dayInMonth(form, field):
            month_field = form._fields.get(month_field_name, None)
            if month_field is None:
                raise ValidationError('The form is broken.')
            max_days = monthdays[int(month_field.data)]
            if field.data > max_days:
                raise ValidationError(msg)

        return _dayInMonth

    class F(CreateRekiForm3):
        start_day = \
            IntegerField(default=1,
                         validators=[InputRequired(), NumberRange(min=1),
                                     dayInMonth('start_month')])
        start_month = \
            SelectField(choices=monthsel, default=0, coerce=int)
        start_weekday = \
            SelectField(choices=weekdaysel, default=0, coerce=int)

        solstice_day = \
            IntegerField(default=min(21, monthdays[min(5, len(monthsel) - 1)]),
                         validators=[InputRequired(), NumberRange(min=1),
                                     dayInMonth('solstice_month')])
        solstice_month = \
            SelectField(choices=monthsel,
                        default=min(5, len(monthsel) - 1), coerce=int)
        leap_month = \
            SelectField(choices=monthsel,
                        default=min(1, len(monthsel) - 1), coerce=int)

    for i in range(form_data['step1']['num_moons']):
        moon_name = 'Moon{}'.format(' {}'.format(i + 1) if (i > 0) else '')
        setattr(F, 'moon_{}_name'.format(i),
                StringField(default=moon_name,
                            validators=[InputRequired(),
                                        Length(min=1, max=60)]))
        setattr(F, 'moon_{}_cycle'.format(i),
                IntegerField(default=29,
                             validators=[InputRequired(), NumberRange(min=1)]))
        setattr(F, 'moon_{}_day'.format(i),
                IntegerField(default=1,
                             validators=[InputRequired(), NumberRange(min=1),
                                         dayInMonth('moon_{}_month'.format(i))]))
        setattr(F, 'moon_{}_month'.format(i),
                SelectField(choices=monthsel,
                            default=0, coerce=int))

    form = F()
    if form.validate_on_submit():
        all_data = {}
        all_data.update(form_data['step1'])
        all_data.update(form_data['step2'])
        all_data.update(form.data)

        reki = model_from_form(all_data, current_user.id)
        current_user.reki_calendars.append(reki)
        db.session.add(reki)
        db.session.commit()

        # We are now done with this.
        session.pop('reki_form_data')

        return redirect(url_for('.run_app', rid=reki.id))

    return render_template('reki_create3.html', form=form,
                           era=form_data['step1']['era_name'],
                           num_moons=form_data['step1']['num_moons'])


@Reki.route('/run')
@login_required
def run_app():
    reki_id = request.args.get('rid', None)

    if not reki_id:
        return redirect(url_for('.main'))

    reki = RekiData.query.options(load_only('user_id')).get(reki_id)

    if not reki or reki.user_id != current_user.id:
        return redirect(url_for('.main'))

    active_rekis[current_user.id] = reki_id

    return render_template('reki_app.html', title=reki.name)


@Reki.route('/_get_reki')
@login_required  # DISABLE FOR TESTING as React server is cross-origin.
def get_reki():
    # The only way this could have ended up here is if the current user
    # owns the Reki and it exists. No need to validate further.
    reki_id = active_rekis.get(current_user.id, None)
    # reki_id = active_rekis[1]

    if not reki_id:
        # Error code 1: Reki not chosen.
        return jsonify(code=1)

    reki = RekiData.query.get(reki_id)

    # Return code 0: success.
    ret = {'code': 0,
           'rid': reki_id,
           'options': reki.options,
           'settings': reki.settings,
           'time': reki.time,
           'world_data': reki.world_data}

    if reki.settings['map'] is not None:
        ret['map_imgurl'] = rekimaps.url(reki.map_file)

    return jsonify(ret)


@Reki.route('/_save_reki', methods=['POST'])
@login_required  # DISABLE FOR TESTING as React server is cross-origin.
# @csrf.exempt
def save_reki():
    data = request.get_json(silent=True)

    reki_id = active_rekis.get(current_user.id, None)  # DISABLED FOR DEBUG
    # reki_id = active_rekis[1]
    if data.get('rid', -1) != reki_id:
        # Error code 2: trying to save to wrong reki.
        return jsonify(code=2)

    reki = RekiData.query.get(reki_id)

    time = data.get('time', None)
    options = data.get('options', None)
    world_data = data.get('world_data', None)

    if time:
        reki.time = time
    if options:
        reki.options = options
    if world_data:
        reki.world_data = world_data

    db.session.add(reki)
    db.session.commit()

    if data.get('quit', False):
        # pass
        del active_rekis[current_user.id]  # DISABLED FOR DEBUG

    # Code 0, everything went OK.
    return jsonify(code=0)


@Reki.route('/delete', methods=['POST'])
@login_required
def delete():
    next_url = request.args.get('next', url_for('.main'))
    reki_id = request.form.get('RekiID', None)

    if reki_id:
        reki = RekiData.query.get(reki_id)

        if (current_user.id in active_rekis) and \
                (active_rekis[current_user.id] == reki.id):
            del active_rekis[current_user.id]

        if reki and reki.user_id == current_user.id:
            if reki.map_file is not None:
                remove_file(rekimaps.path(reki.map_file))
            db.session.delete(reki)
            db.session.commit()

    return redirect(next_url)


@Reki.route('/rename', methods=['POST'])
@login_required
def rename():
    next_url = request.args.get('next', url_for('.main'))
    reki_id = request.form.get('RekiID', None)

    if reki_id:
        reki = RekiData.query.options(load_only('name')).get(reki_id)

        if reki and reki.user_id == current_user.id:
            new_name = request.form.get('newRekiName', 'My Reki')
            if len(new_name.strip()) > 0:
                reki.name = new_name
                db.session.add(reki)
                db.session.commit()

    return redirect(next_url)
