uid = session['currentUser']['uid']
collection_ref = db.collection('plant_data')
documents = collection_ref.list_documents()
matching_docs = []
for doc in documents:
    doc_name = doc.id
    if uid in doc_name:
        matching_docs.append(doc.get().to_dict())

for doc in matching_docs:
    if for_plant_slug in doc.id:
        plant_ref = doc
        break

