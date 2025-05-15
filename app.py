from threading import Event

from flask import flash, Flask, render_template, redirect, request, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask import Flask, render_template, redirect, url_for, flash, request, Response
from werkzeug.utils import secure_filename
from io import BytesIO
from PIL import Image
from data import db_session
from data.add_job import AddEventForm
from flask import current_app
import datetime
from data.login_form import LoginForm
from data.forms import AvatarForm
from data.users import User
from data.events import Events
from data.register import RegisterForm
import requests
import os
from data import events_api

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Неправильный логин или пароль", form=form)
    return render_template('login.html', title='Авторизация', form=form)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return render_template('profile.html')


@app.route('/organisation', methods=['GET', 'POST'])
@login_required
def organization():
    db_sess = db_session.create_session()
    events = db_sess.query(Events).filter_by(team_leader=current_user.id).all()

    events_data = []
    for event in events:
        volunteers = []
        if event.collaborators:
            try:
                peoples = [int(i) for i in event.collaborators.split()]
                for p in peoples:
                    user = db_sess.query(User).filter_by(id=p).first()
                    if user:
                        volunteers.append({'name': user.name, 'phone': user.phone})
            except (ValueError, AttributeError):
                pass

        events_data.append({
            'event': event,
            'volunteers': volunteers
        })

    return render_template('organisation.html', events_data=events_data)


@app.route('/myevents', methods=['GET', 'POST'])
@login_required
def myevents():
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).get(current_user.id)
        if not user.events or user.events.strip() == '':
            return render_template('myevents.html', events_data=[])

        try:
            event_ids = [int(i) for i in user.events.split() if i.strip().isdigit()]
        except (ValueError, AttributeError) as e:
            current_app.logger.error(f"Error parsing events: {str(e)}")
            event_ids = []

        events_data = []
        for event_id in event_ids:
            event = db_sess.query(Events).get(event_id)
            if event:
                events_data.append(event)

        return render_template('myevents.html', events_data=events_data)

    except Exception as e:
        current_app.logger.error(f"Error in myevents: {str(e)}")
        flash('Произошла ошибка при загрузке событий', 'danger')
        return render_template('myevents.html', events_data=[])

    finally:
        db_sess.close


@app.route("/addhours/<int:event_id>", methods=['POST', 'GET'])
def addhours(event_id):
    db_sess = db_session.create_session()
    try:
        event = db_sess.query(Events).get(event_id)
        if not event or not event.collaborators:
            flash('Событие не найдено или нет участников', 'danger')
            return redirect(url_for('index'))

        ids = [int(i) for i in event.collaborators.split() if i.strip().isdigit()]
        data = []

        for user_id in ids:
            user = db_sess.query(User).get(user_id)
            if user:
                # Полностью синхронизированная проверка с функцией hours()
                completed_events = (user.completed_events or '').strip()
                completed_list = [e.strip() for e in completed_events.split() if e.strip()]
                is_completed = str(event_id) in completed_list

                data.append({
                    'name': user.name,
                    'surname': user.surname,
                    'id': user.id,
                    'completed': is_completed,
                    'debug_info': {  # Отладочная информация
                        'user_id': user.id,
                        'completed_events': user.completed_events,
                        'event_id': event_id,
                        'is_completed': is_completed
                    }
                })

        return render_template("hours.html",
                               data=data,
                               event_id=event_id,
                               event=event,
                               debug_mode=True)  # Передаем флаг отладки

    finally:
        db_sess.close()


@app.route('/hours/<int:user_id>/<int:event_id>')
def hours(user_id, event_id):
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).get(user_id)
        event = db_sess.query(Events).get(event_id)

        if not user or not event:
            flash('Пользователь или событие не найдены', 'danger')
            return redirect(url_for('addhours', event_id=event_id))

        completed_events = (user.completed_events or '').strip()
        completed_list = [e.strip() for e in completed_events.split() if e.strip()]

        if str(event_id) in completed_list:
            flash('Часы за это событие уже были добавлены', 'warning')
            return redirect(url_for('addhours', event_id=event_id))

        user.hours += event.work_size
        user.completed_events = f"{completed_events} {event_id}".strip()
        db_sess.commit()
        flash(f'Успешно добавлено {event.work_size} часов', 'success')

    except Exception as e:
        db_sess.rollback()
        flash('Произошла ошибка при добавлении часов', 'danger')
        current_app.logger.error(f"Error in hours: {str(e)}")
        current_app.logger.error(
            f"User: {user_id}, Event: {event_id}, Completed: {user.completed_events if user else 'None'}")

    finally:
        db_sess.close()

    return redirect(url_for('addhours', event_id=event_id))

