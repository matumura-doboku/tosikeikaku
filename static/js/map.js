// Initialize map centered on Hiroshima (approximate coordinates from image)
map = L.map('map').setView([34.3853, 132.4553], 13);

// Add GSI Standard Tile Layer
L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png', {
    attribution: "<a href='https://maps.gsi.go.jp/development/ichiran.html' target='_blank'>Geospatial Information Authority of Japan</a>",
    maxZoom: 18
}).addTo(map);
