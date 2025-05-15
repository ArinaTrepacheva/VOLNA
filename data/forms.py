from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField

class AvatarForm(FlaskForm):
    avatar = FileField('Аватарка', validators=[
        FileRequired('Выберите файл'),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Только изображения (JPG, PNG)')
    ])
    submit = SubmitField('Загрузить')