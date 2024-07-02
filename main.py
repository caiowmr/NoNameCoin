from flask import Flask, request, jsonify, render_template, redirect, url_for
import time
import sqlite3
from banco import init_db, handle_create_transaction, pass_transaction_to_selector
from validador import validate_transaction, view_validators
from seletor import register_validator, select_validators_route

app = Flask(__name__)
db_name = 'nonamecoin.db'


@app.route('/trans', methods=['POST'])
def create_transaction():
    return handle_create_transaction()

@app.route('/hora', methods=['GET'])
def get_current_time():
    return jsonify({"current_time": time.time()})

@app.route('/validador/validate', methods=['POST'])
def validate_transaction_route():
    return validate_transaction()

@app.route('/view_validators')
def view_validators_route():
    return view_validators()

@app.route('/seletor/register', methods=['POST'])
def register_validator_route():
    return register_validator()

@app.route('/seletor/select', methods=['POST'])
def select_validators():
    return select_validators_route()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        user_id = request.form['user_id']
        balance = request.form['balance']
        try:
            balance = float(balance)
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO accounts (user_id, balance) VALUES (?, ?)", (user_id, balance))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid balance value"}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return render_template('create_account.html')

@app.route('/create_trans', methods=['GET', 'POST'])
def create_transaction_route():
    if request.method == 'POST':
        sender = request.form['sender']
        receiver = request.form['receiver']
        amount = request.form['amount']
        try:
            amount = float(amount)
            data = {
                'sender': sender,
                'receiver': receiver,
                'amount': amount
            }

            response = app.test_client().post('/trans', json=data)
            if response.status_code == 201:
                return redirect(url_for('index'))
            else:
                return jsonify({"status": "error", "message": response.json['message']}), response.status_code
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid amount value"}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return render_template('create_transaction.html')

@app.route('/register_validator', methods=['GET', 'POST'])
def register_validator_page():
    if request.method == 'POST':
        validator_id = request.form['validator_id']
        stake = request.form['stake']
        try:
            stake = float(stake)
            data = {
                'validator_id': validator_id,
                'stake': stake
            }

            response = app.test_client().post('/seletor/register', json=data)
            if response.status_code == 201:
                return redirect(url_for('index'))
            else:
                return jsonify({"status": "error", "message": response.json['message']}), response.status_code
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid stake value"}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return render_template('register_validator.html')

@app.route('/account_info', methods=['GET', 'POST'])
def account_info():
    if request.method == 'POST':
        user_id = request.form['user_id']
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Obtenha o saldo da conta
        cursor.execute("SELECT balance FROM accounts WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()

        # Obtenha o número de transações
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE sender=? OR receiver=?", (user_id, user_id))
        transaction_count = cursor.fetchone()[0]

        conn.close()

        if balance:
            balance = balance[0]
            return render_template('account_info.html', user_id=user_id, balance=balance, transaction_count=transaction_count)
        else:
            return render_template('account_info.html', error="Conta não encontrada")
    return render_template('account_info.html')

@app.route('/view_transactions')
def view_transactions():
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions")
        transactions = cursor.fetchall()

        # Mapeia o resultado para um formato mais legível
        formatted_transactions = []
        for transaction in transactions:
            transaction_id, sender, receiver, amount, fee, timestamp, validation_status, validator_id = transaction
            formatted_timestamp = timestamp_to_string(timestamp)  # Chama a função de filtro para formatar o timestamp
            formatted_transactions.append(
                (transaction_id, sender, receiver, amount, fee, formatted_timestamp, validation_status, validator_id))

        conn.close()
        return render_template('view_transactions.html', transactions=formatted_transactions)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.template_filter('timestamp_to_string')
def timestamp_to_string(timestamp):
    if not timestamp:
        return ""  # Retorna vazio se timestamp for None ou vazio

    try:
        # Converte o timestamp para float (caso não seja)
        timestamp_float = float(timestamp)

        # Converte o timestamp float para datetime
        data_hora = datetime.fromtimestamp(timestamp_float).strftime('%Y-%m-%d %H:%M:%S')

        return data_hora
    except ValueError:
        return f"{timestamp}"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
