from flask.ext.wtf import Form

from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, BooleanField, SelectField
from wtforms import SubmitField, FieldList
from wtforms.validators import DataRequired, Length


class LoginForm(Form):
    openid = StringField('openid', validators=[DataRequired()])
    remember_me = BooleanField('remember_me', default=False)


class FileUploadForm(Form):
    file_1 = FileField("file_1", validators=[FileRequired()])


class ChangeTabdataDatasetCsvForm(Form):
    file_1 = FileField("file_1", validators=[FileRequired()])


class AddDatasetForm(Form):
    descriptionField = StringField(
        'Description',
        validators=[Length(min=0, max=255), DataRequired()])
    queryField = StringField(
        'Query Text', validators=[Length(min=0, max=1024), DataRequired()])


class AddCsvToDatasetForm(Form):
    file_1 = FileField("file_1", validators=[FileRequired()])


class AddQueryToDatasetForm(Form):
    query = SelectField('Query', coerce=int)


class MakeGpsRemapForm(Form):
    remap_to = StringField(
        "remap_to", validators=[Length(min=0, max=255),
                                DataRequired()])
    test_button = SubmitField("Test by Google Geolocation:")
    remap_button = SubmitField("Yes, approve this remap:")


class AddTabdataDatasetForm(Form):
    file_1 = FileField("file_1", validators=[FileRequired()])
    descriptionField = StringField(
        'Description',
        validators=[Length(min=0, max=1024), DataRequired()])


class EditTabdataDatasetForm(Form):
    verifyDeleteCheckbox = BooleanField("verify_delete")
    delete_button = SubmitField("Delete this Tabdata Dataset")


class AddTabdataQueryForm(Form):
    parameterFields = FieldList(SelectField("parm", coerce=int))
    submitButton = SubmitField("Add this Query")

    def setParameterChoices(self, parameters, column_choices):
        # this is not quite right as for the moment it only allows
        # column choices for each parameter, plus the code is just heinous
        parmlist = [key for key, value in parameters.items()]
        for i in range(len(self.parameterFields)):
            field = self.parameterFields[i]
            field.choices = column_choices
            field.label = parmlist[i]
            field.id = parmlist[i]
