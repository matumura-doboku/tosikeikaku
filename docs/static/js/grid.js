// Grid Toggle & Data Loading
if (gridToggle) {
    gridToggle.addEventListener('change', function () {
        if (this.checked) {
            if (!gridLayer) {
                fetch('/grid-data')
                    .then(response => response.json())
                    .then(data => {
                        map.createPane('gridPane');
                        map.getPane('gridPane').style.zIndex = 600;

                        let pops = [];
                        let r65 = [];
                        let r15 = [];
                        let vRate = [];

                        data.features.forEach(f => {
                            pops.push(f.properties.POP_TOTAL || 0);
                            r65.push(f.properties.VAL_RATIO_65_OVER || 0);
                            r15.push(f.properties.VAL_RATIO_15_64 || 0);
                            vRate.push(f.properties.VACANT_FLOOR_AREA_RATE || 0);
                        });

                        statsRanges.pop_total.max = Math.max(...pops);
                        statsRanges.ratio_65_over.max = Math.max(...r65);
                        statsRanges.ratio_15_64.max = Math.max(...r15);

                        gridLayer = L.geoJSON(data, {
                            pane: 'gridPane',
                            style: getFeatureStyle,
                            onEachFeature: function (feature, layer) {
                                if (!feature.id && !feature.properties.id) {
                                    feature.id = L.Util.stamp(layer);
                                }
                                const id = feature.properties.id || feature.id;

                                layer.on('click', (e) => {
                                    if (isSelectionMode) {
                                        if (selectedGridIds.has(id)) {
                                            selectedGridIds.delete(id);
                                        } else {
                                            selectedGridIds.add(id);
                                        }
                                        gridLayer.resetStyle(layer);
                                    } else {
                                        activePopupGridId = id;
                                        gridLayer.resetStyle();

                                        let content = '<ul style="padding-left: 20px; margin: 5px 0;">';
                                        for (const [key, value] of Object.entries(feature.properties)) {
                                            const label = PROPERTY_LABELS[key] || key;
                                            content += `<li><strong>${label}:</strong> ${value}</li>`;
                                        }
                                        content += '</ul>';

                                        propertyContent.innerHTML = content;
                                        propertyPanel.style.display = 'flex';
                                        map.invalidateSize();
                                    }
                                });
                            }
                        }).addTo(map);
                    })
                    .catch(error => console.error('Error loading grid data:', error));
            } else {
                map.addLayer(gridLayer);
            }
        } else {
            if (gridLayer) {
                map.removeLayer(gridLayer);
            }
        }
    });
}
