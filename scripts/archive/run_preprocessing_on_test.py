import csv
import json
from test_preprocessing import preprocess_applicant_data

def process_csv(input_file, output_file, sample_size=10):
    """
    Process test.csv and generate preprocessed output.

    Args:
        input_file: Path to test.csv
        output_file: Path to output JSON file
        sample_size: Number of records to show in console output
    """
    processed_records = []

    print(f"Reading and preprocessing {input_file}...")
    print("=" * 80)

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            try:
                # Preprocess the row
                processed = preprocess_applicant_data(row)
                processed_records.append(processed)

                # Show first few records
                if i < sample_size:
                    print(f"\nRecord {i+1}:")
                    print(f"  Name: {processed['full_name']}")
                    print(f"  Job: {processed['job_title']}")
                    print(f"  Education: {processed['education_level']}")
                    print(f"  Experience: {processed['total_years_experience']} years")
                    print(f"  Current Company: {processed['current_company']}")
                    print(f"  Skills: {processed['skills_extracted']}")
                    print(f"  Location: {processed['location']}")
                    print(f"  Stage: {processed['current_stage']}")

            except Exception as e:
                print(f"\nError processing row {i+1}: {e}")
                continue

    # Save to JSON
    print(f"\n{'=' * 80}")
    print(f"Saving {len(processed_records)} processed records to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_records, f, indent=2, ensure_ascii=False)

    print(f"✓ Successfully processed {len(processed_records)} records")

    # Generate statistics
    print(f"\n{'=' * 80}")
    print("PROCESSING STATISTICS")
    print("=" * 80)

    # Education distribution
    education_dist = {}
    for rec in processed_records:
        edu = rec['education_level']
        education_dist[edu] = education_dist.get(edu, 0) + 1

    print("\nEducation Distribution:")
    for edu, count in sorted(education_dist.items(), key=lambda x: x[1], reverse=True):
        print(f"  {edu}: {count}")

    # Location distribution
    location_dist = {}
    for rec in processed_records:
        loc = rec['location']
        location_dist[loc] = location_dist.get(loc, 0) + 1

    print("\nTop 10 Locations:")
    for loc, count in sorted(location_dist.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {loc}: {count}")

    # Experience statistics
    experiences = [rec['total_years_experience'] for rec in processed_records if rec['total_years_experience'] > 0]
    if experiences:
        avg_exp = sum(experiences) / len(experiences)
        print(f"\nExperience Statistics:")
        print(f"  Average: {avg_exp:.2f} years")
        print(f"  Min: {min(experiences):.1f} years")
        print(f"  Max: {max(experiences):.1f} years")

    # Skills analysis
    all_skills = set()
    for rec in processed_records:
        if rec['skills_extracted']:
            skills = rec['skills_extracted'].split(', ')
            all_skills.update(skills)

    print(f"\nTotal Unique Skills Detected: {len(all_skills)}")
    print(f"Skills: {', '.join(sorted(all_skills))}")

    # Stage distribution
    stage_dist = {}
    for rec in processed_records:
        stage = rec['current_stage']
        stage_dist[stage] = stage_dist.get(stage, 0) + 1

    print("\nApplication Stage Distribution:")
    for stage, count in sorted(stage_dist.items(), key=lambda x: x[1], reverse=True):
        print(f"  {stage}: {count}")

    return processed_records


if __name__ == "__main__":
    input_csv = "/mnt/c/Users/prita/Downloads/SuperLinked/test_fixed.csv"
    output_json = "/mnt/c/Users/prita/Downloads/SuperLinked/preprocessed_data.json"

    processed_data = process_csv(input_csv, output_json, sample_size=5)

    print(f"\n{'=' * 80}")
    print("PREPROCESSING COMPLETE")
    print("=" * 80)
    print(f"Output saved to: {output_json}")
    print(f"Total records processed: {len(processed_data)}")