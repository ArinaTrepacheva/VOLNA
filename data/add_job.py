from flask_wtf import FlaskForm
from wtforms import SubmitField, DateField, FileField, StringField, BooleanField, IntegerField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileAllowed


class AddEventForm(FlaskForm):
    event = StringField('Название события', validators=[DataRequired()])
    discription = StringField('Описание события', validators=[DataRequired()])
    photo = FileField('Фотография события', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Только изображения JPG/PNG!')
    ])
    age = IntegerField('Возрастное ограничение(минимальное)',  validators=[DataRequired()])
    place = StringField('Место проведения(точный адрес)', validators=[DataRequired()])
    work_size = IntegerField('Длительность(в часах)', validators=[DataRequired()])
    start_date = DateField('Дата начала', validators=[DataRequired()])
    submit = SubmitField('Создать')
