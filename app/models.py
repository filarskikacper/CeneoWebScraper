import os
import json
from bs4 import BeautifulSoup
import requests
from app.utils import extract_feature, selectors
from config import headers
import pandas as pd
import matplotlib.pyplot as plt

class Opinion:
    
    def __init__(self, opinion_id="", author="", recommendation="", stars=0.0, content="", pros=[], cons=[], useful=0, unuseful=0, post_date="", purchase_date=""):
        self.opinion_id = opinion_id
        self.author = author
        self.recommendation = recommendation
        self.stars = stars
        self.content = content
        self.pros = pros
        self.cons = cons
        self.useful = useful
        self.unuseful = unuseful
        self.post_date = post_date
        self.purchase_date = purchase_date

    
    def from_dict(self, opinion_in_dict):
        for key in selectors.keys():
            setattr(self, key, opinion_in_dict[key])
    
    def to_dict(self):
        return {feature: getattr(self,feature) for feature in selectors.keys()}
    
    def extract_features(self, opinion):
        for key, value in selectors.items():
           setattr(self, key, extract_feature(opinion, *value))
        return self
    
    def transform(self):
        try:
            self.stars = float(self.stars.split("/")[0].replace(",", "."))
        except TypeError:
            self.stars = float(self.stars)
        self.useful = int(self.useful)
        self.unuseful = int(self.unuseful)
        return self


class Product:
    def __init__(self, product_id, product_name=""):
        self.product_id = product_id
        self.product_name = product_name
        self.stats = {}
        self.opinions = []
    
    def check_opinions(self):
        next_page = f"https://www.ceneo.pl/{self.product_id}#tab=reviews"
        response = requests.get(next_page, headers=headers)
        if response.status_code == 200:
            page_dom = BeautifulSoup(response.text, "html.parser")
            self.product_name = extract_feature(page_dom, "h1")
            opinions_count = extract_feature(page_dom, "a.product-review__link > span")
            if opinions_count:
                return False
            else:
                return "Dla produktu o podanym ID nie ma jeszcze żadnej opinii."
        else:
            return "Nie znaleziono produktu o podanym ID."
        
    def extract_opinions(self):
        next_page = f"https://www.ceneo.pl/{self.product_id}#tab=reviews"
        while next_page:
            response = requests.get(next_page, headers=headers)
            if response.status_code == 200:
                page_dom = BeautifulSoup(response.text, "html.parser")     
                opinions = page_dom.select("div.js_product-review:not(.user-post--highlight)")
                for opinion in opinions:
                    single_opinion = Opinion()
                    self.opinions.append(single_opinion.extract_features(opinion).transform())
                try:
                    next_page = "https://www.ceneo.pl" + extract_feature(page_dom, "a.pagination__next", "href")
                except TypeError:
                    next_page = None
            else:
                next_page = None
        return self
    
    def opinions_from_dict(self, opinions_list):
        for opinion_dict in opinions_list:
            opinion = Opinion()
            opinion.from_dict(opinion_dict)
            self.opinions.append(opinion)

    def product_from_dict(self, products):
        self.product_id = products["product_id"]
        self.product_name = products["product_name"]
        self.stats = products["stats"]
    
    def make_stats(self):
        opinions = pd.DataFrame([opinion.to_dict() for opinion in self.opinions])
        self.stats = {
        "opinions_count": opinions.shape[0],
        "pros_count": int(opinions.pros.astype(bool).sum()),
        "cons_count": int(opinions.cons.astype(bool).sum()),
        "pros_cons_count": int(opinions.apply(lambda o: bool(o.pros) and bool(o.cons), axis=1).sum()),
        "average_stars": opinions.stars.mean(),
        "pros": opinions.pros.explode().dropna().value_counts().to_dict(),
        "cons": opinions.cons.explode().dropna().value_counts().to_dict(),
        "recommendations": opinions.recommendation.value_counts(dropna=False).reindex(["Nie polecam", "Polecam", None], fill_value=0).to_dict()
        }
        return self
    
    def export_to_opinions(self):
        if not os.path.exists("./app/data"):
            os.mkdir("./app/data")
        if not os.path.exists("./app/data/opinions"):
            os.mkdir("./app/data/opinions")
        with open(f"./app/data/opinions/{self.product_id}.json", "w", encoding="UTF-8") as jf:
            json.dump([opinion.to_dict() for opinion in self.opinions], jf, indent=4, ensure_ascii=False)

    def export_to_products(self):
        if not os.path.exists("./app/data"):
            os.mkdir("./app/data")
        if not os.path.exists("./app/data/products"):
            os.mkdir("./app/data/products")
        with open(f"./app/data/products/{self.product_id}.json", "w", encoding="UTF-8") as jf:
            json.dump({
            "product_id": self.product_id,
            "product_name": self.product_name,
            "stats": self.stats
            }, jf, indent=4, ensure_ascii=False)

    def load_from_file(self):
        with open(f"./app/data/products/{self.product_id}.json", "r", encoding="UTF-8") as jf:
            self.product_from_dict(json.load(jf))
        with open(f"./app/data/opinions/{self.product_id}.json", "r", encoding="UTF-8") as jf:    
            self.opinions_from_dict(json.load(jf))
        return self
    
    def export_charts(self):
        if not os.path.exists("./app/static/images"):
            os.mkdir("./app/static/images")
        if not os.path.exists("./app/static/images/charts"):
            os.mkdir("./app/static/images/charts")
        with open(f"./app/data/products/{self.product_id}.json", "r", encoding="UTF-8") as jf:
            self.product_from_dict(json.load(jf))
        recommendations = pd.Series(self.stats["recommendations"])
        recommendations.plot.pie(
            label = "",
            labels = ["Nie polecam", "Polecam", "Nie mam zdania"],
            title = f"Rozkład rekomendacji w opiniach o produkcie {self.product_id}",
            colors = ["crimson", "forestgreen", "lightgrey"],
            autopct = "%1.1f%%"
            )
        plt.savefig(f"./app/static/images/charts/{self.product_id}_pie.png")
        plt.close()

        with open(f"./app/data/opinions/{self.product_id}.json", "r", encoding="UTF-8") as jf:
            self.opinions = pd.read_json(jf)
        stars = self.opinions["stars"].value_counts().sort_index()
        stars.plot.bar(
            title=f"Liczba opinii z poszczególną liczbą gwiazdek dla produktu {self.product_id}",
            color="orange"
            )
        plt.xlabel("Liczba gwiazdek")
        plt.ylabel("Liczba opinii")
        plt.savefig(f"./app/static/images/charts/{self.product_id}_bar.png", bbox_inches='tight')
        plt.close()

    def export_file(self, file_type):
        if file_type == 'csv':
            with open(f"./app/data/opinions/{self.product_id}.json", "r", encoding="UTF-8") as jf:
                opinions = pd.read_json(jf)
                opinions.to_csv(f"./app/data/opinions/{self.product_id}.csv", encoding="UTF-8")
        elif file_type == 'xlsx':
            with open(f"./app/data/opinions/{self.product_id}.json", "r", encoding="UTF-8") as jf:
                opinions = pd.read_json(jf)
                opinions.to_excel(f"./app/data/opinions/{self.product_id}.xlsx")
