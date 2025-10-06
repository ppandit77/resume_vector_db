import csv

with open('/mnt/c/Users/prita/Downloads/SuperLinked/test.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)

    print("Headers:", reader.fieldnames)
    print("\n" + "="*80)

    for i, row in enumerate(reader):
        if i < 3:
            print(f"\nRow {i+1}:")
            print(f"  Full Name: {row.get('Full Name', 'N/A')[:80]}")
            print(f"  Job Title: {row.get('Job Title (from JOB #)', 'N/A')[:80]}")
            print(f"  GPT COMPANY: {row.get('GPT COMPANY', 'N/A')[:80]}")
            print(f"  Resume TXT: {row.get('Resume TXT', 'N/A')[:80]}")
        else:
            break