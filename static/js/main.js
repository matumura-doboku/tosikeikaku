// Initialize map centered on Hiroshima (approximate coordinates from image)
const map = L.map('map').setView([34.3853, 132.4553], 13);

// Add GSI Standard Tile Layer
L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png', {
    attribution: "<a href='https://maps.gsi.go.jp/development/ichiran.html' target='_blank'>Geospatial Information Authority of Japan</a>",
    maxZoom: 18
}).addTo(map);

// Address Search Logic
const addressInput = document.getElementById('address-input');
const suggestionList = document.getElementById('suggestion-list');

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

// Tab switching logic
document.querySelectorAll('.tab-btn').forEach(button => {
    button.addEventListener('click', () => {
        // Remove active class from all buttons and contents
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

        // Add active class to clicked button
        button.classList.add('active');

        // Show corresponding content
        const tabId = button.getAttribute('data-tab');
        document.getElementById(`${tabId}-tab`).classList.add('active');
    });
});

// Grid Toggle & Selection Logic
const gridToggle = document.getElementById('grid-toggle');
const rangeSelectBtn = document.getElementById('range-select-btn');
const mapContainer = document.getElementById('map');
const propertyPanel = document.getElementById('property-panel');
const propertyContent = document.getElementById('property-content');
const closePropertyPanelBtn = document.getElementById('close-property-panel');
const vizModeSelect = document.getElementById('viz-mode');
const legendDiv = document.getElementById('legend');
let gridLayer = null;
let isSelectionMode = false;
let selectedGridIds = new Set(); // Stores IDs of selected features
let activePopupGridId = null; // Stores ID of the grid with open popup
let currentVizMode = 'none';

// Data Ranges for Visualization
let statsRanges = {
    'pop_total': { min: 0, max: 0 },
    'ratio_65_over': { min: 0, max: 0 },
    'ratio_15_64': { min: 0, max: 0 },
    'ratio_15_64': { min: 0, max: 0 },
    'traffic_flow': { min: 0, max: 1000 },
    'land_price': { min: 10, max: 20 }, // Base 10, max depends on acc
    'pop_sim': { min: 0, max: 100 },
    'vacant_floor_area_rate': { min: 0, max: 100 }
};

let simulationResults = {}; // Traffic: { zone_id: { flow_Total: ... } }
let cityResults = {}; // City: { mesh_code: { land_price: ..., population: ... } }

// Simulation Controls
const runSimBtn = document.getElementById('run-simulation-btn');
const simStatus = document.getElementById('simulation-status');
const flowMaxSlider = document.getElementById('flow-max-slider');
const flowMaxValSpan = document.getElementById('flow-max-val');

if (runSimBtn) {
    runSimBtn.addEventListener('click', () => {
        simStatus.textContent = "Status: Running...";
        simStatus.style.color = "orange";

        fetch('/api/simulate', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    simStatus.textContent = "Error: " + data.error;
                    simStatus.style.color = "red";
                } else {
                    simulationResults = data;
                    simStatus.textContent = "Status: Done (Zones: " + Object.keys(data).length + ")";
                    simStatus.style.color = "green";

                    // Auto-switch to traffic flow mode? Maybe not force it, let user choose.
                    // But if they are waiting, maybe good feedback?
                    // Let's just update the map if currently in traffic mode.
                    if (currentVizMode === 'traffic_flow') {
                        if (gridLayer) gridLayer.setStyle(getFeatureStyle);
                    }
                }
            })
            .catch(err => {
                console.error(err);
                simStatus.textContent = "Status: Failed";
                simStatus.style.color = "red";
            });
    });
}

if (flowMaxSlider) {
    flowMaxSlider.addEventListener('input', function () {
        const val = parseInt(this.value);
        flowMaxValSpan.textContent = val;
        statsRanges.traffic_flow.max = val;

        if (currentVizMode === 'traffic_flow' && gridLayer) {
            gridLayer.setStyle(getFeatureStyle);
            updateLegend();
        }
    });
}


// City Simulation Controls (Land Price & Pop)
const initCityBtn = document.getElementById('init-city-btn');
const stepCityBtn = document.getElementById('step-city-btn');
const resetCityBtn = document.getElementById('reset-city-btn');
const cityStatus = document.getElementById('city-status');

