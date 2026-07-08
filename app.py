from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Create the flask application instance
app = Flask(__name__)

# Configure the database connection.
# This tells SQLAlchemy to use a SQLite database file called
# 'inventory.db', which will be created in the project's instance
# folder if it does not already exist.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"

# Disable SQLAlchemy's modification tracking feature.
# This reduces memory usage and removes a warning because
# the feature is not needed for this application.
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Create the SQLAlchemy database object.
# This links SQLAlchemy to the Flask application, allowing
# models to be defined and database operations (queries,
# inserts, updates, and deletes) to be performed.
db = SQLAlchemy(app)


# Database model for the products table
class Product(db.Model):

    # Specify the name of the table
    __tablename__ = "products"

    # Define the table columns and their data types
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

# Database model for the stock movement table
class StockMovement(db.Model):

    # Specify the name of the table
    __tablename__ = "stock_movements"

    # Define the table columns and their data types
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    movement_type = db.Column(db.String(20))
    quantity = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(200))

    # Create. a relationship with the product table
    product = db.relationship("Product")


# Dashboard page
@app.route("/")
def dashboard():
    # Get all products from database
    products = Product.query.all()

    # Count total numberf of products
    total_products = len(products)

    # Find products with low stock
    low_stock = Product.query.filter(
        Product.stock_quantity <= Product.reorder_level
    ).all()

    # Calculate low value of stock
    stock_value = 0

    for product in products:
        stock_value += product.stock_quantity * product.cost_price

    # Get all the stock movements
    movements = StockMovement.query.all()

    # store number of monthly movements
    monthly_counts = {}

    for movement in movements:
        month = movement.date.strftime("%b %Y")

        if month not in monthly_counts:
            monthly_counts[month] = 0

        monthly_counts[month] += 1

    # Prepare chart labels
    chart_labels = list(monthly_counts.keys())
    chart_data = list(monthly_counts.values())

    # Send data to
    return render_template(
        "dashboard.html",
        total_products=total_products,
        low_stock=low_stock,
        stock_value=stock_value,
        chart_labels=chart_labels,
        chart_data=chart_data
    )


# Products page
@app.route("/products")
def products():

    # Get search value from user
    search = request.args.get("search")

    # Search for matching products if a search term is entered
    if search:
        products = Product.query.filter(
            (Product.barcode.contains(search)) |
            (Product.product_code.contains(search)) |
            (Product.name.contains(search))
        ).all()

    # If no search term display all products
    else:
        products = Product.query.all()

    # Send product list to template
    return render_template("products.html", products=products)

# Add new product
@app.route("/add-product", methods=["GET", "POST"])
def add_product():

    # Process the form when it is submitted
    if request.method == "POST":

        # Create a new product from the form data
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

        # Save the product to the database
        db.session.add(product)
        db.session.commit()

        # Return to the products page
        return redirect(url_for("products"))

    # Dispaly the add product form
    return render_template("add_product.html")

# Edit an existing product
@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    # Find the selected product
    product = Product.query.get_or_404(product_id)

    # Process the form when it is submitted
    if request.method == "POST":

        # Update the product details
        product.barcode = request.form["barcode"]
        product.product_code = request.form["product_code"]
        product.name = request.form["name"]
        product.category = request.form["category"]
        product.supplier = request.form["supplier"]
        product.location = request.form["location"]
        product.stock_quantity = int(request.form["stock_quantity"])
        product.reorder_level = int(request.form["reorder_level"])
        product.cost_price = float(request.form["cost_price"])

        # save changes to database
        db.session.commit()

        # Return to the products page
        return redirect(url_for("products"))

    # Display the edit product form
    return render_template("edit_product.html", product=product)

# Delete a product
@app.route("/delete-product/<int:product_id>")
def delete_product(product_id):

    # Find selected product
    product = Product.query.get_or_404(product_id)

    # REmove the product from the database
    db.session.delete(product)
    db.session.commit()

    # Return to the product page
    return redirect(url_for("products"))


