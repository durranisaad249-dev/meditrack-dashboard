import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

cities       = ['Karachi', 'Lahore', 'Islamabad', 'Peshawar', 'Multan']
departments  = ['General', 'Cardiology', 'Ortho', 'Dermatology', 'Pediatrics', 'MBBS', 'Physiotherapy']
doctors      = [
    ('Dr.Hammad', 'Physiotherapist'),
    ('Dr.Saad',   'MBBS Specialist'),
    ('Dr.Aleena', 'Cardiologist'),
    ('Dr.Maryam', 'Neurologist'),
]
status_list  = ['Completed', 'Cancelled', 'No-show']
first_names  = ['Ali','Ahmed','Sara','Fatima','Usman','Ayesha','Hassan','Zainab','Omar',
                'Hira','Bilal','Nadia','Tariq','Sana','Imran','Rabia','Kamran','Amna',
                'Farhan','Nimra','Babar','Saima','Faisal','Mehwish','Shahid']
last_names   = ['Khan','Ahmed','Ali','Sheikh','Malik','Qureshi','Hussain','Butt',
                'Chaudhry','Rana','Mirza','Siddiqui']

np.random.seed(42)
random.seed(42)


def generate_data(n=2000):
    data = []
    for i in range(n):
        city   = random.choice(cities)
        dept   = random.choice(departments)
        doctor, spec = random.choice(doctors)
        date   = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 180))
        status = random.choices(status_list, weights=[0.7, 0.1, 0.2])[0]
        fee    = random.randint(1000, 5000)
        ret    = random.choice([0, 1])
        hour   = random.randint(9, 18)
        first  = random.choice(first_names)
        last   = random.choice(last_names)
        name   = f"{first} {last}"
        email  = f"{first.lower()}.{last.lower()}{random.randint(1,99)}@gmail.com"
        phone  = f"03{random.randint(0,3)}{random.randint(1000000,9999999)}"
        data.append([i, name, email, phone, city, dept, doctor, spec,
                     date, status, fee, ret, hour])

    df = pd.DataFrame(data, columns=[
        'patient_id','patient_name','email','phone',
        'city','department','doctor','specialization',
        'appointment_date','status','fee','returning','hour'
    ])
    df.to_csv('meditrack_data.csv', index=False)
    print(f"✅ {n} records saved to meditrack_data.csv")


if __name__ == '__main__':
    generate_data()