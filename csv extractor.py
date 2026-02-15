import pandas as pd
import os

# Create the folder
os.makedirs("medical_demo_data", exist_ok=True)

# Read the CSV
df = pd.read_csv("mtsamples.csv")

# Grab 5 random rows
sample = df.sample(5)

# Save them as individual text files
for index, row in sample.iterrows():
    # Use the 'medical_specialty' as the filename category
    filename = f"medical_demo_data/patient_{index}_{row['medical_specialty'].replace(' ', '_')}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(str(row['transcription']))

print("Done! Created 5 text files in 'medical_demo_data/'")