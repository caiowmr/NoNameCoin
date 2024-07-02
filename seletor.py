import sqlite3
import uuid
from flask import jsonify, request

db_name = 'nonamecoin.db'

def register_validator():
    try:
        data = request.get_json()
        validator_id = data['validator_id']
        stake = data['stake']
        unique_key = str(uuid.uuid4())
        status = 'active'

        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO validators (validator_id, stake, status, unique_key) VALUES (?, ?, ?, ?)",
                       (validator_id, stake, status, unique_key))
        conn.commit()
        conn.close()

        return jsonify({"message": "Validador registrado com sucesso!", "unique_key": unique_key}), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def select_validators_route():
    try:
        data = request.get_json()
        transaction_id = data['transaction_id']

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

        return jsonify({"message": "Validadores selecionados e transação enviada para validação!"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
