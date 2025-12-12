// Traffic Simulation Controls
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
function updateCityYearLabel() {
    if (cityYearLabel) {
        cityYearLabel.textContent = `シミュレーション年: ${cityYear}年後`;
    }
}

if (initCityBtn) {
    initCityBtn.addEventListener('click', () => {
        cityStatus.textContent = "Status: Initializing...";
        cityStatus.style.color = "orange";
        cityYear = 0;
        updateCityYearLabel();

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

        const steps = stepYearsSelect ? parseInt(stepYearsSelect.value) || 1 : 1;

        fetch('/api/city/step', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ steps: steps })
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    cityStatus.textContent = "Error: " + data.error;
                    cityStatus.style.color = "red";
                } else {
                    cityResults = data.results || {};
                    cityYear = data.year || 0;
                    cityStatus.textContent = `Status: ${cityYear}年後まで計算`;
                    cityStatus.style.color = "green";
                    updateCityYearLabel();

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
                cityYear = 0;
                updateCityYearLabel();
                if (gridLayer) gridLayer.setStyle(getFeatureStyle);
            });
    });
}
