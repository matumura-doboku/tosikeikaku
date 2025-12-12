// Address Search Logic
if (addressInput && suggestionList) {
    addressInput.addEventListener('input', function () {
        const query = this.value;
        if (query.length < 2) {
            suggestionList.style.display = 'none';
            return;
        }

        fetch(`https://msearch.gsi.go.jp/address-search/AddressSearch?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                suggestionList.innerHTML = '';
                if (data.length > 0) {
                    suggestionList.style.display = 'block';
                    data.forEach(item => {
                        const li = document.createElement('li');
                        li.textContent = item.properties.title;
                        li.addEventListener('click', () => {
                            const coords = item.geometry.coordinates; // [lng, lat]
                            map.flyTo([coords[1], coords[0]], 16); // Leaflet takes [lat, lng]
                            suggestionList.style.display = 'none';
                            addressInput.value = item.properties.title;
                        });
                        suggestionList.appendChild(li);
                    });
                } else {
                    suggestionList.style.display = 'none';
                }
            })
            .catch(error => console.error('Error fetching address:', error));
    });

    // Hide suggestions when clicking outside
    document.addEventListener('click', function (e) {
        if (e.target !== addressInput && e.target !== suggestionList) {
            suggestionList.style.display = 'none';
        }
    });
}