# Add stock
@app.route("/stock-in/<int:product_id>", methods=["POST"])
def stock_in(product_id):

    # Find selected product
    product = Product.query.get_or_404(product_id)

    # Get quantity from user
    quantity = int(request.form["quantity"])

    # Increase the stock quantity
    product.stock_quantity += quantity

    # Record the stock movement
    movement = StockMovement(
        product_id=product.id,
        movement_type="IN",
        quantity=quantity,
        note="Goods Received"
    )

    # Save cahnges to the database
    db.session.add(movement)
    db.session.commit()

    # Return to the product page
    return redirect(url_for("products"))


# Remove stock
@app.route("/stock-out/<int:product_id>", methods=["POST"])
def stock_out(product_id):

    # Find the selected product
    product = Product.query.get_or_404(product_id)

    # Get quantity entered by the user
    quantity = int(request.form["quantity"])

    # Reduce the stock quantoity
    product.stock_quantity -= quantity

    # Record the stock movement
    movement = StockMovement(
        product_id=product.id,
        movement_type="OUT",
        quantity=quantity,
        note="Stock Issued"
    )

    # Save changes to the database
    db.session.add(movement)
    db.session.commit()

    # Return to products page
    return redirect(url_for("products"))


# Stock movement history
@app.route("/movements")
def movements():

    # Get all stock movements, latest first
    movements = StockMovement.query.order_by(
        StockMovement.date.desc()
    ).all()

    # Send stock movements to template
    return render_template("movements.html", movements=movements)


# Stock sheet report
@app.route("/stock-sheet")
def stock_sheet():

    # Get products sorted by location and name
    products = Product.query.order_by(Product.location, Product.name).all()

    # Count total number of products 
    total_items = len(products)

    # Calculate the toatl value of all stock
    total_stock_value = 0

    for product in products:
        total_stock_value += product.stock_quantity * product.cost_price

    # Get current date and time
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Send the report data to the template
    return render_template(
        "stock_sheet.html",
        products=products,
        total_items=total_items,
        total_stock_value=total_stock_value,
        current_date=current_date
    )

# Low stock report
@app.route("/reports/low-stock")
def low_stock_report():

    # Get all products below the minimum reorder level
    products = Product.query.filter(
        Product.stock_quantity <= Product.reorder_level
    ).order_by(Product.name).all()

    # Get current date and time
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Send the data to the template
    return render_template(
        "low_stock_report.html",
        products=products,
        current_date=current_date
    )

# Stock valuation report
@app.route("/reports/stock-valuation")
def stock_valuation_report():

    # Get all products sorted by name
    products = Product.query.order_by(Product.name).all()

    # Calculate total value of stock
    total_value = 0

    for product in products:
        total_value += product.stock_quantity * product.cost_price

    # Get date and time
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Return report to template
    return render_template(
        "stock_valuation_report.html",
        products=products,
        total_value=total_value,
        current_date=current_date
    )

# Stock movement report
@app.route("/reports/stock-movements", methods=["GET"])
def stock_movement_report():

    # Get all stock movements and link to products
    query = StockMovement.query.join(Product)

    # Get search information from user
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    part_number = request.args.get("part_number")

    # Filter by start date
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(StockMovement.date >= start)

    # Filter by end date
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.filter(StockMovement.date <= end)

    # Filter by part number
    if part_number:
        query = query.filter(
            Product.product_code.contains(part_number)
        )

    # Get filtered results, latest first
    movements = query.order_by(
        StockMovement.date.desc()
    ).all()

    # Get current date and time
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Return report to template
    return render_template(
        "stock_movement_report.html",
        movements=movements,
        current_date=current_date,
        start_date=start_date,
        end_date=end_date,
        part_number=part_number
    )

# Supplier report
@app.route("/reports/suppliers")
def supplier_report():

    # Get all products sorted by supplier and product name
    products = Product.query.order_by(
        Product.supplier,
        Product.name
    ).all()

    # Get current date and time
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Return report to template
    return render_template(
        "supplier_report.html",
        products=products,
        current_date=current_date
    )

# Inventory audit report
@app.route("/reports/inventory-audit")
def inventory_audit_report():

    # Get all products, sort by location and product code
    products = Product.query.order_by(
        Product.location,
        Product.product_code
    ).all()

    # Get current date and time
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Return data to template
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