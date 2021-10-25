from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk as es_bulk

from django.conf import settings

ES_HOST = settings.ELASTICSEARCH_HOST + ":" + settings.ELASTICSEARCH_PORT


class Indexer:
    es_client = Elasticsearch(hosts=[ES_HOST])

    def __init__(self, project):
        self.project = project
        self.index_name = f"project-{project.id}"

    def configure(self):
        indices = IndicesClient(self.es_client)
        if not indices.exists(self.index_name):
            indices.create(self.index_name)
            print(f"Created a new index named {self.index_name}")

    def process(self):
        to_insert = []
        for document in self.project.documents.all():
            to_insert += self.process_document(document)

        to_insert = [entry for entry in to_insert if entry["transcription"]]

        nb_inserted, _ = es_bulk(self.es_client, to_insert, stats_only=True)
        print(f"Inserted {nb_inserted} new entries in index {self.index_name}")

    def process_document(self, document):
        return [
            {
                "_index": self.index_name,
                "_type": "document",
                "_id": str(part.id),
                "document_id": str(document.id),
                "project_slug": str(self.project.slug),
                "transcription": " ".join([transcription.content for line in part.lines.all() for transcription in line.transcriptions.all()])
            }
            for part in document.parts.all()
        ]
