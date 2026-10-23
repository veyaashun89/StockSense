from flask import Blueprint, request, jsonify
from backend.services.inventory_service import (
    list_products, get_product, create_product, update_product,
    delete_product, list_categories, list_suppliers, create_supplier
)
from backend.services.csv_service import import_products_csv

products_bp = Blueprint("products", __name__)

@products_bp.route("/products", methods=["GET"])
def get_products():
    search = request.args.get("search")
    category = request.args.get("category")
    status = request.args.get("status")
    sort_by = request.args.get("sort_by", "name")
    sort_dir = request.args.get("sort_dir", "asc")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    result = list_products(
        search=search,
        category=category,
        status=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        per_page=per_page
    )
    return jsonify(result), 200

@products_bp.route("/products/<id_or_sku>", methods=["GET"])
def get_single_product(id_or_sku):
    product = get_product(id_or_sku)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product), 200

@products_bp.route("/products", methods=["POST"])
def add_product():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON request body"}), 400
    try:
        product = create_product(data)
        return jsonify(product), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to create product: {str(e)}"}), 500

@products_bp.route("/products/<int:product_id>", methods=["PATCH", "PUT"])
def edit_product(product_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON request body"}), 400
    try:
        updated = update_product(product_id, data)
        if not updated:
            return jsonify({"error": "Product not found"}), 404
        return jsonify(updated), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to update product: {str(e)}"}), 500

@products_bp.route("/products/<int:product_id>", methods=["DELETE"])
def remove_product(product_id):
    try:
        res = delete_product(product_id)
        return jsonify(res), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to delete product: {str(e)}"}), 500

@products_bp.route("/products/categories", methods=["GET"])
def get_categories():
    categories = list_categories()
    return jsonify(categories), 200

@products_bp.route("/products/suppliers", methods=["GET"])
def get_suppliers():
    suppliers = list_suppliers()
    return jsonify(suppliers), 200

@products_bp.route("/products/suppliers", methods=["POST"])
def add_supplier():
    data = request.get_json() or {}
    try:
        supplier = create_supplier(data)
        return jsonify(supplier), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to create supplier: {str(e)}"}), 500

@products_bp.route("/products/import", methods=["POST"])
def import_products():
    if "file" not in request.files:
        return jsonify({"error": "No CSV file uploaded in 'file' form field"}), 400
    file = request.files["file"]
    content = file.read().decode("utf-8", errors="replace")
    try:
        res = import_products_csv(content)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
