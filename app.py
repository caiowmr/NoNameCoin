from flask import Flask, request, jsonify, render_template, redirect, url_for
import time
import sqlite3
import random
import uuid

app = Flask(__name__)
db_name = 'nonamecoin.db'


# Função para inicializar o banco de dados
def init_db():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Criação das tabelas
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                      user_id TEXT PRIMARY KEY,
                      balance REAL NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                      transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      sender TEXT NOT NULL,
                      receiver TEXT NOT NULL,
                      amount REAL NOT NULL,
                      fee REAL NOT NULL,
                      timestamp REAL NOT NULL,
                      validation_status INTEGER DEFAULT 0,
                      validator_id TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS validators (
                      validator_id TEXT PRIMARY KEY,
                      stake REAL NOT NULL,
                      status TEXT NOT NULL,
                      unique_key TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS validation_queue (
                      transaction_id INTEGER NOT NULL,
                      validator_id TEXT NOT NULL,
                      status INTEGER DEFAULT 0)''')

    # Nova tabela para armazenar o histórico de validações dos validadores
    cursor.execute('''CREATE TABLE IF NOT EXISTS validator_history (
                      validator_id TEXT NOT NULL,
                      transaction_id INTEGER NOT NULL,
                      validation_status INTEGER,
                      approvals INTEGER,
                      rejections INTEGER,
                      total INTEGER DEFAULT 1,  
                      penalty INTEGER DEFAULT 0,
                      FOREIGN KEY (validator_id) REFERENCES validators (validator_id),
                      FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id))''')

    conn.commit()
    conn.close()


# Banco: Distribuição de transações e informações das contas
@app.route('/trans', methods=['POST'])
def handle_create_transaction():
    try:
        data = request.get_json()
        sender = data['sender']
        receiver = data['receiver']
        amount = data['amount']
        fee = 0.015 * amount
        timestamp = time.time()

        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Checando se o remetente existe e se o seu saldo é o suficiente
        #(Primeira validação 1/5)
        cursor.execute("SELECT balance FROM accounts WHERE user_id=?", (sender,))
        sender_balance = cursor.fetchone()
        if sender_balance is None:
            validation_status = 2
            cursor.execute("INSERT INTO transactions (sender, receiver, amount, fee, timestamp, validation_status) VALUES (?, ?, ?, ?, ?, ?)",
                       (sender, receiver, amount, fee, timestamp, validation_status))
            conn.commit()
            transaction_id = cursor.lastrowid

            validation_status = 0
            approvals = 0
            rejections = 1
            total = 1
            validator_id = '27355d9a-5736-4da4-a47e-f521f85451ec'
            cursor.execute("INSERT INTO validator_history (validator_id,transaction_id, validation_status, approvals, rejections, total) VALUES (?, ?, ?, ?, ?, ?)",
                        (validator_id, transaction_id,validation_status, approvals, rejections, total,))
            conn.commit()
            validator_id = cursor.lastrowid

            conn.close()
            return jsonify({"message": "Remetente não cadastrado!"})
        sender_balance = sender_balance[0]  # Checagem extra para evitar erro de valores nulos

        if sender_balance < amount + fee:
            validation_status = 2
            cursor.execute("INSERT INTO transactions (sender, receiver, amount, fee, timestamp, validation_status) VALUES (?, ?, ?, ?, ?, ?)",
                       (sender, receiver, amount, fee, timestamp, validation_status))
            conn.commit()
            transaction_id = cursor.lastrowid

            validation_status = 0
            approvals = 0
            rejections = 1
            total = 1
            validator_id = '27355d9a-5736-4da4-a47e-f521f85451ec'
            cursor.execute("INSERT INTO validator_history (validator_id,transaction_id, validation_status, approvals, rejections, total) VALUES (?, ?, ?, ?, ?, ?)",
                        (validator_id, transaction_id,validation_status, approvals, rejections, total,))
            conn.commit()
            validator_id = cursor.lastrowid
        
            conn.close()
            return jsonify({"status": "error", "message": "Saldo insuficiente para completar a transação."}), 400

        # Update sender's balance
        new_sender_balance = sender_balance - amount - fee
        cursor.execute("UPDATE accounts SET balance=? WHERE user_id=?", (new_sender_balance, sender))

        # Increment receiver's balance
        cursor.execute("SELECT balance FROM accounts WHERE user_id=?", (receiver,))
        receiver_balance = cursor.fetchone()
        if receiver_balance is None:
            conn.close()
            return jsonify({"status": "error", "message": "Receiver does not exist"}), 400
        receiver_balance = receiver_balance[0]  # Extra check to avoid 'NoneType' error

        new_receiver_balance = receiver_balance + amount
        cursor.execute("UPDATE accounts SET balance=? WHERE user_id=?", (new_receiver_balance, receiver))

        # Create the transaction
        validation_status = 1
        cursor.execute("INSERT INTO transactions (sender, receiver, amount, fee, timestamp,validation_status) VALUES (?, ?, ?, ?, ?, ?)",
                       (sender, receiver, amount, fee, timestamp, validation_status))
        conn.commit()
        transaction_id = cursor.lastrowid


        validation_status = 1
        approvals = 1
        rejections = 0
        total = 1
        validator_id = '27355d9a-5736-4da4-a47e-f521f85451ec'
        cursor.execute("INSERT INTO validator_history (validator_id,transaction_id, validation_status, approvals, rejections, total) VALUES (?, ?, ?, ?, ?, ?)",
                       (validator_id, transaction_id,validation_status, approvals, rejections, total,))
        conn.commit()
        validator_id = cursor.lastrowid
        conn.close()

        # Pass the transaction to the Selector
        pass_transaction_to_selector(transaction_id)

        return jsonify({"status": "success", "message": "Transaction created"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



def pass_transaction_to_selector(transaction_id):
    data = {'transaction_id': transaction_id}
    # Select validators
    select_validators(data)


@app.route('/hora', methods=['GET'])
def get_current_time():
    return jsonify({"current_time": time.time()})


# Seletor: Gerenciamento e seleção de validadores
@app.route('/seletor/register', methods=['POST'])
def register_validator():
    try:
        data = request.get_json()
        validator_id = data['validator_id']
        stake = data['stake']
        unique_key = str(uuid.uuid4())

        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute("INSERT INTO validators (validator_id, stake, status, unique_key) VALUES (?, ?, ?, ?)",
                       (validator_id, stake, 'active', unique_key))
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": "Validator registered", "unique_key": unique_key}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/seletor/select', methods=['POST'])
def select_validators(data=None):
    try:
        if data is None:
            data = request.get_json()
        transaction_id = data['transaction_id']

        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT validator_id, stake FROM validators WHERE status='active'")
        validators = cursor.fetchall()

        if len(validators) < 3:
            return jsonify({"status": "error", "message": "Not enough validators available"}), 400

        # Weighted random selection based on stake
        total_stake = sum([v[1] for v in validators])
        selected_validators = random.choices(
            validators,
            weights=[v[1] / total_stake for v in validators],
            k=3
        )

        for validator in selected_validators:
            cursor.execute("INSERT INTO validation_queue (transaction_id, validator_id) VALUES (?, ?)",
                           (transaction_id, validator[0]))
        conn.commit()
        conn.close()

        # Pass the transaction to the selected validators
        pass_transaction_to_validators(transaction_id, selected_validators)

        return jsonify({"status": "success", "validators": selected_validators}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def pass_transaction_to_validators(transaction_id, validators):
    for validator in validators:
        data = {
            'transaction_id': transaction_id,
            'validator_id': validator[0],
            'unique_key': get_validator_unique_key(validator[0])
        }
        # In a real-world scenario, here we would send the transaction to the validator
        # For simulation purposes, we assume validation is always successful
        validate_transaction(data)


def get_validator_unique_key(validator_id):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("SELECT unique_key FROM validators WHERE validator_id=?", (validator_id,))
    unique_key = cursor.fetchone()[0]
    conn.close()

    return unique_key


# Validador: Validação das transações
@app.route('/validador/validate', methods=['POST'])
def validate_transaction(data=None):
    try:
        if data is None:
            data = request.get_json()
        transaction_id = data['transaction_id']
        validator_id = data['validator_id']
        unique_key = data['unique_key']

        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Verify the unique key
        cursor.execute("SELECT unique_key FROM validators WHERE validator_id=?", (validator_id,))
        stored_key = cursor.fetchone()
        if stored_key is None or stored_key[0] != unique_key:
            conn.close()
            return jsonify({"status": "error", "message": "Invalid validator key"}), 400

        # Validate the transaction (here we assume it's always successful for simulation)
        cursor.execute("UPDATE transactions SET validation_status=1, validator_id=? WHERE transaction_id=?",
                       (validator_id, transaction_id))
        cursor.execute("UPDATE validation_queue SET status=1 WHERE transaction_id=? AND validator_id=?",
                       (transaction_id, validator_id))

        # Update the balances of sender and receiver
        cursor.execute("SELECT sender, receiver, amount, fee FROM transactions WHERE transaction_id=?", (transaction_id,))
        transaction = cursor.fetchone()
        if transaction is None:
            conn.close()
            return jsonify({"status": "error", "message": "Transaction not found"}), 400

        sender = transaction[0]
        receiver = transaction[1]
        amount = transaction[2]
        fee = transaction[3]

        cursor.execute("UPDATE accounts SET balance = balance - ? WHERE user_id = ?", (amount + fee, sender))
        cursor.execute("UPDATE accounts SET balance = balance + ? WHERE user_id = ?", (amount, receiver))

        cursor.execute("INSERT INTO validator_history (validator_id, transaction_id, validation_status) VALUES (?, ?, ?)",
                       (validator_id, transaction_id, 1))
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": "Transaction validated"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/view_validators')
def view_validators():
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM validator_history")

        validators = cursor.fetchall()
        conn.close()
        return render_template('view_validators.html', validators=validators)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Interface web
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
def register_validator_route():
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
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions")
    transactions = cursor.fetchall()
    conn.close()
    return render_template('view_transactions.html', transactions=transactions)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)


# Funcao para adicionar colunas no banco de dados
# def add_column_accounts():
#     conn = sqlite3.connect(db_name)
#     cursor = conn.cursor()

#     # Adicionar coluna 'email' na tabela 'accounts' se ainda não existir
#     cursor.execute('''PRAGMA table_info(validator_history)''')
#     columns = cursor.fetchall()
#     column_names = [col[1] for col in columns]

#     if 'approvals' not in column_names:
#         cursor.execute('''ALTER TABLE validator_history 
#                           ADD COLUMN approvals INTEGER''')
#         conn.commit()
#         print("Coluna 'approvals' adicionada à tabela 'accounts'")
#     if 'rejections' not in column_names:
#         cursor.execute('''ALTER TABLE validator_history 
#                           ADD COLUMN rejections INTEGER''')
#         conn.commit()
#         print("Coluna 'rejections' adicionada à tabela 'accounts'")
#     else:
#         print("Coluna 'rejections' já existe na tabela 'accounts'")
#     if 'total' not in column_names:
#         cursor.execute('''ALTER TABLE validator_history 
#                           ADD COLUMN total INTEGER DEFAULT 1''')
#         conn.commit()
#         print("Coluna 'total' adicionada à tabela 'accounts'")
#     else:
#         print("Coluna 'total' já existe na tabela 'accounts'")

#     conn.close()

# add_column_accounts()