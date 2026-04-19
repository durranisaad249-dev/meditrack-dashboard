import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import pickle


def train_model():
    df = pd.read_csv('meditrack_data.csv')
    df['appointment_date'] = pd.to_datetime(df['appointment_date'])
    df['day_of_week'] = df['appointment_date'].dt.dayofweek
    df['month']       = df['appointment_date'].dt.month
    df['no_show']     = df['status'].apply(lambda x: 1 if x == 'No-show' else 0)

    le_city   = LabelEncoder()
    le_dept   = LabelEncoder()
    le_doctor = LabelEncoder()

    df['city_enc']   = le_city.fit_transform(df['city'])
    df['dept_enc']   = le_dept.fit_transform(df['department'])
    df['doctor_enc'] = le_doctor.fit_transform(df['doctor'])

    features = ['city_enc','dept_enc','doctor_enc','returning','hour','day_of_week','month']
    X = df[features]
    y = df['no_show']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=150, max_depth=8, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("=== Model Evaluation ===")
    print(f"Accuracy: {accuracy_score(y_test, y_pred)*100:.2f}%")
    print(classification_report(y_test, y_pred))

    pickle.dump(model,     open('model.pkl',     'wb'))
    pickle.dump(le_city,   open('le_city.pkl',   'wb'))
    pickle.dump(le_dept,   open('le_dept.pkl',   'wb'))
    pickle.dump(le_doctor, open('le_doctor.pkl', 'wb'))
    print("✅ All model files saved.")


if __name__ == '__main__':
    train_model()