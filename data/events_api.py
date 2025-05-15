
from flask import jsonify, Blueprint, request, make_response

from . import db_session
from .events import Events

blueprint = Blueprint(
    'events_api',
    __name__,
    template_folder='templates'
)


@blueprint.route('/api/events/all')
def get_events():
    db_sess = db_session.create_session()
    events = db_sess.query(Events).all()
    return jsonify({'events': [item.to_dict(
        only=('id', 'event', 'work_size', 'place', 'discription',
              'collaborators', 'start_date', 'age', 'team_leader')
    )
        for item in events]})

@blueprint.route('/api/events/age/<int:age_us>')
def get_events_age(age_us):
    db_sess = db_session.create_session()
    events = db_sess.query(Events).filter(Events.age >= age_us)
    return jsonify({'events': [item.to_dict(
        only=('id', 'event', 'work_size', 'place', 'discription',
              'collaborators', 'start_date', 'age', 'team_leader')
    )
        for item in events]})

@blueprint.route('/api/events/place/<place>')
def get_events_place(place):
    db_sess = db_session.create_session()
    events = db_sess.query(Events).filter(Events.place == place)
    return jsonify({'events': [item.to_dict(
        only=('id', 'event', 'work_size', 'place', 'discription',
              'collaborators', 'start_date', 'age', 'team_leader')
    )
        for item in events]})

@blueprint.route('/api/events/id/<idd>')
def get_events_id(idd):
    db_sess = db_session.create_session()
    events = db_sess.query(Events).filter(Events.id == idd)
    return jsonify({'events': [item.to_dict(
        only=('id', 'event', 'work_size', 'place', 'discription',
              'collaborators', 'start_date', 'age', 'team_leader')
    )
        for item in events]})

@blueprint.route('/api/events/id_leader/<int:idd>')
def get_events_id_leader(idd):
    db_sess = db_session.create_session()
    events = db_sess.query(Events).filter(Events.team_leader == idd)
    return jsonify({'events': [item.to_dict(
        only=('id', 'event', 'work_size', 'place', 'discription',
              'collaborators', 'start_date', 'age', 'team_leader')
    )
        for item in events]})