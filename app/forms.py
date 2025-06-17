from wtforms import Form, StringField, SubmitField, validators

class ProductForm(Form):
    product_id = StringField('',
                            [validators.DataRequired("Wymagane jest podanie ID produktu."), 
                            validators.Length(min=5, max=10, message="ID produktu powinno mieć od 5 do 10 znaków."),
                            validators.Regexp(r'^\d+$', message="ID produktu musi składać się tylko z cyfr.")],
                            )
    submit = SubmitField('Pobierz opinie')