if (initCityBtn) {
    initCityBtn.addEventListener('click', () => {
        cityStatus.textContent = "Status: Initializing...";
        cityStatus.style.color = "orange";

        // Prepare filtering payload
        let payload = {};
        if (typeof pinkGridIds !== 'undefined' && pinkGridIds.size > 0) {
            payload.mesh_codes = Array.from(pinkGridIds);
            console.log("Initializing filter with codes:", payload.mesh_codes);
        }

        fetch('/api/city/init', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
            .then(res => res.json())
            .then(data => {
                if (data.filtered) {
                    cityStatus.textContent = "Status: Init (Range)";
                } else {
                    cityStatus.textContent = "Status: Initialized";
                }
                cityStatus.style.color = "green";
                console.log(data);

                // Refresh Styles
                if (gridLayer) gridLayer.setStyle(getFeatureStyle);
            })
            .catch(err => {
                console.error(err);
                cityStatus.textContent = "Status: Error";
                cityStatus.style.color = "red";
            });
    });
}

if (stepCityBtn) {
    stepCityBtn.addEventListener('click', () => {
        cityStatus.textContent = "Status: Running Step...";

        fetch('/api/city/step', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    cityStatus.textContent = "Error: " + data.error;
                    cityStatus.style.color = "red";
                } else {
                    cityResults = data;
                    cityStatus.textContent = "Status: Step Done";
                    cityStatus.style.color = "green";

                    // Stats update
                    let prices = [];
                    let pops = [];
                    Object.values(cityResults).forEach(v => {
                        prices.push(v.land_price);
                        pops.push(v.population);
                    });

                    if (prices.length > 0) {
                        statsRanges.land_price.max = Math.max(...prices);
                        statsRanges.land_price.min = Math.min(...prices);
                        statsRanges.pop_sim.max = Math.max(...pops);
                    }

                    // Refresh
                    if (currentVizMode.includes('_sim') || currentVizMode === 'land_price') {
                        if (gridLayer) gridLayer.setStyle(getFeatureStyle);
                        updateLegend();
                    }
                }
            })
            .catch(err => {
                console.error(err);
                cityStatus.textContent = "Status: Failed";
            });
    });
}

if (resetCityBtn) {
    resetCityBtn.addEventListener('click', () => {
        fetch('/api/city/reset', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                cityStatus.textContent = "Status: Reset";
                cityResults = {};
                if (gridLayer) gridLayer.setStyle(getFeatureStyle);
            });
    });
}

// Analysis State
let pinkGridIds = new Set(); // 7x7 zone
let analysisOverlays = []; // Red border, roads, etc.

const PROPERTY_LABELS = {
    'KEY_CODE': '地域メッシュコード',
    'MESH1_ID': '第1次メッシュコード',
    'MESH2_ID': '第2次メッシュコード',
    'MESH3_ID': '第3次メッシュコード',
    'MESH4_ID': '第4次メッシュコード',
    'OBJ_ID': 'オブジェクトID',
    'gml_id': 'GML ID',
    'POP_TOTAL': '人口（総数）',
    'POP_MALE': '人口（男）',
    'POP_FEMALE': '人口（女）',
    'RATIO_0_14': '年少人口比率（0-14歳）',
    'RATIO_15_64': '生産年齢人口比率（15-64歳）',
    'RATIO_65_OVER': '高齢人口比率（65歳以上）',
    'FLOOR_AREA': '床面積(㎡)',
    'VACANT_FLOOR_AREA': '空き床面積(㎡)',
    'VACANT_FLOOR_AREA_RATE': '空き床面積率(%)'
};

// Toggle Selection Mode
rangeSelectBtn.addEventListener('click', () => {
    isSelectionMode = !isSelectionMode;
    if (isSelectionMode) {
        rangeSelectBtn.classList.add('active');
        mapContainer.classList.add('crosshair-cursor');
        // Ensure grid is visible
        if (!gridToggle.checked) {
            gridToggle.checked = true;
            gridToggle.dispatchEvent(new Event('change'));
        }
    } else {
        exitSelectionMode(false); // Just exit mode, keep selection
    }
});

function exitSelectionMode(clearSelection) {
    isSelectionMode = false;
    rangeSelectBtn.classList.remove('active');
    mapContainer.classList.remove('crosshair-cursor');
    if (clearSelection) {
        selectedGridIds.clear();
        pinkGridIds.clear(); // Clear analysis
        // Remove overlays
        analysisOverlays.forEach(l => map.removeLayer(l));
        analysisOverlays = [];

        if (gridLayer) gridLayer.resetStyle();
    }
}

// Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (isSelectionMode) {
            exitSelectionMode(true); // Cancel (clear selection)
        } else {
            closePropertyPanel(); // Close right panel
            map.closePopup(); // Keep generic popup close just in case
        }
    } else if (e.key === 'Enter') {
        if (isSelectionMode) {
            if (selectedGridIds.size > 0) {
                performRangeAnalysis();
                exitSelectionMode(false); // Exit mode but keep results
            } else {
                exitSelectionMode(false); // Confirm without selection logic (fallback)
            }
        }
    }
});

