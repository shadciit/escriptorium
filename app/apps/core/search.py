class Indexer:

    def __init__(self, project):
        self.project = project
        self.index_name = f"project-{project.id}"

    def process(self):
        to_insert = []
        for document in self.project.documents.all():
            to_insert += self.process_document(document)

        to_insert = [entry for entry in to_insert if entry["transcription"]]

        return to_insert

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