@app.route("/")
def index():
    db_sess = db_session.create_session()
    events = db_sess.query(Events).all()
    data = []

    for event in events:
        if current_user.is_authenticated and event.age > current_user.age:
            continue

        user = db_sess.query(User).filter(User.id == event.team_leader).first()
        has_responded = False
        if current_user.is_authenticated and event.collaborators:
            has_responded = str(current_user.id) in event.collaborators.split()

        data.append({
            'event': event,
            'organizer': user,
            'has_responded': has_responded
        })

    return render_template("index.html", data=data)

@app.route('/respond/<int:event_id>', methods=['POST', 'GET'])
@login_required
def respond(event_id):
    db_sess = db_session.create_session()
    try:
        event = db_sess.query(Events).get(event_id)
        user = db_sess.query(User).get(current_user.id)

        if not event:
            flash('Событие не найдено', 'danger')
            return redirect(url_for('index'))

        if user.events is None:
            user.events = ''
        if f'{event_id}' not in user.events.split():
            user.events += f'{event_id} '

        collaborators = event.collaborators.split() if event.collaborators else []
        if str(user.id) not in collaborators:
            collaborators.append(str(user.id))
            event.collaborators = ' '.join(collaborators)
            flash('Вы успешно откликнулись на событие!', 'success')
        else:
            flash('Вы уже откликались на это событие', 'warning')

        db_sess.commit()

    except Exception as e:
        db_sess.rollback()
        flash('Произошла ошибка при обработке запроса', 'danger')
        current_app.logger.error(f"Error in respond: {str(e)}")

    finally:
        db_sess.close()

    return redirect(url_for('index'))


