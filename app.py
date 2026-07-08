from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Configure Flask
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Database Models
class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(50), unique=True, nullable=False)
    product_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    supplier = db.Column(db.String(100))
    location = db.Column(db.String(100))
    stock_quantity = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=0)
    cost_price = db.Column(db.Float, default=0.0)


class StockMovement(db.Model):
    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    movement_type = db.Column(db.String(20))
    quantity = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(200))

    product = db.relationship("Product")


# Dashboard
@app.route("/")
def dashboard():
    products = Product.query.all()

    total_products = len(products)

    low_stock = Product.query.filter(
        Product.stock_quantity <= Product.reorder_level
    ).all()

    stock_value = 0

    for product in products:
        stock_value += product.stock_quantity * product.cost_price

    return render_template(
        "dashboard.html",
        total_products=total_products,
        low_stock=low_stock,
        stock_value=stock_value
    )


# Products
@app.route("/products")
def products():
    search = request.args.get("search")

    if search:
        products = Product.query.filter(
            (Product.barcode.contains(search)) |
            (Product.product_code.contains(search)) |
            (Product.name.contains(search))
        ).all()
    else:
        products = Product.query.all()

    return render_template("products.html", products=products)


@app.route("/add-product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        product = Product(
            barcode=request.form["barcode"],
            product_code=request.form["product_code"],
            name=request.form["name"],
            category=request.form["category"],
            supplier=request.form["supplier"],
            location=request.form["location"],
            stock_quantity=int(request.form["stock_quantity"]),
            reorder_level=int(request.form["reorder_level"]),
            cost_price=float(request.form["cost_price"])
        )

        db.session.add(product)
        db.session.commit()

        return redirect(url_for("products"))

    return render_template("add_product.html")


@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        product.barcode = request.form["barcode"]
        product.product_code = request.form["product_code"]
        product.name = request.form["name"]
        product.category = request.form["category"]
        product.supplier = request.form["supplier"]
        product.location = request.form["location"]
        product.stock_quantity = int(request.form["stock_quantity"])
        product.reorder_level = int(request.form["reorder_level"])
        product.cost_price = float(request.form["cost_price"])

        db.session.commit()

        return redirect(url_for("products"))

    return render_template("edit_product.html", product=product)


@app.route("/delete-product/<int:product_id>")
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    db.session.delete(product)
    db.session.commit()

    return redirect(url_for("products"))


# Stock In
@app.route("/stock-in/<int:product_id>", methods=["POST"])
def stock_in(product_id):
    product = Product.query.get_or_404(product_id)

    quantity = int(request.form["quantity"])

    product.stock_quantity += quantity

    movement = StockMovement(
        product_id=product.id,
        movement_type="IN",
        quantity=quantity,
        note="Goods Received"
    )

    db.session.add(movement)
    db.session.commit()

    return redirect(url_for("products"))


# Stock Out
@app.route("/stock-out/<int:product_id>", methods=["POST"])
def stock_out(product_id):
    product = Product.query.get_or_404(product_id)

    quantity = int(request.form["quantity"])

    product.stock_quantity -= quantity

    movement = StockMovement(
        product_id=product.id,
        movement_type="OUT",
        quantity=quantity,
        note="Stock Issued"
    )

    db.session.add(movement)
    db.session.commit()

    return redirect(url_for("products"))


# Stock Movement History
@app.route("/movements")
def movements():
    movements = StockMovement.query.order_by(
        StockMovement.date.desc()
    ).all()

    return render_template("movements.html", movements=movements)


# Reports
@app.route("/stock-sheet")
def stock_sheet():
    products = Product.query.order_by(Product.location, Product.name).all()

    total_items = len(products)

    total_stock_value = 0

    for product in products:
        total_stock_value += product.stock_quantity * product.cost_price

    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    return render_template(
        "stock_sheet.html",
        products=products,
        total_items=total_items,
        total_stock_value=total_stock_value,
        current_date=current_date
    )


@app.route("/reports/low-stock")
def low_stock_report():

    products = Product.query.filter(
        Product.stock_quantity <= Product.reorder_level
    ).order_by(Product.name).all()

    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    return render_template(
        "low_stock_report.html",
        products=products,
        current_date=current_date
    )


@app.route("/reports/stock-valuation")
def stock_valuation_report():
    products = Product.query.order_by(Product.name).all()

    total_value = 0

    for product in products:
        total_value += product.stock_quantity * product.cost_price

    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    return render_template(
        "stock_valuation_report.html",
        products=products,
        total_value=total_value,
        current_date=current_date
    )

@app.route("/reports/stock-movements", methods=["GET"])
def stock_movement_report():

    query = StockMovement.query.join(Product)

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    part_number = request.args.get("part_number")

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(StockMovement.date >= start)

    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.filter(StockMovement.date <= end)

    if part_number:
        query = query.filter(
            Product.product_code.contains(part_number)
        )

    movements = query.order_by(
        StockMovement.date.desc()
    ).all()

    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    return render_template(
        "stock_movement_report.html",
        movements=movements,
        current_date=current_date,
        start_date=start_date,
        end_date=end_date,
        part_number=part_number
    )


@app.route("/reports/suppliers")
def supplier_report():

    products = Product.query.order_by(
        Product.supplier,
        Product.name
    ).all()

    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    return render_template(
        "supplier_report.html",
        products=products,
        current_date=current_date
    )


@app.route("/reports/inventory-audit")
def inventory_audit_report():

    products = Product.query.order_by(
        Product.location,
        Product.product_code
    ).all()

    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    return render_template(
        "inventory_audit_report.html",
        products=products,
        current_date=current_date
    )

# Create Database
with app.app_context():
    db.create_all()


# Run Application
if __name__ == "__main__":
    app.run(debug=True)