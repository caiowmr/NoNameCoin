import sqlite3
import time
from flask import jsonify

db_name = 'nonamecoin.db'

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
            cursor.execute("INSERT INTO validator_history (validator_id, transaction_id, validation_status, approvals, rejections, total) VALUES (?, ?, ?, ?, ?, ?)",
                           (validator_id, transaction_id, validation_status, approvals, rejections, total))
            conn.commit()
            validator_id = cursor.lastrowid

            conn.close()
            return jsonify({"message": "Remetente não cadastrado!"})
        sender_balance = sender_balance[0]

        if sender_balance < amount + fee:
            conn.close()
            return jsonify({"message": "Saldo insuficiente!"})

        cursor.execute("SELECT balance FROM accounts WHERE user_id=?", (receiver,))
        receiver_balance = cursor.fetchone()
        if receiver_balance is None:
            conn.close()
            return jsonify({"message": "Destinatário não encontrado!"})

        receiver_balance = receiver_balance[0]

        cursor.execute("UPDATE accounts SET balance = ? WHERE user_id = ?", (sender_balance - amount - fee, sender))
        cursor.execute("UPDATE accounts SET balance = ? WHERE user_id = ?", (receiver_balance + amount, receiver))

        cursor.execute("INSERT INTO transactions (sender, receiver, amount, fee, timestamp) VALUES (?, ?, ?, ?, ?)",
                       (sender, receiver, amount, fee, timestamp))
        conn.commit()

        transaction_id = cursor.lastrowid

        pass_transaction_to_selector(transaction_id)

        conn.close()

        return jsonify({"message": "Transação criada com sucesso!", "transaction_id": transaction_id}), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def pass_transaction_to_selector(transaction_id):
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT validator_id FROM validators WHERE status = 'active'")
        active_validators = cursor.fetchall()
        if not active_validators:
            conn.close()
            return jsonify({"message": "Nenhum validador ativo disponível!"})

        for validator in active_validators:
            cursor.execute("INSERT INTO validation_queue (transaction_id, validator_id) VALUES (?, ?)",
                           (transaction_id, validator[0]))
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
