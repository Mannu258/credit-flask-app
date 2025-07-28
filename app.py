from flask import Flask, request, redirect, url_for, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_FILE = 'sqlite3.db'


# ─── DATABASE INIT ─────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS shops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        details TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id INTEGER,
        product TEXT,
        amount INTEGER,
        date TEXT,
        FOREIGN KEY (shop_id) REFERENCES shops(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id INTEGER,
        amount INTEGER,
        date TEXT,
        FOREIGN KEY (shop_id) REFERENCES shops(id)
    )''')

    conn.commit()
    conn.close()


init_db()


# ─── ROUTES ────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Add Shop POST
    if request.method == 'POST' and 'shop_name' in request.form:
        shop_name = request.form['shop_name'].strip()
        shop_details = request.form['shop_details'].strip()
        if shop_name:
            c.execute('INSERT INTO shops (name, details) VALUES (?, ?)', (shop_name, shop_details))
            conn.commit()
        return redirect(url_for('index'))

    # Add Payment POST
    if request.method == 'POST' and 'pay_amount' in request.form and 'pay_shop_id' in request.form:
        shop_id = request.form['pay_shop_id']
        try:
            pay_amount = int(request.form['pay_amount'])
        except ValueError:
            pay_amount = 0
        if pay_amount > 0:
            pay_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute('INSERT INTO payments (shop_id, amount, date) VALUES (?, ?, ?)', (shop_id, pay_amount, pay_date))
            conn.commit()
        return redirect(url_for('index', shop_id=shop_id if shop_id != "all" else None))

    # Fetch shops as (str_id, name) for template
    c.execute('SELECT id, name FROM shops ORDER BY name COLLATE NOCASE')
    shops = [(str(row[0]), row[1]) for row in c.fetchall()]

    selected_shop_id = request.args.get('shop_id')

    # Fetch expenses and payments filtered or all
    if selected_shop_id and selected_shop_id != "all":
        c.execute('''SELECT p.product, p.amount, p.date, s.name 
                     FROM products p JOIN shops s ON p.shop_id = s.id
                     WHERE s.id = ?
                     ORDER BY p.date DESC''', (selected_shop_id,))
        expenses = c.fetchall()

        c.execute('SELECT SUM(amount) FROM products WHERE shop_id = ?', (selected_shop_id,))
        total_expense = c.fetchone()[0] or 0

        c.execute('SELECT SUM(amount) FROM payments WHERE shop_id = ?', (selected_shop_id,))
        total_paid = c.fetchone()[0] or 0

        c.execute('''SELECT p.amount, p.date, s.name
                     FROM payments p JOIN shops s ON p.shop_id = s.id
                     WHERE s.id = ?
                     ORDER BY p.date DESC''', (selected_shop_id,))
        payments = c.fetchall()
    else:
        c.execute('''SELECT p.product, p.amount, p.date, s.name 
                     FROM products p JOIN shops s ON p.shop_id = s.id
                     ORDER BY p.date DESC''')
        expenses = c.fetchall()

        c.execute('SELECT SUM(amount) FROM products')
        total_expense = c.fetchone()[0] or 0

        c.execute('SELECT SUM(amount) FROM payments')
        total_paid = c.fetchone()[0] or 0

        c.execute('''SELECT p.amount, p.date, s.name
                     FROM payments p JOIN shops s ON p.shop_id = s.id
                     ORDER BY p.date DESC''')
        payments = c.fetchall()

    conn.close()

    net_due = total_expense - total_paid

    return render_template_string(INDEX_HTML,
        shops=shops,
        expenses=expenses,
        payments=payments,
        selected_shop_id=selected_shop_id,
        total_expense=total_expense,
        total_paid=total_paid,
        net_due=net_due)


@app.route('/add_product', methods=['POST'])
def add_product():
    shop_id = request.form.get('shop_id')
    product = request.form.get('product', '').strip()
    amount = request.form.get('amount', '').strip()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not (shop_id and product and amount):
        return redirect(url_for('index'))
    try:
        amount = int(amount)
    except ValueError:
        return redirect(url_for('index'))
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO products (shop_id, product, amount, date) VALUES (?, ?, ?, ?)',
              (shop_id, product, amount, date))
    conn.commit()
    conn.close()
    return redirect(url_for('index', shop_id=shop_id))


@app.route('/delete_shop/<shop_id>', methods=['POST'])
def delete_shop(shop_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM payments WHERE shop_id = ?', (shop_id,))
    c.execute('DELETE FROM products WHERE shop_id = ?', (shop_id,))
    c.execute('DELETE FROM shops WHERE id = ?', (shop_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


# ─── HTML TEMPLATE ─────────────────────────────────────
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Shop Expense Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .fab-add-shop {
            position: fixed;
            right: 16px;
            bottom: 86px;
            z-index: 1000;
        }
        .fab-add-pay {
            position: fixed;
            right: 16px;
            bottom: 16px;
            z-index: 1000;
        }
        .fab-delete-shop {
            position: fixed;
            right: 16px;
            bottom: 156px;
            z-index: 1000;
        }
        @media (max-width: 768px) {
            .fab-add-shop, .fab-add-pay, .fab-delete-shop {
                right: 10px;
            }
        }
        /* Optional styling for floating buttons */
        .btn-rounded-circle {
            width: 48px;
            height: 48px;
            padding: 0;
            border-radius: 50%;
            font-size: 1.5rem;
            line-height: 48px;
            text-align: center;
        }
    </style>
</head>
<body class="bg-light">
<div class="container py-4">

    <h2 class="text-center mb-2">🛒 Net Due:
        <span class="{% if net_due > 0 %}text-danger{% elif net_due < 0 %}text-success{% else %}text-secondary{% endif %}">
            ₹{{ net_due }}
        </span>
    </h2>
    <div class="text-center small mb-4">
        Expense: <span class="text-primary">₹{{ total_expense }}</span> &nbsp;|&nbsp;
        Paid: <span class="text-success">₹{{ total_paid }}</span>
    </div>

    <form method="GET" class="mb-4">
        <label class="form-label">Filter by Shop</label>
        <select name="shop_id" class="form-select" onchange="this.form.submit()">
            <option value="all" {% if not selected_shop_id or selected_shop_id == 'all' %}selected{% endif %}>All Shops</option>
            {% for shop in shops %}
                <option value="{{ shop[0] }}" {% if selected_shop_id == shop[0] %}selected{% endif %}>{{ shop[1] }}</option>
            {% endfor %}
        </select>
    </form>

    <div class="row g-4">
        <div class="col-12 col-md-6">
            <div class="card shadow">
                <div class="card-body">
                    <h5 class="card-title">➕ Add Product</h5>
                    <form method="POST" action="{{ url_for('add_product') }}">
                        <div class="mb-2">
                            <label class="form-label">Shop</label>
                            <select name="shop_id" class="form-select" required {% if shops|length == 0 %}disabled{% endif %}>
                                {% if shops|length == 0 %}
                                    <option>No shop yet</option>
                                {% else %}
                                    {% for shop in shops %}
                                        <option value="{{ shop[0] }}">{{ shop[1] }}</option>
                                    {% endfor %}
                                {% endif %}
                            </select>
                        </div>
                        <div class="mb-2">
                            <label class="form-label">Product Name</label>
                            <input type="text" name="product" class="form-control" required {% if shops|length == 0 %}disabled{% endif %}>
                        </div>
                        <div class="mb-2">
                            <label class="form-label">Amount (₹)</label>
                            <input type="number" name="amount" min="1" class="form-control" required {% if shops|length == 0 %}disabled{% endif %}>
                        </div>
                        <button type="submit" class="btn btn-primary w-100" {% if shops|length == 0 %}disabled{% endif %}>Add Product</button>
                        {% if shops|length == 0 %}
                            <div class="text-danger mt-2">Add a shop first!</div>
                        {% endif %}
                    </form>
                </div>
            </div>
        </div>
        <div class="col-12 col-md-6"></div>
    </div>

    <hr class="my-4">

    <h4 class="mb-3">📋 Expense Records {% if selected_shop_id and selected_shop_id != 'all' %}(Filtered){% endif %}</h4>
    <div class="table-responsive">
        <table class="table table-bordered table-striped table-sm align-middle">
            <thead class="table-dark">
                <tr>
                    <th>Shop</th>
                    <th>Product</th>
                    <th>Amount (₹)</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
                {% for exp in expenses %}
                <tr>
                    <td>{{ exp[3] }}</td>
                    <td>{{ exp[0] }}</td>
                    <td>{{ exp[1] }}</td>
                    <td>{{ exp[2] }}</td>
                </tr>
                {% endfor %}
                {% if expenses|length == 0 %}
                <tr><td colspan="4" class="text-center text-muted">No expenses recorded.</td></tr>
                {% endif %}
            </tbody>
        </table>
    </div>

    <hr class="my-4">

    <h4 class="mb-3">💰 Payment History {% if selected_shop_id and selected_shop_id != 'all' %}(Filtered){% endif %}</h4>
    <div class="table-responsive">
        <table class="table table-bordered table-striped table-sm align-middle">
            <thead class="table-dark">
                <tr>
                    <th>Shop</th>
                    <th>Amount Paid (₹)</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
                {% for pay in payments %}
                <tr>
                    <td>{{ pay[2] }}</td>
                    <td>{{ pay[0] }}</td>
                    <td>{{ pay[1] }}</td>
                </tr>
                {% endfor %}
                {% if payments|length == 0 %}
                <tr><td colspan="3" class="text-center text-muted">No payments recorded.</td></tr>
                {% endif %}
            </tbody>
        </table>
    </div>

</div>

<!-- Floating Add Shop Button -->
<button type="button" class="btn btn-success btn-rounded-circle fab-add-shop" data-bs-toggle="modal" data-bs-target="#addShopModal" title="Add Shop">
    +
</button>

<!-- Floating Add Payment Button -->
<button type="button" class="btn btn-primary btn-rounded-circle fab-add-pay" data-bs-toggle="modal" data-bs-target="#addPayModal" title="Add Payment">
    ₹
</button>

<!-- Floating Delete Shop Button with Dropdown -->
<div class="fab-delete-shop">
  <div class="btn-group dropup">
    <button type="button" class="btn btn-danger btn-rounded-circle dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false" title="Delete Shop">
      &ndash;
    </button>
    <ul class="dropdown-menu">
      <li><h6 class="dropdown-header">Delete Shop</h6></li>
      {% for shop in shops %}
      <li>
        <button class="dropdown-item text-danger" onclick="deleteShopConfirm('{{ shop[0] }}', '{{ shop[1] }}')">
          {{ shop[1] }}
        </button>
      </li>
      {% endfor %}
      {% if shops|length == 0 %}
      <li><span class="dropdown-item text-muted">No Shops</span></li>
      {% endif %}
    </ul>
  </div>
</div>

<!-- Delete Shop Hidden Form -->
<form id="deleteShopForm" method="POST" style="display:none;"></form>

<!-- Add Shop Modal -->
<div class="modal fade" id="addShopModal" tabindex="-1" aria-labelledby="addShopModalLabel" aria-hidden="true">
  <div class="modal-dialog">
    <form method="POST">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="addShopModalLabel">Add Shop</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
            <div class="mb-2">
                <label class="form-label">Shop Name</label>
                <input type="text" name="shop_name" class="form-control" required>
            </div>
            <div class="mb-2">
                <label class="form-label">Shop Details</label>
                <textarea name="shop_details" class="form-control" rows="2" required></textarea>
            </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
          <button type="submit" class="btn btn-success">Add Shop</button>
        </div>
      </div>
    </form>
  </div>
</div>

<!-- Add Payment Modal -->
<div class="modal fade" id="addPayModal" tabindex="-1" aria-labelledby="addPayModalLabel" aria-hidden="true">
  <div class="modal-dialog">
    <form method="POST">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="addPayModalLabel">Add Payment to Shop</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
            <div class="mb-2">
                <label class="form-label">Shop</label>
                <select name="pay_shop_id" class="form-select" required {% if shops|length == 0 %}disabled{% endif %}>
                    {% if shops|length == 0 %}
                    <option>No shop yet</option>
                    {% else %}
                        {% for shop in shops %}
                        <option value="{{ shop[0] }}">{{ shop[1] }}</option>
                        {% endfor %}
                    {% endif %}
                </select>
            </div>
            <div class="mb-2">
                <label class="form-label">Amount Paid (₹)</label>
                <input type="number" name="pay_amount" min="1" class="form-control" required {% if shops|length == 0 %}disabled{% endif %}>
            </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
          <button type="submit" class="btn btn-primary">Add Payment</button>
        </div>
      </div>
    </form>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<script>
  const MOBILE_NUMBER = "9386090900";

  function deleteShopConfirm(shopId, shopName) {
    if (!confirm(`Are you sure you want to delete "${shopName}" and all its data?`)) return;
    const userText = prompt(`Type DELETE to confirm you want to delete "${shopName}" and all its records:`);
    if (!userText || userText.trim().toUpperCase() !== "DELETE") {
      alert("You must type DELETE exactly.");
      return;
    }
    const mnum = prompt("Enter your mobile number to confirm deletion:");
    if (mnum !== MOBILE_NUMBER) {
      alert("Mobile number doesn't match.");
      return;
    }
    const form = document.getElementById('deleteShopForm');
    form.action = "/delete_shop/" + encodeURIComponent(shopId);
    form.method = "POST";
    form.submit();
  }
</script>

</body>
</html>
'''


# ─── RUN ───────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
