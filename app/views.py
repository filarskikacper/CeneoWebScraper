from app import app
import os
import json
from bs4 import BeautifulSoup
from flask import render_template, request, redirect, url_for, send_file
import requests
from config import headers
from app import utils
from app.models import Product
from app.forms import ProductForm
import pandas as pd
from matplotlib import pyplot as plt

import matplotlib
matplotlib.use('Agg')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/extract")
def display_form():
    form = ProductForm()
    return render_template("extract.html", form=form)

@app.route("/extract", methods=["POST"])
def extract():
    form = ProductForm(request.form)
    if form.validate():
        product_id = form.product_id.data
        product = Product(product_id)
        check_opinions = product.check_opinions()
        if check_opinions:
            return render_template("extract.html", form=form, error=check_opinions)
        product.extract_opinions().make_stats()
        print("self.opinions type:", type(product.opinions))
        product.export_to_opinions()
        product.export_to_products()
        product_name = product.product_name
    else: return render_template("extract.html", form=form)

    return redirect(url_for('product', product_id=product_id, product_name=product_name))

@app.route("/products")
def products():
    products_files = os.listdir("./app/data/products")
    products_list = []
    for filename in products_files:
        with open(f"./app/data/products/{filename}", "r", encoding="UTF-8") as jf:
            product = Product(filename.split(".")[0])
            product.product_from_dict(json.load(jf))
            products_list.append(product)

    return render_template("products.html", products=products_list)

@app.route("/author")
def author():
    return render_template("author.html")

@app.route("/product/<product_id>")
def product(product_id):
    product = Product(product_id)
    product.load_from_file()
    return render_template("product.html", product_id=product_id, product_name=product.product_name, opinions=product.opinions)

@app.route("/charts/<product_id>")
def charts(product_id):
    product = Product(product_id)
    product.export_charts()
    return render_template("charts.html", product_id=product_id, product_name=product.product_name)

@app.route("/download/<product_id>/<file_type>", methods=["GET"])
def download(product_id, file_type):
        product = Product(product_id)
        product.export_file(file_type)
        if file_type == 'json':
            format = 'json'
        elif file_type == 'csv':
            format = 'csv'
        elif file_type == 'xlsx':
            format = 'xlsx'
        file_path = os.path.abspath(f"./app/data/opinions/{product_id}.{format}")
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return "Nie odnaleziono pliku.", 404