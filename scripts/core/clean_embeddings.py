"""
Filter dataset to keep only records with pure Gemini embeddings (3072-dim)
"""
import json

# Load data
print("Loading applicants_with_embeddings.json...")
with open('/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings.json', 'r') as f:
    data = json.load(f)

print(f"Total records: {len(data)}")

# Filter for pure Gemini embeddings (3072-dim only)
clean_data = []
filtered_out = []

for i, record in enumerate(data):
    resume_dim = len(record['embedding_resume'])
    skills_dim = len(record['embedding_skills'])
    tasks_dim = len(record['embedding_tasks'])

    if resume_dim == 3072 and skills_dim == 3072 and tasks_dim == 3072:
        clean_data.append(record)
    else:
        filtered_out.append({
            'index': i,
            'id': record['id'],
            'name': record['full_name'],
            'resume': resume_dim,
            'skills': skills_dim,
            'tasks': tasks_dim
        })

print(f"\n✓ Clean records (all 3072-dim): {len(clean_data)}")
print(f"✗ Filtered out (mixed dimensions): {len(filtered_out)}")

# Save clean data
output_file = '/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings_clean.json'
print(f"\nSaving clean dataset...")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(clean_data, f, ensure_ascii=False)

print(f"✅ Saved clean dataset to: applicants_with_embeddings_clean.json")
print(f"   Records: {len(clean_data)}")
print(f"   All embeddings: 3072 dimensions (pure Gemini)")

# Save filtered records list for reference
filtered_file = '/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/filtered_records.json'
with open(filtered_file, 'w', encoding='utf-8') as f:
    json.dump(filtered_out, f, indent=2)

print(f"\n📋 Filtered records list saved to: filtered_records.json")
print(f"   Count: {len(filtered_out)}")
