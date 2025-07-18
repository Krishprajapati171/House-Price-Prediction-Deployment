from flask import Flask, render_template, request, redirect, url_for, session, flash
import numpy as np
import joblib
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Admin login credentials
ADMIN_USERNAME = 'krish'
ADMIN_PASSWORD = 'Krish@32900'

# 🔐 FreeSQLDatabase connection details
DB_CONFIG = {
    'host': 'sql12.freesqldatabase.com',   # ✅ Replace with your actual host
    'user': 'sql12790611',                # ✅ Replace with your actual username
    'password': 'AwccmwR6KZ',        # ✅ Replace with your actual password
    'database': 'sql12790611',            # ✅ Replace with your actual DB name
    'port': 3306
}

# Load model and scaler
model = joblib.load('house_price_model.pkl')
scaler = joblib.load('scaler.pkl')

# ✅ Check if feature_id already exists in DB
def is_duplicate_id(feature_id):
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE feature_id = %s", (feature_id,))
        count = cursor.fetchone()[0]
        cursor.close()
        connection.close()
        return count > 0
    except Exception as e:
        print(f"❌ MySQL Check Error: {e}")
        return True

# ✅ Insert prediction data into MySQL
def insert_data_to_mysql(data, predicted_price):
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        sql = """
        INSERT INTO predictions (
            feature_id, lot_area, overall_qual, overall_cond, mas_vnr_area,
            bsmt_fin_sf2, bsmt_unf_sf, total_bsmt_sf, first_flr_sf, second_flr_sf,
            low_qual_fin_sf, gr_liv_area, bsmt_full_bath, bsmt_half_bath,
            full_bath, half_bath, bedroom_abv_gr, kitchen_abv_gr,
            tot_rms_abv_grd, fireplaces, garage_cars, wood_deck_sf,
            open_porch_sf, enclosed_porch, porch_3ssn, screen_porch,
            pool_area, misc_val, predicted_price
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, tuple(data + [predicted_price]))
        connection.commit()
        cursor.close()
        connection.close()
        print("✅ Data inserted into MySQL.")
    except Exception as e:
        print(f"❌ MySQL Insert Error: {e}")

# ---------------- ROUTES ---------------- #

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/predict-form')
def predict_form():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        feature_names = [
            'Id', 'LotArea', 'OverallQual', 'OverallCond', 'MasVnrArea',
            'BsmtFinSF2', 'BsmtUnfSF', 'TotalBsmtSF', 'FirstFlrSF', 'SecondFlrSF',
            'LowQualFinSF', 'GrLivArea', 'BsmtFullBath', 'BsmtHalfBath',
            'FullBath', 'HalfBath', 'BedroomAbvGr', 'KitchenAbvGr',
            'TotRmsAbvGrd', 'Fireplaces', 'GarageCars', 'WoodDeckSF',
            'OpenPorchSF', 'EnclosedPorch', 'ThreeSsnPorch', 'ScreenPorch',
            'PoolArea', 'MiscVal'
        ]

        input_features = []
        for feature in feature_names:
            value = request.form.get(feature)
            if not value:
                return f"❌ Error: Missing value for '{feature}'"
            float_value = float(value)
            if float_value < 0:
                return f"❌ Error: '{feature}' cannot be negative."
            input_features.append(float_value)

        feature_id = int(input_features[0])
        if is_duplicate_id(feature_id):
            return render_template('index.html', prediction_text=f"⚠️ Feature ID {feature_id} already exists. Use a unique ID.")

        scaled_input = scaler.transform([input_features])
        prediction = model.predict(scaled_input)[0]
        prediction = round(prediction, 2)

        insert_data_to_mysql(input_features, prediction)

        return render_template('index.html', prediction_text=f"💰 Estimated House Price: ₹{prediction:,.2f}")

    except Exception as e:
        return f"❌ Prediction Error: {str(e)}"

# 🔐 Admin Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user'] = username
            flash('✅ Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid credentials.', 'error')
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

# 📊 Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('🔐 Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))

    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM predictions ORDER BY feature_id ASC")
        records = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('dashboard.html', records=records)
    except Exception as e:
        return f"❌ Dashboard Error: {str(e)}"

# 🚪 Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('👋 You have been logged out.', 'info')
    return redirect(url_for('login'))

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
