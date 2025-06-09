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
        
        const editUrl = window.routes.editProduct + id;
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

document.getElementById('clear-search-button').addEventListener('click', function() {
    document.getElementById('search-query').value = '';
    const products = document.querySelectorAll('.product-item');
    products.forEach(product => {
        product.style.display = '';
    });
});

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

document.addEventListener('DOMContentLoaded', function() {
    const categories = document.querySelectorAll('.categories li');
    const products = document.querySelectorAll('#product-list .product-item');
    const CATEGORY_KEY = 'selectedCategory';

    function filterProducts(category) {
        products.forEach(item => {
            if (category === 'all' || item.dataset.category === category) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
        categories.forEach(li => {
            li.classList.toggle('active', li.dataset.category === category);
        });
    }

    categories.forEach(li => {
        li.addEventListener('click', function(e) {
            e.preventDefault();
            const category = li.dataset.category;
            localStorage.setItem(CATEGORY_KEY, category);
            filterProducts(category);
        });
    });

    const savedCategory = localStorage.getItem(CATEGORY_KEY) || 'all';
    filterProducts(savedCategory);
});

window.selectProduct = selectProduct;

