import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

cities = ['Karachi', 'Lahore', 'Islamabad', 'Peshawar', 'Multan']
departments = ['General', 'Cardiology', 'Ortho', 'Dermatology', 'Pediatrics']
doctors = ['Dr A', 'Dr B', 'Dr C', 'Dr D', 'Dr E']
status_list = ['Completed', 'Cancelled', 'No-show']

np.random.seed(42)

def generate_data(n=2000):
    data = []
    for i in range(n):
        city = random.choice(cities)
        dept = random.choice(departments)
        doctor = random.choice(doctors)
        date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 180))
        status = random.choices(status_list, weights=[0.7, 0.1, 0.2])[0]
        fee = random.randint(1000, 5000)
        returning = random.choice([0, 1])
        hour = random.randint(9, 18)

        data.append([
            i, city, dept, doctor, date, status, fee, returning, hour
        ])

    df = pd.DataFrame(data, columns=[
        'patient_id', 'city', 'department', 'doctor',
        'appointment_date', 'status', 'fee', 'returning', 'hour'
    ])

    df.to_csv('meditrack_data.csv', index=False)

if __name__ == '__main__':
    generate_data()