"""Text Model Class"""
import pickle
import time
import os
import sys
import threading
from datetime import datetime
import requests
from description import descriptions  # pylint: disable=import-error
import spacy
from tqdm import tqdm
from gensim.models.fasttext import FastText, FastTextKeyedVectors
from rank_bm25 import BM25Okapi
import numpy as np
import nmslib
import boto3
from boto3.s3.transfer import TransferConfig
import compress_fasttext

# pylint: disable=C0209, R0903, W0702, R0801


class ProgressPercentage:
    """Progress for Boto Uploading"""

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)"
                % (self._filename, self._seen_so_far, self._size, percentage)
            )
            sys.stdout.flush()


# TODO: Add Descriptions to MongoDB;
# Add in Admin to trigger change if model change ; add rabbitmq, add in API to get recent model and load


class TextModel:
    """Run Text Model"""

    def __init__(self, epoch=20):
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
            window=30,  # window size: 10 tokens before and 10 tokens after to get wider context
            min_count=3,  # only consider tokens with at least n occurrences in the corpus
            negative=25,  # negative subsampling: bigger than default to sample negative examples more
            min_n=3,  # min character n-gram
            max_n=15,  # max character n-gram
        )
        self.index = nmslib.init(method="hnsw", space="cosinesimil")
        self.__session = boto3.session.Session()
        self.client = self.__session.client(
            "s3",
            endpoint_url=(
                f"https://{os.getenv('SPACES_REGION', 'sfo3')}.digitaloceanspaces.com"
            ),
            region_name=os.getenv(
                "SPACES_REGION", "sfo3"
            ),  # Use the region in your endpoint.
            aws_access_key_id=os.getenv("SPACES_KEY_ID", "DO00WXAJ82236KQQJWQC"),
            # Access key pair. You can create access key pairs using the control panel or API.
            aws_secret_access_key=os.getenv(
                "SPACES_SECRET", "tN6BrdAm3MW6IBBzcifF/Jt+D9zHN4DaVpzt/Qe185E"
            ),
        )
        self.object_key = None
        self.object_key_index = None

    def add_descriptions(self):
        """Add descriptions, Note this will be deprecated when added to mongodb"""
        # TODO: write these to mongodb
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
                # "general_topic",
                "description",
            ]:
                t = r.get(text_choices, " ")
                if t:
                    text += f" {t}"

            # text += " " + " ".join(r.get("tags", [""]))
            self.texts.append(text.lower())

    def fix_text(self, x):
        """Fix Text"""
        return " ".join(self.unique_list(x.split()))

    def create_tokens(self):
        """Create tokenized corpus"""
        self.tok_text = []  # for our tokenized corpus
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
            doc_vector_mean = np.median(doc_vector, axis=0)
            self.weighted_doc_vects.append(doc_vector_mean)
        data = np.vstack(self.weighted_doc_vects)
        # initialize a new index, using a HNSW index on Cosine Similarity - can take a couple of mins

        self.index.addDataPointBatch(data)

        params = {"M": 100, "indexThreadQty": 1, "efConstruction": 200, "post": 2}
        self.index.createIndex(params, print_progress=True)

    def predict(self, search_query):
        """Predict services based on search query"""
        # querying the index:
        t0 = time.time()
        inpu = search_query.lower().split()
        try:
            query = [self.ft_model.wv[vec] for vec in inpu]
        except:  # noqa: E722
            query = [self.ft_model[vec] for vec in inpu]
        query = np.mean(query, axis=0)
        print(query)
        ids, distances = self.index.knnQuery(query, k=30)
        t1 = time.time()
        print(
            f"Searched {len(self.services)} records in {round(t1 - t0, 4)} seconds \n"
        )
        queried_ids = []
        for i, j in zip(ids, distances):
            if j < 0.4:
                print(i, j)
                queried_ids.append(self.services[i]["id"])
        return queried_ids

    def run(self):
        """Run model training and indexing"""
        self.get_services()
        self.add_descriptions()
        self.clean_services()
        self.create_tokens()
        self.train_model()
        self.create_index()

    def get_max_str_date(self):
        """Find Max Model in Spaces"""
        paginator = self.client.get_paginator("list_objects")
        dates = []
        result = paginator.paginate(
            Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
            Delimiter="/",
            Prefix="model/",
        )
        for prefix in result.search("CommonPrefixes"):
            folder = datetime.strptime(prefix.get("Prefix").split("/")[-2], "%m_%d_%Y")
            dates.append(folder)
        max_date = max(dates)
        max_str_date = datetime.strftime(max_date, "%m_%d_%Y")
        return max_str_date

    def load_recent_model(self):
        """Load Model from Spaces"""
        max_str_date = self.get_max_str_date()
        payload = self.client.get_object(
            Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
            Key=f"model/{max_str_date}/model.pickle",
        )
        data = pickle.loads(payload["Body"].read())
        self.services = data["services"]

        self.client.download_file(
            os.getenv("SPACES_BUCKET", "mhpportal"),
            f"model/{max_str_date}/index.bin",
            "index.bin",
        )

        self.index.loadIndex("index.bin", load_data=True)
        config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True,
        )

        meta_data = self.client.head_object(
            Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
            Key=f"model/{max_str_date}/ft_model.pickle",
        )
        total_length = int(meta_data.get("ContentLength", 0))
        downloaded = 0

        def progress(chunk):
            nonlocal downloaded
            downloaded += chunk
            done = int(50 * downloaded / total_length)
            sys.stdout.write(
                "\r[%s%s]  (%.2f%%)" % ("=" * done, " " * (50 - done), done * 2)
            )
            sys.stdout.flush()

        with open("ft_model_2.bin", "wb") as file:
            self.client.download_fileobj(
                Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
                Config=config,
                Key=f"model/{max_str_date}/ft_model.bin",
                Fileobj=file,
                Callback=progress,
            )

        self.ft_model = compress_fasttext.models.CompressedFastTextKeyedVectors.load(
            "ft_model_2.bin"
        )

    def save_model(self):
        """Save Model to Spaces"""
        model = {
            "services": self.services,
            "date": datetime.now(),
            "weighted_docs": self.weighted_doc_vects,
        }
        with open("model.pickle", "wb") as file:
            pickle.dump(model, file)
        directory_date = datetime.strftime(datetime.now(), "%m_%d_%Y")
        self.object_key = f"model/{directory_date}/model.pickle"
        self.object_key_index = f"model/{directory_date}/index.bin"
        print(f"Writing object to key: {self.object_key}")
        config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True,
        )
        self.index.saveIndex("index.bin", save_data=True)

        self.client.upload_file(
            "index.bin",
            os.getenv("SPACES_BUCKET", "mhpportal"),
            self.object_key_index,
            ExtraArgs={"ACL": "public-read"},
            Config=config,
            Callback=ProgressPercentage("index.bin"),
        )

        self.client.upload_file(
            "model.pickle",
            os.getenv("SPACES_BUCKET", "mhpportal"),
            self.object_key,
            ExtraArgs={"ACL": "public-read"},
            Config=config,
            Callback=ProgressPercentage("model.pickle"),
        )

        self.ft_model.save("ft.model")
        big_model = FastTextKeyedVectors.load("ft.model")
        small_model = compress_fasttext.prune_ft_freq(big_model.wv, pq=True)
        small_model.save("ft_model.bin")
        ft_model_object_key = f"model/{directory_date}/ft_model.bin"
        self.client.upload_file(
            "ft_model.bin",
            os.getenv("SPACES_BUCKET", "mhpportal"),
            ft_model_object_key,
            ExtraArgs={"ACL": "public-read"},
            Config=config,
            Callback=ProgressPercentage("ft_model.bin"),
        )

        self.client.upload_file(
            "ft_model.bin.wv.vectors_ngrams.npy",
            os.getenv("SPACES_BUCKET", "mhpportal"),
            f"model/{directory_date}/ft.model.bin.wv.vectors_ngrams.npy",
            ExtraArgs={"ACL": "public-read"},
            Config=config,
            Callback=ProgressPercentage("ft_model.bin.wv.vectors_ngrams.npy"),
        )
