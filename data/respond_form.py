from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired

class RespondForm(FlaskForm):
    message = TextAreaField('Сообщение', validators=[DataRequired()])
    submit = SubmitField('Отправить')