"""Test GPT extraction on a small sample"""
import csv
import json
from load_env import load_env
from preprocess_with_gpt import GPTExtractor, preprocess_applicant_data

# Load environment
load_env()

# Initialize GPT extractor
try:
    extractor = GPTExtractor()
    print("✓ GPT Extractor initialized successfully")
    print(f"✓ Model: {extractor.model}")
except Exception as e:
    print(f"❌ Failed to initialize GPT: {e}")
    print("→ Please check your API key in .env file")
    exit(1)

# Test on first 10 records
INPUT_CSV = "/mnt/c/Users/prita/Downloads/SuperLinked/test_fixed.csv"
TEST_SIZE = 10

print(f"\n{'=' * 80}")
print(f"Testing GPT extraction on first {TEST_SIZE} records")
print("=" * 80)

with open(INPUT_CSV, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)

    for i, row in enumerate(reader):
        if i >= TEST_SIZE:
            break

        print(f"\n{'─' * 80}")
        print(f"[{i+1}] {row.get('Full Name', 'N/A')}")
        print("─" * 80)

        try:
            # Process with GPT
            processed = preprocess_applicant_data(row, gpt_extractor=extractor)

            print(f"\n📍 Location (GPT):")
            print(f"   {processed['location']}")

            print(f"\n💼 Work Experience (GPT):")
            print(f"   Total: {processed['total_years_experience']:.1f} years")
            print(f"   Current: {processed['current_company']}")
            print(f"   Companies: {processed['company_names']}")

            print(f"\n🛠  Skills (GPT):")
            if processed['skills_extracted']:
                skills = processed['skills_extracted'].split(', ')
                for skill in skills[:10]:  # Show first 10
                    print(f"   • {skill}")
                if len(skills) > 10:
                    print(f"   ... and {len(skills) - 10} more")
            else:
                print("   (none detected)")

            print(f"\n📚 Education: {processed['education_level']}")
            print(f"🎯 Job: {processed['job_title']}")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue

print(f"\n{'=' * 80}")
print("✓ Test complete!")
print("=" * 80)
print("\nNext steps:")
print("1. Review the extracted data above")
print("2. If it looks good, run: python3 preprocess_with_gpt.py")
print("3. This will process all 5000 records (~$4-5 cost)")