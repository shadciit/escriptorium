from core.models import Project
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk as es_bulk

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Index projects by creating DocumentPart wide transcriptions for each Document in each Project."

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-pks",
            nargs="+",
            type=int,
            help="Specify a few project PKs to index. If unset, all projects will be indexed by default.",
        )

    def handle(self, *args, **options):
        if not settings.ELASTICSEARCH_URL:
            print("Please define ELASTICSEARCH_URL Django setting to use this command.")
            return

        self.es_client = Elasticsearch(hosts=[settings.ELASTICSEARCH_URL])
        if not self.es_client.ping():
            print(
                f"Unable to connect to Elasticsearch host defined as {settings.ELASTICSEARCH_URL}."
            )
            return

        if options.get("project_pks") is not None:
            projects = Project.objects.filter(pk__in=options["project_pks"])
        else:
            projects = Project.objects.all()

        for project in projects:
            print("\n" + "-" * 50)
            print(f"Indexing project {project.name} (PK={project.pk})...")
            self.index_project(project)

    def create_project_index(self, name):
        indices = IndicesClient(self.es_client)
        if not indices.exists(name):
            indices.create(name)
            print(f"Created a new index named {name}")

    def index_project(self, project):
        index_name = f"escriptorium-data-project-{project.pk}"
        self.create_project_index(index_name)

        to_insert = []
        for document in project.documents.all():
            to_insert += self.process_document(index_name, document)

        to_insert = [entry for entry in to_insert if entry["transcription_text"]]

        nb_inserted, _ = es_bulk(self.es_client, to_insert, stats_only=True)
        print(f"Inserted {nb_inserted} new entries in index {index_name}")
        print("-" * 50)

    def process_document(self, index, document):
        return [
            {
                "_index": index,
                "_id": f"{part.id}/{transcription.id}",
                "document_id": document.id,
                "document_part_id": part.id,
                "transcription_id": transcription.id,
                "transcription_text": " ".join(
                    [
                        line.transcriptions.get(transcription=transcription).content
                        for line in part.lines.all()
                        if line.transcriptions.filter(
                            transcription=transcription
                        ).exists()
                    ]
                ),
            }
            for part in document.parts.all()
            for transcription in document.transcriptions.all()
        ]
