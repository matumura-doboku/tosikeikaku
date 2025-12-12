// Toggle Selection Mode
if (rangeSelectBtn) {
    rangeSelectBtn.addEventListener('click', () => {
        isSelectionMode = !isSelectionMode;
        if (isSelectionMode) {
            rangeSelectBtn.classList.add('active');
            mapContainer.classList.add('crosshair-cursor');
            if (gridToggle && !gridToggle.checked) {
                gridToggle.checked = true;
                gridToggle.dispatchEvent(new Event('change'));
            }
        } else {
            exitSelectionMode(false);
        }
    });
}

function exitSelectionMode(clearSelection) {
    isSelectionMode = false;
    rangeSelectBtn.classList.remove('active');
    mapContainer.classList.remove('crosshair-cursor');
    if (clearSelection) {
        selectedGridIds.clear();
        pinkGridIds.clear();
        analysisOverlays.forEach(l => map.removeLayer(l));
        analysisOverlays = [];
        if (gridLayer) gridLayer.resetStyle();
    }
}

// Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (isSelectionMode) {
            exitSelectionMode(true);
        } else {
            closePropertyPanel();
            map.closePopup();
        }
    } else if (e.key === 'Enter') {
        if (isSelectionMode) {
            if (selectedGridIds.size > 0) {
                performRangeAnalysis();
                exitSelectionMode(false);
            } else {
                exitSelectionMode(false);
            }
        }
    }
});

function performRangeAnalysis() {
    if (!gridLayer) return;
    const baseId = selectedGridIds.values().next().value;
    let baseLayer = null;

    gridLayer.eachLayer(layer => {
        const id = layer.feature.properties.id || layer.feature.id;
        if (id === baseId) {
            baseLayer = layer;
        }
    });

    if (!baseLayer) return;

    const bounds = baseLayer.getBounds();
    const center = bounds.getCenter();
    const northEast = bounds.getNorthEast();
    const southWest = bounds.getSouthWest();
    const latStep = northEast.lat - southWest.lat;
    const lngStep = northEast.lng - southWest.lng;

    const b7LatRadius = latStep * 3.5;
    const b7LngRadius = lngStep * 3.5;

    const bounds7 = L.latLngBounds(
        [center.lat - b7LatRadius, center.lng - b7LngRadius],
        [center.lat + b7LatRadius, center.lng + b7LngRadius]
    );

    const b20LatRadius = latStep * 10;
    const b20LngRadius = lngStep * 10;

    const bounds20 = L.latLngBounds(
        [center.lat - b20LatRadius, center.lng - b20LngRadius],
        [center.lat + b20LatRadius, center.lng + b20LngRadius]
    );

    pinkGridIds.clear();
    gridLayer.eachLayer(layer => {
        const id = layer.feature.properties.id || layer.feature.id;
        if (id !== baseId) {
            const lCenter = layer.getBounds().getCenter();
            if (bounds7.contains(lCenter)) {
                pinkGridIds.add(id);
            }
        }
    });
    gridLayer.setStyle(getFeatureStyle);

    const redBorder = L.rectangle(bounds20, {
        color: 'red',
        weight: 3,
        fill: false,
        dashArray: '5,5'
    }).addTo(map);
    analysisOverlays.push(redBorder);

    map.fitBounds(bounds20, { padding: [50, 50] });
    showRoads(bounds7);
}

function showRoads(bounds) {
    const north = bounds.getNorth();
    const south = bounds.getSouth();
    const east = bounds.getEast();
    const west = bounds.getWest();

    const url = `/api/roads?north=${north}&south=${south}&east=${east}&west=${west}`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.features && data.features.length > 0) {
                const roadLayer = L.geoJSON(data, {
                    style: {
                        color: 'gray',
                        weight: 1,
                        fillColor: 'gray',
                        fillOpacity: 0.6
                    }
                }).addTo(map);
                analysisOverlays.push(roadLayer);
            } else {
                console.log('No roads found in this area.');
            }
        })
        .catch(error => {
            console.error('Error fetching roads:', error);
        });
}

function closePropertyPanel() {
    propertyPanel.style.display = 'none';
    activePopupGridId = null;
    if (gridLayer) gridLayer.resetStyle();
    map.invalidateSize();
}

if (closePropertyPanelBtn) {
    closePropertyPanelBtn.addEventListener('click', closePropertyPanel);
}

if (vizModeSelect) {
    vizModeSelect.addEventListener('change', function () {
        currentVizMode = this.value;
        if (gridLayer) {
            gridLayer.setStyle(getFeatureStyle);
            updateLegend();
        }
    });
}
