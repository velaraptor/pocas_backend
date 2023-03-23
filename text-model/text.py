"""Text Model Class"""
import pickle
import time
from datetime import datetime
import requests
from description import descriptions  # pylint: disable=import-error
import spacy
from tqdm import tqdm
from gensim.models.fasttext import FastText
from rank_bm25 import BM25Okapi
import numpy as np
import nmslib


class TextModel:
    """Run Text Model"""

    def __init__(self, epoch=40):
        self.epoch = epoch
        self.api_url = "https://mhpportal.app"
        self.services = None
        self.nlp = spacy.load("en_core_web_sm")
        self.texts = []
        self.tok_text = []
        self.model_name = "_fasttext.model"
        self.weighted_doc_vects = []
        self.ft_model = FastText(
            sg=1,  # use skip-gram: usually gives better results
            window=25,  # window size: 10 tokens before and 10 tokens after to get wider context
            min_count=4,  # only consider tokens with at least n occurrences in the corpus
            negative=25,  # negative subsampling: bigger than default to sample negative examples more
            min_n=3,  # min character n-gram
            max_n=15,  # max character n-gram
        )
        self.index = nmslib.init(method="hnsw", space="cosinesimil")

    def add_descriptions(self):
        """Add descriptions, Note this will be deprecated when added to mongodb"""
        for s, d in zip(self.services, descriptions):
            s["description"] = d

    def get_services(self):
        """Get Services from API"""
        query = f"{self.api_url}/api/v1/services"
        resp = requests.get(query, timeout=10)
        results = resp.json()
        self.services = results["services"]

    @staticmethod
    def unique_list(texts):
        """Create a unique list of words"""
        ulist = []
        for x in texts:
            if x not in ulist:
                ulist.append(x)
        return ulist

    def clean_services(self):
        """Clean services and create text for each document"""
        self.add_descriptions()
        self.texts = []
        for r in self.services:
            text = ""
            for text_choices in [
                "name",
                "city",
                "address",
                "state",
                "general_topic",
                "zip_code",
                "description",
            ]:
                t = r.get(text_choices, " ")
                if t:
                    text += f" {t}"

            text += " " + " ".join(r.get("tags", [""]))
            self.texts.append(text.lower())

    def fix_text(self, x):
        """Fix Text"""
        return " ".join(self.unique_list(x.split()))

    def create_tokens(self):
        """Create tokenized corpus"""
        self.tok_text = []  # for our tokenised corpus
        text = [self.fix_text(str(i)) for i in self.texts]
        for doc in tqdm(self.nlp.pipe(text, disable=["ner"])):
            tok = [
                t.text
                for t in doc
                if (t.is_ascii and not t.is_punct and not t.is_space)
            ]
            # print([t.lemma_ for t in doc])
            self.tok_text.append(tok)

    def train_model(self):
        """Train FastText Model"""
        self.ft_model.build_vocab(self.tok_text)

        self.ft_model.train(
            self.tok_text,
            epochs=self.epoch,
            total_examples=self.ft_model.corpus_count,
            total_words=self.ft_model.corpus_total_words,
        )

    def create_index(self):
        """Create BM250 Index"""
        bm25 = BM25Okapi(self.tok_text)
        self.weighted_doc_vects = []

        for i, doc in tqdm(enumerate(self.tok_text)):
            doc_vector = []
            for word in doc:
                vector = self.ft_model.wv[word]
                # note for newer versions of fasttext you may need to replace ft_model[word] with ft_model.wv[word]
                weight = (
                    bm25.idf[word] * ((bm25.k1 + 1.0) * bm25.doc_freqs[i][word])
                ) / (
                    bm25.k1 * (1.0 - bm25.b + bm25.b * (bm25.doc_len[i] / bm25.avgdl))
                    + bm25.doc_freqs[i][word]
                )
                weighted_vector = vector * weight
                doc_vector.append(weighted_vector)
            doc_vector_mean = np.mean(doc_vector, axis=0)
            self.weighted_doc_vects.append(doc_vector_mean)
        data = np.vstack(self.weighted_doc_vects)
        # initialize a new index, using a HNSW index on Cosine Similarity - can take a couple of mins

        self.index.addDataPointBatch(data)
        self.index.createIndex({"post": 2}, print_progress=True)

    def predict(self, search_query):
        """Predict services based on search query"""
        # querying the index:
        t0 = time.time()
        inpu = search_query.lower().split()
        query = [self.ft_model.wv[vec] for vec in inpu]
        query = np.mean(query, axis=0)
        print(query)
        ids, distances = self.index.knnQuery(query, k=15)
        t1 = time.time()
        print(
            f"Searched {len(self.services)} records in {round(t1 - t0, 4)} seconds \n"
        )
        ids = []
        for i, j in zip(ids, distances):
            if j < 0.3:
                ids.append(self.services[i]["id"])
        return ids

    def run(self):
        """Run model training and indexing"""
        self.get_services()
        self.add_descriptions()
        self.clean_services()
        self.create_tokens()
        self.train_model()
        self.create_index()

    def load_recent_model(self):
        """Load Model from Spaces"""
        return None

    def save_model(self):
        """Save Model to Spaces"""
        model = {
            "fast_text_model": self.ft_model,
            "index": self.index,
            "services": self.services,
            "date": datetime.now(),
            "weighted_docs": self.weighted_doc_vects,
        }
        with open(f"model_{datetime.now()}", "wb") as file:
            pickle.dump(model, file)