@app.route('/view_map/<int:event_id>')
def view_map(event_id):
    # Конфигурационные ключи
    GEOCODER_API_KEY = "8013b162-6b42-4997-9691-77b7074026e0"
    YANDEX_MAPS_API_KEY = "f3a0fe3a-b07e-4840-a1da-06f18b2ddf13"

    # Получаем событие из БД
    db_sess = db_session.create_session()
    event = db_sess.query(Events).get(event_id)

    if not event:
        flash('Событие не найдено', 'danger')
        return redirect(url_for('index'))

    try:
        # Запрос к геокодеру
        geocoder_request = (
            f'http://geocode-maps.yandex.ru/1.x/?'
            f'apikey={GEOCODER_API_KEY}&'
            f'geocode={event.place}&'
            f'format=json'
        )

        # Получаем и обрабатываем ответ
        response = requests.get(geocoder_request)
        response.raise_for_status()  # Проверка на ошибки HTTP

        geo_data = response.json()
        feature_member = geo_data["response"]["GeoObjectCollection"]["featureMember"]

        if not feature_member:
            flash('Не удалось найти указанное место на карте', 'warning')
            # Возвращаем шаблон с координатами по умолчанию (например, центр Москвы)
            return render_template(
                'event_map.html',
                event=event,
                latitude=55.751244,
                longitude=37.618423,
                yandex_api_key=YANDEX_MAPS_API_KEY,
                geocode_error=True
            )

        pos = feature_member[0]["GeoObject"]["Point"]["pos"]
        longitude, latitude = map(float, pos.split())

        return render_template(
            'event_map.html',
            event=event,
            latitude=latitude,
            longitude=longitude,
            yandex_api_key=YANDEX_MAPS_API_KEY,
            geocode_error=False
        )

    except requests.exceptions.RequestException as e:
        flash(f'Ошибка при запросе к геокодеру: {str(e)}', 'danger')
        return redirect(url_for('event_details', event_id=event_id))
    except (KeyError, ValueError) as e:
        flash('Не удалось обработать данные местоположения', 'danger')
        return redirect(url_for('event_details', event_id=event_id))
    finally:
        db_sess.close()


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Register', form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Register', form=form,
                                   message="Такой пользователь уже существует")
        user = User(
            name=form.name.data,
            surname=form.surname.data,
            age=form.age.data,
            email=form.email.data,
            region=form.region.data,
            phone=form.phone.data,
            hours=0,
            events=''
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/addevent', methods=['GET', 'POST'])
def addevent():
    add_form = AddEventForm()
    if add_form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            events = Events(
                event=add_form.event.data,
                team_leader=current_user.id,
                work_size=add_form.work_size.data,
                collaborators='',
                start_date=add_form.start_date.data,
                discription=add_form.discription.data,
                age=add_form.age.data,
                place=add_form.place.data
            )

            if add_form.photo.data:
                photo = add_form.photo.data
                if photo.filename:
                    filename = secure_filename(photo.filename)
                    unique_name = f"{int(datetime.datetime.now().timestamp())}_{filename}"
                    upload_dir = os.path.join(current_app.root_path, 'static', 'event_photos')

                    # Создание папки если не существует
                    if not os.path.exists(upload_dir):
                        os.makedirs(upload_dir)
                        print(f"Создана папка: {upload_dir}")

                    filepath = os.path.join(upload_dir, unique_name)
                    photo.save(filepath)

                    # Двойная проверка сохранения
                    if os.path.exists(filepath):
                        print(f"Файл сохранён: {filepath}")
                        events.photo_filename = unique_name
                    else:
                        print("Ошибка: файл не сохранён!")

            db_sess.add(events)
            db_sess.commit()
            return redirect(url_for('index'))

        except Exception as e:
            db_sess.rollback()
            current_app.logger.error(f"Ошибка сохранения: {str(e)}")
            return render_template('addevent.html',
                                   form=add_form,
                                   message=f"Ошибка: {str(e)}")

    # Логирование ошибок формы
    if request.method == 'POST' and not add_form.validate():
        current_app.logger.warning(f"Ошибки формы: {add_form.errors}")

    return render_template('addevent.html', form=add_form)

@app.route('/delete/<int:event_id>')
@login_required
def delete(event_id):
    db_sess = db_session.create_session()
    event = db_sess.query(Events).filter(Events.id==event_id).first()

    if current_user.id == event.team_leader:
        db_sess.delete(event)
        db_sess.commit()
        return redirect('/organisation')
    else:
        return redirect('/organisation')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/upload_avatar', methods=['GET', 'POST'])
@login_required
def upload_avatar():
    form = AvatarForm()
    if form.validate_on_submit():
        file = form.avatar.data
        try:
            img = Image.open(file.stream)

            if img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail((500, 500))
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            avatar_data = buffer.getvalue()
            db_sess = db_session.create_session()
            user = db_sess.query(User).get(current_user.id)
            user.avatar_data = avatar_data
            user.avatar_mimetype = 'image/jpeg'
            db_sess.commit()

            flash('Аватар успешно обновлен!', 'success')
            return redirect(url_for('profile'))

        except Exception as e:
            flash(f'Ошибка обработки изображения: {str(e)}', 'danger')

    return render_template('upload_avatar.html',
                           form=form,
                           MAX_AVATAR_SIZE=2 * 1024 * 1024)


@app.route('/avatar')
@login_required
def get_avatar():
    db_sess = db_session.create_session()
    user = db_sess.query(User).get(current_user.id)

    if user and user.avatar_data:
        return Response(user.avatar_data, mimetype=user.avatar_mimetype)

    default_path = os.path.join(app.root_path, 'static', 'img', 'default_avatar.jpg')
    with open(default_path, 'rb') as f:
        default_data = f.read()
    return Response(default_data, mimetype='image/jpeg')

# @app.route('/update/<int:work_id>', methods=['GET', 'POST'])
# @login_required
# def update(work_id):
#     db_sess = db_session.create_session()
#     job = db_sess.query(Jobs).filter(Jobs.id == work_id).first()
#
#     if current_user.id =laborators.data = job.collaborators
#             add_form.is_finished.data = job.is_finished
#
#         if add_form.validate_on_submit():
#             job.job = add_form.job.data
#             job.team_leader = add_form.team_leader.data
#             job.work_size = add_form.work_size.data
#             job.collaborators = add_form.collaborators.data
#             job.is_finished = add_form.is_finished.data
#             db_sess.commit()
#             return redirect('/')
#
#         return render_template('updatejob.html', title='Редактирование работы', form=add_form)
#     else:
#         return 'У вас нет доступа'
#
#
def main():
    db_session.global_init("db/volunteers.db")
    app.register_blueprint(events_api.blueprint)
    app.run()


if __name__ == '__main__':
    main()
