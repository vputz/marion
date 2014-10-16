from flask.ext.wtf import Form

from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length


class LoginForm(Form) :
    openid = StringField('openid', validators = [DataRequired()])
    remember_me = BooleanField('remember_me', default=False )
    
class FileUploadForm( Form ) :
    file_1 = FileField("file_1", validators =[FileRequired()])

class AddDatasetForm( Form ) :
    descriptionField = StringField('Description', validators=[Length(min=0, max=255),DataRequired()])
    queryField = StringField('Query Text', validators=[Length(min=0, max=1024),DataRequired()])
    
class AddCsvToDatasetForm( Form ) :
    file_1 = FileField("file_1", validators =[FileRequired()])

class AddQueryToDatasetForm( Form ) :
    query = SelectField('Query', coerce=int)
