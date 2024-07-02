import sqlite3
from flask import jsonify, request

db_name = 'nonamecoin.db'

def validate_transaction():
    try:
        data = request.get_json()
        validator_id = data['validator_id']
        transaction_id = data['transaction_id']
        approval = data['approval']

        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM validation_queue WHERE transaction_id=? AND validator_id=?",
                       (transaction_id, validator_id))
        validation = cursor.fetchone()
        if not validation:
            conn.close()
            return jsonify({"message": "Transação ou validador não encontrado na fila de validação!"})

        cursor.execute("SELECT * FROM transactions WHERE transaction_id=?", (transaction_id,))
        transaction = cursor.fetchone()
        if not transaction:
            conn.close()
            return jsonify({"message": "Transação não encontrada!"})

        new_status = 1 if approval else 2
        cursor.execute("UPDATE transactions SET validation_status=?, validator_id=? WHERE transaction_id=?",
                       (new_status, validator_id, transaction_id))

        if new_status == 1:
            cursor.execute("UPDATE accounts SET balance = balance - (SELECT fee FROM transactions WHERE transaction_id=?) WHERE user_id = (SELECT sender FROM transactions WHERE transaction_id=?)",
                           (transaction_id, transaction_id))

        cursor.execute("DELETE FROM validation_queue WHERE transaction_id=? AND validator_id=?",
                       (transaction_id, validator_id))

        cursor.execute("SELECT * FROM validator_history WHERE transaction_id=? AND validator_id=?", (transaction_id, validator_id))
        existing_validation = cursor.fetchone()
        if existing_validation:
            approvals = existing_validation[3] + (1 if approval else 0)
            rejections = existing_validation[4] + (1 if not approval else 0)
            total = approvals + rejections
            cursor.execute("UPDATE validator_history SET validation_status=?, approvals=?, rejections=?, total=? WHERE transaction_id=? AND validator_id=?",
                           (new_status, approvals, rejections, total, transaction_id, validator_id))
        else:
            approvals = 1 if approval else 0
            rejections = 1 if not approval else 0
            total = 1
            cursor.execute("INSERT INTO validator_history (validator_id, transaction_id, validation_status, approvals, rejections, total) VALUES (?, ?, ?, ?, ?, ?)",
                           (validator_id, transaction_id, new_status, approvals, rejections, total))

        conn.commit()
        conn.close()

        return jsonify({"message": "Transação validada com sucesso!"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def view_validators():
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT validator_id, status, stake, unique_key FROM validators")
        validators = cursor.fetchall()

        conn.close()
        return jsonify({"validators": validators})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
