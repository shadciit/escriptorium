from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk as es_bulk

from django.core.management.base import BaseCommand
from core.search import Indexer
from core.models import Project


class Command(BaseCommand):
    help = 'Index all projects by creating a DocumentPart wide transcription for each Document in each Project.'
        
    def handle(self, *args, **options):
        es_client = Elasticsearch()

        for project in Project.objects.all():
            indexer = Indexer(project)
            to_insert = indexer.process()

            nb_inserted, _ = es_bulk(es_client, to_insert, stats_only=True)
            print(f"Inserted {nb_inserted} new entries in index {indexer.index_name}")