function performRangeAnalysis() {
    // 1. Get Base Cell (Use first selected)
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

    // 2. Calculate Zones
    // 7x7 Zone: Center +/- 3 steps
    const b7LatMargin = latStep * 3.5; // 3.5 to create 7x7 around center? No, 7x7 means 3 neighbors each side + center. 3 * step.
    // If center is 1 unit, +/- 3 units radius = 7 units width.
    const b7LatRadius = latStep * 3.5; // Margin needs to cover the edges.
    const b7LngRadius = lngStep * 3.5;

    const bounds7 = L.latLngBounds(
        [center.lat - b7LatRadius, center.lng - b7LngRadius],
        [center.lat + b7LatRadius, center.lng + b7LngRadius]
    );

    // 20x20 Zone: Center +/- 10 steps
    const b20LatRadius = latStep * 10;
    const b20LngRadius = lngStep * 10;

    const bounds20 = L.latLngBounds(
        [center.lat - b20LatRadius, center.lng - b20LngRadius],
        [center.lat + b20LatRadius, center.lng + b20LngRadius]
    );

    // 3. Highlight 7x7 grids (Pink)
    pinkGridIds.clear();
    gridLayer.eachLayer(layer => {
        const id = layer.feature.properties.id || layer.feature.id;
        if (id !== baseId) { // Exclude base
            const lCenter = layer.getBounds().getCenter();
            if (bounds7.contains(lCenter)) {
                pinkGridIds.add(id);
            }
        }
    });
    gridLayer.setStyle(getFeatureStyle);

    // 4. Draw Red Border (20x20)
    const redBorder = L.rectangle(bounds20, {
        color: 'red',
        weight: 3,
        fill: false,
        dashArray: '5,5' // Optional: dashed line for zone
    }).addTo(map);
    analysisOverlays.push(redBorder);

    // Zoom to area
    map.fitBounds(bounds20, { padding: [50, 50] });

    // 5. Show Roads
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

// Panel Control Functions
function closePropertyPanel() {
    propertyPanel.style.display = 'none';
    activePopupGridId = null;
    if (gridLayer) gridLayer.resetStyle();
    // Force map resize to reclaim space
    map.invalidateSize();
}

closePropertyPanelBtn.addEventListener('click', closePropertyPanel);

vizModeSelect.addEventListener('change', function () {
    currentVizMode = this.value;
    if (gridLayer) {
        gridLayer.setStyle(getFeatureStyle); // Re-apply style
        updateLegend();
    }
});

function getColor(value, min, max, hueStart, hueEnd) {
    if (value === null || value === undefined || value === 0) return 'transparent';
    if (max === min) return `hsl(${hueEnd}, 70%, 50%)`;

    // Normalize 0 to 1
    let ratio = (value - min) / (max - min);
    if (ratio < 0) ratio = 0;
    if (ratio > 1) ratio = 1;

    // Interpolate Hue (or Lightness if single hue)
    // Let's use Lightness for simpler heatmap: 90% (light) -> 40% (dark)
    // Or Hue: 
    // Pop: Light Red (0, 100%, 90%) -> Dark Red (0, 100%, 40%)
    // But we passed hueStart/End. If they are same, vary lightness.

    if (hueStart === hueEnd) {
        let l = 90 - (ratio * 50); // 90 -> 40
        return `hsl(${hueStart}, 70%, ${l}%)`;
    }

    // If different hues, interpolate hue
    let h = hueStart + (ratio * (hueEnd - hueStart));
    return `hsl(${h}, 70%, 50%)`;
}

function getFeatureStyle(feature) {
    const id = feature.properties.id || feature.id;
    const isSelected = selectedGridIds.has(id);
    const isPink = pinkGridIds.has(id);
    const isActive = id === activePopupGridId;

    // Active overrides all
    if (isActive) {
        return {
            color: 'gray',
            weight: 2,
            fillOpacity: 0.5,
            fillColor: 'gray'
        };
    }

    let fillColor = 'blue';
    let fillOpacity = 0.1;
    let strokeColor = 'blue';
    let weight = 1;

    // Visualization Mode Logic
    if (currentVizMode !== 'none') {
        let val = 0;
        let min = 0;
        let max = 100;
        let hue = 0;

        if (currentVizMode === 'pop_total') {
            val = feature.properties.POP_TOTAL;
            min = statsRanges.pop_total.min;
            max = statsRanges.pop_total.max;
            hue = 0;
        } else if (currentVizMode === 'ratio_65_over') {
            val = feature.properties.VAL_RATIO_65_OVER;
            min = statsRanges.ratio_65_over.min;
            max = statsRanges.ratio_65_over.max;
            hue = 270;
        } else if (currentVizMode === 'ratio_15_64') {
            val = feature.properties.VAL_RATIO_15_64;
            min = statsRanges.ratio_15_64.min;
            max = statsRanges.ratio_15_64.max;
            hue = 120;
        } else if (currentVizMode === 'traffic_flow') {
            const res = simulationResults[id];
            if (res) {
                val = res.flow_Total;
            } else {
                val = 0;
            }
            min = 0;
            max = statsRanges.traffic_flow.max; // Use slider value
            hue = 0; // Red
        } else if (currentVizMode === 'land_price_sim') {
            const res = cityResults[feature.properties.KEY_CODE];
            val = res ? res.land_price : 0;
            min = statsRanges.land_price.min;
            max = statsRanges.land_price.max;
            hue = 60; // Yellow -> Red (if loop logic supports range)
            // Custom Color Logic for Price: Yellow (60) to Red (0)
            if (val > 0) {
                let r = (val - min) / (max - min || 1);
                hue = 60 - (r * 60);
                return {
                    color: strokeColor,
                    weight: weight,
                    fillColor: `hsl(${hue}, 100%, 50%)`,
                    fillOpacity: 0.6
                };
            }
        } else if (currentVizMode === 'pop_sim') {
            const res = cityResults[feature.properties.KEY_CODE];
            val = res ? res.population : 0;
            min = 0;
            max = statsRanges.pop_sim.max;
            hue = 200; // Blue
        } else if (currentVizMode === 'vacant_floor_area_rate') {
            val = feature.properties.VACANT_FLOOR_AREA_RATE;
            min = statsRanges.vacant_floor_area_rate.min;
            max = statsRanges.vacant_floor_area_rate.max;
            hue = 240; // Blue
        }

        fillColor = getColor(val, min, max, hue, hue);
        fillOpacity = (val > 0) ? 0.6 : 0.0;

        strokeColor = 'none';
        weight = 0;
    }

    // Selection / Analysis Overrides
    if (isPink) {
        fillOpacity = 0.0; // Transparent inside
        strokeColor = '#FF69B4'; // HotPink border
        weight = 2;
    }

    // Selected Base Cell
    if (isSelected) {
        strokeColor = 'green';
        weight = 3;
        // Keep fill from Viz or Pink? 
        // If standard mode, fill is blue/0.1.
        if (currentVizMode === 'none') {
            // Keep default behavior
        }
    }

    return {
        color: strokeColor,
        weight: weight,
        fillColor: fillColor,
        fillOpacity: fillOpacity
    };
}

function updateLegend() {
    if (currentVizMode === 'none') {
        legendDiv.style.display = 'none';
        return;
    }

    let min, max, hue, label;
    if (currentVizMode === 'pop_total') {
        min = statsRanges.pop_total.min;
        max = statsRanges.pop_total.max;
        hue = 0;
        label = "人口（総数）";
    } else if (currentVizMode === 'ratio_65_over') {
        min = statsRanges.ratio_65_over.min;
        max = statsRanges.ratio_65_over.max;
        hue = 270;
        label = "高齢化率（%）";
    } else if (currentVizMode === 'ratio_15_64') {
        min = statsRanges.ratio_15_64.min;
        max = statsRanges.ratio_15_64.max;
        hue = 120;
        label = "生産年齢人口率（%）";
    } else if (currentVizMode === 'traffic_flow') {
        min = 0;
        max = statsRanges.traffic_flow.max;
        hue = 0;
        label = "Traffic Volume (Veh/Hr)";
    } else if (currentVizMode === 'land_price_sim') {
        min = statsRanges.land_price.min;
        max = statsRanges.land_price.max;
        hue = 60; // Start hue (Yellow)
        label = "Land Price (Simulated)";
        // For special gradient Yellow->Red
        hue = "60, 100%, 50%), hsl(0";
    } else if (currentVizMode === 'pop_sim') {
        min = 0;
        max = statsRanges.pop_sim.max;
        hue = 200;
        label = "Population (Simulated)";
    } else if (currentVizMode === 'vacant_floor_area_rate') {
        min = statsRanges.vacant_floor_area_rate.min;
        max = statsRanges.vacant_floor_area_rate.max;
        hue = 240;
        label = "空き床面積率（%）";
    }


    legendDiv.innerHTML = `
        <strong>${label}</strong>
        <div class="legend-gradient" style="background: linear-gradient(to right, hsl(${hue}, 70%, 90%), hsl(${hue}, 70%, 40%));"></div>
        <div class="legend-labels">
            <span>${Math.round(min)}</span>
            <span>${Math.round(max)}</span>
        </div>
    `;
    legendDiv.style.display = 'block';
}

gridToggle.addEventListener('change', function () {
    if (this.checked) {
        if (!gridLayer) {
            fetch('/grid-data')
                .then(response => response.json())
                .then(data => {
                    map.createPane('gridPane');
                    map.getPane('gridPane').style.zIndex = 600;

                    // Calculate Statistics (Min/Max)
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
                    // Min usually 0, but good to check min > 0 if needed. keeping 0 for now.

                    gridLayer = L.geoJSON(data, {
                        pane: 'gridPane',
                        style: getFeatureStyle,
                        onEachFeature: function (feature, layer) {
                            // Assign an ID if missing for tracking
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
                                    // Neutral mode: Show properties in Right Panel
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

                                    // Trigger map resize so it fits in the new space
                                    map.invalidateSize();
                                }
                            });
                        }
                    }).addTo(map);

                    // Replaced popup logic with panel control, so we don't need map.on('popupclose') for this specific feature anymore
                    // However, if we click map background, we might want to close the panel?
                    map.on('click', (e) => {
                        // If we click on the map (not on a feature), close the panel
                        // Note: L.geoJSON click bubbles up, but we handle the feature click first.
                        // We need to ensure this doesn't conflict. 
                        // Actually, Leaflet click event on map fires even if we click a feature unless propagation is stopped.
                        // Let's rely on the feature click handler to set activePopupGridId, 
                        // and check if the click target is the map itself to close.
                    });
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

// Report Tab Logic
const reportTabBtn = document.querySelector('.tab-btn[data-tab="report"]');
const reportContentDiv = document.getElementById('report-tab');

if (reportTabBtn) {
    reportTabBtn.addEventListener('click', () => {
        loadReport();
    });
}

function loadReport() {
    reportContentDiv.innerHTML = '<p>Loading report data...</p>';

    fetch('/api/report')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'No data') {
                reportContentDiv.innerHTML = `
                    <h3>Simulation Report</h3>
                    <p>No simulation data available. Please run a simulation first in the "Calculation" tab.</p>
                `;
                return;
            }

            renderReport(data);
        })
        .catch(err => {
            console.error(err);
            reportContentDiv.innerHTML = `<p style="color:red">Error loading report: ${err}</p>`;
        });
}

function renderReport(data) {
    const summary = data.summary;
    const topZones = data.top_congested_zones;

    let html = `<h3>Simulation Report</h3>`;

    // Summary Table
    html += `
        <h4>Summary</h4>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">Total Zones</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${summary.total_zones.toLocaleString()}</td>
            </tr>
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">Active Traffic Zones</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${summary.active_traffic_zones.toLocaleString()}</td>
            </tr>
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">Total Network Flow (Vol)</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${summary.total_network_flow.toLocaleString()}</td>
            </tr>
        </table>
    `;

    // Top Zones Table
    html += `<h4>Top 5 Congested Zones</h4>`;
    if (topZones && topZones.length > 0) {
        html += `
            <table style="width: 100%; border-collapse: collapse;">
                <thead style="background-color: #f2f2f2;">
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Zone ID</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Total Flow</th>
                    </tr>
                </thead>
                <tbody>
        `;

        topZones.forEach(z => {
            html += `
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">${z.key_code}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">${z.total_flow.toLocaleString()}</td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
    } else {
        html += `<p>No traffic data found.</p>`;
    }

    // City Model Report
    if (data.city_model) {
        const cm = data.city_model;
        html += `
            <hr style="margin: 20px 0;">
            <h3>City Dynamics Report</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Max Land Price</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">${cm.max_land_price.toFixed(2)}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Max Pop/Cell</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">${cm.max_population_cell.toFixed(0)}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Total Population (Simulated Range)</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">${cm.total_population.toLocaleString()}</td>
                </tr>
            </table>
        `;
    }

    // Add Export Button (Mockup)
    html += `
        <div style="margin-top: 20px;">
            <button onclick="alert('CSV Export feature coming soon!')" style="padding: 10px; cursor: pointer;">Download CSV</button>
        </div>
    `;

    reportContentDiv.innerHTML = html;
}
