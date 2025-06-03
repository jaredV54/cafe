function selectProduct(element) {
    const isActive = element.classList.contains('active_product');

    const previouslyActive = document.querySelector('.product-item.active_product');
    if (previouslyActive) {
        previouslyActive.classList.remove('active_product');
    }

    if (!isActive) {
        element.classList.add('active_product');

        const id = element.getAttribute('data-id');
        const name = element.getAttribute('data-name');
        const price = element.getAttribute('data-price');
        const category = element.getAttribute('data-category');
        const isAvailable = element.getAttribute('data-available') === 'true';

        document.getElementById('product-id').value = id;
        document.getElementById('product-name').value = name;
        document.getElementById('product-price').value = price;
        document.getElementById('product-category').value = category;
        document.getElementById('product-available').checked = isAvailable;
        
        document.getElementById('form-title').innerText = 'Update Product';
        document.getElementById('submit-button').innerText = 'Update';
        
        const editUrl = "{{ url_for('edit_product', product_id='0') }}".replace('/0', '/' + id);
        document.getElementById('product-form').action = editUrl;
        
        document.getElementById('cancel-button').style.display = 'inline';
    } else {
        document.getElementById('product-form').reset();
        document.getElementById('form-title').innerText = 'Add New Product';
        document.getElementById('submit-button').innerText = 'Add Product';
        document.getElementById('product-form').action = "{{ url_for('add_product') }}";
        document.getElementById('cancel-button').style.display = 'none';
    }
}

document.getElementById('cancel-button').onclick = function() {
        document.getElementById('product-form').reset();
        document.getElementById('form-title').innerText = 'Add New Product';
        document.getElementById('submit-button').innerText = 'Add Product';
        document.getElementById('product-form').action = "{{ url_for('add_product') }}";
        this.style.display = 'none';

        const previouslyActive = document.querySelector('.product-item.active_product');
        if (previouslyActive) {
            previouslyActive.classList.remove('active_product');
        }
};

document.getElementById('search-query').addEventListener('input', function() {
    const query = this.value.toLowerCase();
    const products = document.querySelectorAll('.product-item');
    
    products.forEach(product => {
        const name = product.getAttribute('data-name').toLowerCase();
        if (name.includes(query)) {
            product.style.display = '';
        } else {
            product.style.display = 'none';
        }
    });
});

window.selectProduct = selectProduct;
