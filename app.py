import os
import sqlite3
from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)


def get_db_path():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(root_dir, 'flowers_store.db')


def get_db():
    if not hasattr(g, 'db'):
        g.db = sqlite3.connect(get_db_path())
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    db = get_db()
    categories = db.execute('SELECT * FROM Categories ORDER BY name').fetchall()
    flowers = db.execute(
        'SELECT f.*, c.name AS category_name FROM Flowers f JOIN Categories c ON c.id = f.category_id ORDER BY f.id DESC'
    ).fetchall()
    return render_template('index.html', page='home', categories=categories, flowers=flowers)


@app.route('/flower/new', methods=['GET', 'POST'])
def flower_new():
    db = get_db()
    categories = db.execute('SELECT * FROM Categories ORDER BY name').fetchall()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '0').strip() or '0'
        stock = request.form.get('stock', '0').strip() or '0'
        color = request.form.get('color', '').strip()
        category_id = request.form.get('category_id')
        db.execute(
            'INSERT INTO Flowers (name, price, stock, color, category_id) VALUES (?, ?, ?, ?, ?)',
            (name, float(price), int(stock), color, int(category_id)),
        )
        db.commit()
        return redirect(url_for('index'))

    return render_template(
        'index.html',
        page='flower_form',
        form_type='new',
        categories=categories,
        flower=None,
    )


@app.route('/flower/edit/<int:flower_id>', methods=['GET', 'POST'])
def flower_edit(flower_id):
    db = get_db()
    categories = db.execute('SELECT * FROM Categories ORDER BY name').fetchall()
    flower = db.execute('SELECT * FROM Flowers WHERE id = ?', (flower_id,)).fetchone()
    if flower is None:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '0').strip() or '0'
        stock = request.form.get('stock', '0').strip() or '0'
        color = request.form.get('color', '').strip()
        category_id = request.form.get('category_id')
        db.execute(
            'UPDATE Flowers SET name = ?, price = ?, stock = ?, color = ?, category_id = ? WHERE id = ?',
            (name, float(price), int(stock), color, int(category_id), flower_id),
        )
        db.commit()
        return redirect(url_for('index'))

    return render_template(
        'index.html',
        page='flower_form',
        form_type='edit',
        categories=categories,
        flower=flower,
    )


@app.route('/flower/delete/<int:flower_id>', methods=['POST'])
def flower_delete(flower_id):
    db = get_db()
    db.execute('DELETE FROM Flowers WHERE id = ?', (flower_id,))
    db.commit()
    return redirect(url_for('index'))


@app.route('/category/new', methods=['GET', 'POST'])
def category_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        db = get_db()
        db.execute('INSERT INTO Categories (name, description) VALUES (?, ?)', (name, description))
        db.commit()
        return redirect(url_for('index'))

    return render_template('index.html', page='category_form', form_type='new', category=None)


@app.route('/category/edit/<int:category_id>', methods=['GET', 'POST'])
def category_edit(category_id):
    db = get_db()
    category = db.execute('SELECT * FROM Categories WHERE id = ?', (category_id,)).fetchone()
    if category is None:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        db.execute('UPDATE Categories SET name = ?, description = ? WHERE id = ?', (name, description, category_id))
        db.commit()
        return redirect(url_for('index'))

    return render_template('index.html', page='category_form', form_type='edit', category=category)


@app.route('/category/delete/<int:category_id>', methods=['POST'])
def category_delete(category_id):
    db = get_db()
    db.execute('DELETE FROM Flowers WHERE category_id = ?', (category_id,))
    db.execute('DELETE FROM Categories WHERE id = ?', (category_id,))
    db.commit()
    return redirect(url_for('index'))


def row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


@app.route('/api/flowers', methods=['GET'])
def api_flowers_list():
    db = get_db()
    rows = db.execute(
        'SELECT f.*, c.name AS category_name FROM Flowers f JOIN Categories c ON c.id = f.category_id ORDER BY f.id DESC'
    ).fetchall()
    return jsonify([row_to_dict(row) for row in rows])


@app.route('/api/flowers/<int:flower_id>', methods=['GET'])
def api_flower_detail(flower_id):
    db = get_db()
    row = db.execute(
        'SELECT f.*, c.name AS category_name FROM Flowers f JOIN Categories c ON c.id = f.category_id WHERE f.id = ?',
        (flower_id,),
    ).fetchone()
    if row is None:
        abort(404)
    return jsonify(row_to_dict(row))


@app.route('/api/flowers', methods=['POST'])
def api_flower_create():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    price = data.get('price', 0)
    stock = data.get('stock', 0)
    color = data.get('color', '').strip()
    category_id = data.get('category_id')
    if not name or category_id is None:
        abort(400, 'name and category_id are required')
    db = get_db()
    cursor = db.execute(
        'INSERT INTO Flowers (name, price, stock, color, category_id) VALUES (?, ?, ?, ?, ?)',
        (name, float(price), int(stock), color, int(category_id)),
    )
    db.commit()
    return jsonify({'id': cursor.lastrowid}), 201


@app.route('/api/flowers/<int:flower_id>', methods=['PUT'])
def api_flower_update(flower_id):
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    price = data.get('price', 0)
    stock = data.get('stock', 0)
    color = data.get('color', '').strip()
    category_id = data.get('category_id')
    if not name or category_id is None:
        abort(400, 'name and category_id are required')
    db = get_db()
    cursor = db.execute(
        'UPDATE Flowers SET name = ?, price = ?, stock = ?, color = ?, category_id = ? WHERE id = ?',
        (name, float(price), int(stock), color, int(category_id), flower_id),
    )
    db.commit()
    if cursor.rowcount == 0:
        abort(404)
    return jsonify({'id': flower_id})


@app.route('/api/flowers/<int:flower_id>', methods=['DELETE'])
def api_flower_delete(flower_id):
    db = get_db()
    cursor = db.execute('DELETE FROM Flowers WHERE id = ?', (flower_id,))
    db.commit()
    if cursor.rowcount == 0:
        abort(404)
    return jsonify({'deleted': flower_id})


@app.route('/api/categories', methods=['GET'])
def api_categories_list():
    db = get_db()
    rows = db.execute('SELECT * FROM Categories ORDER BY name').fetchall()
    return jsonify([row_to_dict(row) for row in rows])


@app.route('/api/categories/<int:category_id>', methods=['GET'])
def api_category_detail(category_id):
    db = get_db()
    row = db.execute('SELECT * FROM Categories WHERE id = ?', (category_id,)).fetchone()
    if row is None:
        abort(404)
    return jsonify(row_to_dict(row))


@app.route('/api/categories', methods=['POST'])
def api_category_create():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    if not name:
        abort(400, 'name is required')
    db = get_db()
    cursor = db.execute('INSERT INTO Categories (name, description) VALUES (?, ?)', (name, description))
    db.commit()
    return jsonify({'id': cursor.lastrowid}), 201


@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def api_category_update(category_id):
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    if not name:
        abort(400, 'name is required')
    db = get_db()
    cursor = db.execute('UPDATE Categories SET name = ?, description = ? WHERE id = ?', (name, description, category_id))
    db.commit()
    if cursor.rowcount == 0:
        abort(404)
    return jsonify({'id': category_id})


@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def api_category_delete(category_id):
    db = get_db()
    db.execute('DELETE FROM Flowers WHERE category_id = ?', (category_id,))
    cursor = db.execute('DELETE FROM Categories WHERE id = ?', (category_id,))
    db.commit()
    if cursor.rowcount == 0:
        abort(404)
    return jsonify({'deleted': category_id})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
