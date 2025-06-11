import re
from datetime import datetime
print("Loading extractor.py...")

def extract_patient_data(text):
    data = {}
    
    age_match = re.search(r"(\d+)[- ]year[- ]old", text, re.IGNORECASE)
    if age_match:
        data['age'] = int(age_match.group(1))

    if re.search(r"\bfemale\b", text, re.IGNORECASE):
        data['gender'] = 'female'
    elif re.search(r"\bmale\b", text, re.IGNORECASE):
        data['gender'] = 'male'

    height = re.search(r"(\d+)\s?cm", text)
    weight = re.search(r"(\d+)\s?kg", text)
    if height: data['height_cm'] = int(height.group(1))
    if weight: data['weight_kg'] = int(weight.group(1))

    consent = re.search(r"consent.*on (\d{4}-\d{2}-\d{2})", text)
    dob = re.search(r"(?:date of birth|dob)[\s:]+(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if consent: data['date_of_consent'] = consent.group(1)
    if dob: data['dob'] = dob.group(1)

    if 'height_cm' in data and 'weight_kg' in data:
        height_m = data['height_cm'] / 100
        data['bmi'] = round(data['weight_kg'] / (height_m ** 2), 2)

    return data
